#!/usr/bin/env python3
"""Build the anonymised artifact mirror referenced by the S&P submission.

Why
---
The submission states that the release ships on artifact acceptance and that the
anonymous submission carries no locator. That leaves a gap a reviewer cannot
close: nothing in the repository is prepared for anonymous inspection, so the
``\\path{}`` targets in the appendix cannot be resolved by anyone but the author,
and several files in the tree carry author identity, cloud subscription
identifiers, and credential-shaped strings.

This script closes that gap. It assembles a bundle containing exactly the
version of record, redacts identity and credential-shaped strings, and then
*verifies* the result rather than asserting it:

1. every appendix ``\\path{}`` target resolves inside the bundle;
2. no banned token survives anywhere in the bundle;
3. no text file in the bundle is byte-identical to a source file that contained
   a banned token, which catches a rule that silently failed to apply;
4. every included file is hashed into ``MANIFEST.json``.

Inclusion is an explicit allowlist, not a glob, so the mirror's contents are
auditable and cannot silently grow when the repository does.

Usage::

    python scripts/build_anonymized_mirror.py            # build + verify
    python scripts/build_anonymized_mirror.py --check    # verify an existing build
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUNDLE_NAME = "ragin-sp-mirror"

# ── version of record ─────────────────────────────────────────────────
# The submission surface and nothing else. The 27-page identified companion
# (paper/main.tex and its sections) is deliberately excluded: it carries the
# author's name, affiliation, and e-mail, and it is not the submitted paper.
PAPER_FILES = [
    "paper/sp2027.tex",
    "paper/references.tex",
    "paper/sections/introduction.tex",
    "paper/sections/sp_threat_model.tex",
    "paper/sections/sp_related.tex",
    "paper/sections/sp_evaluation.tex",
    "paper/sections/design.tex",
    "paper/sections/conclusion.tex",
    "paper/sections/sp_appendix.tex",
    "paper/figures/results.tex",
    "paper/figures/grounding.tex",
    "paper/figures/ladder.tex",
    "paper/figures/architecture.tex",
    "paper/figures/funnel.tex",
    "paper/figures/generated_values.tex",
]

# The checks the appendix names, plus the corpora they read.
SCRIPT_FILES = [
    "scripts/bootstrap_ci.py",
    "scripts/verifier_ci_cluster_bootstrap.py",
    "scripts/gen_sp_figures.py",
    "scripts/audit_figure_geometry.py",
    "scripts/verifier_redteam.py",
    "scripts/verifier_redteam_cases.py",
    "scripts/verifier_harm_probe.py",
    "scripts/verifier_harm_cases.py",
    # Named in the appendix, so part of the version of record; tests/unit/test_anonymized_mirror.py enforces it.
    "scripts/build_anonymized_mirror.py",
]

RESULT_FILES = [
    "results/b4_baseline_zodiac_20260922.json",
    "results/external_baseline_model_coherent.json",
    "results/verifier_redteam.json",
    "results/verifier_redteam_supported_claims.json",
    "results/verifier_redteam_cross_family.json",
    "results/verifier_ci_cluster_bootstrap.json",
    "results/verifier_harm_probe.json",
    "results/bootstrap_ci.json",
    "results/stability_run1_vs_run2.json",
    "results/live_benchmark_zodiac_20260922.json",
    "results/live_benchmark_zodiac_20260922_run2.json",
    "results/vor_guarded_served_text_lower_bounds.json",
    "results/serve_provenance.json",
    "results/figure_geometry_audit.json",
    "results/hitl_audit_bench.jsonl",
    "results/sp2027_rescue/behavior_trajectory_benchmark.json",
]

DOC_FILES = [
    "docs/RAGIN_RESULTS_LEDGER_2026-10-08.md",
    "docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md",
]

SUPPORT_FILES = ["requirements-runtime.txt"]

# Never shipped, whatever the allowlist says.
EXCLUDE_PREFIXES = ("logs/", "dist/", "algorithms/", ".venv/", ".git/")
EXCLUDE_NAMES = {
    ".env",
    "cti_audit_blinding_key.json",  # unblinding key: never leaves the ops store
    "bandit-report.json",
}

_KEEP = ("AKIA", "sk-", "ghp_", "xoxb-", "npm_")


def _prefixed(prefix: str, marker: str):
    """Keep the token's identifying prefix, replace the secret body.

    The mirror must stay verdict-faithful: the verifier detects these formats
    by prefix and length, so replacing the whole match with a marker changes the
    gate's verdict. Keeping the prefix and substituting an obviously synthetic
    alphanumeric body preserves detection while shipping nothing that reads as a
    live secret.
    """
    def repl(m: re.Match[str]) -> str:
        return m.group(0)[: len(prefix)] + marker
    return repl


def _sendgrid(m: re.Match[str]) -> str:
    return "SG.REDACTEDREDACTED.REDACTEDREDACTED"


def _jwt(m: re.Match[str]) -> str:
    return "eyJREDACTEDREDACTEDRED.eyJREDACTEDREDACTED.REDACTEDREDACTEDRED"


_PEM_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
)


def _pem(m: re.Match[str]) -> str:
    """Keep the BEGIN/END scaffold, replace the key body with one marker line.

    Single-line on purpose: these corpora are Python source, so a replacement
    containing a raw newline would produce an unterminated string literal in the
    mirrored file. The scaffold is what the gate matches on, so keeping it
    preserves the verdict.
    """
    return _PEM_RE.sub("REDACTEDREDACTEDREDACTEDREDACTEDREDACTED", m.group(0))


# ── redaction rules ──────────────────────────────────────────────────
REDACTIONS: list[tuple[str, re.Pattern[str], object]] = [
    (
        "author-email",
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "[anonymised-email]",
    ),
    (
        "author-name",
        re.compile(
            r"Youssef\s+Hamdi\s+Zaf(?:aan)?(?:\s+Ibrahim)?|Hamdi\s+Zaf(?:aan)?(?:\s+Ibrahim)?",
            re.IGNORECASE,
        ),
        "[anonymised-author]",
    ),
    ("author-affiliation", re.compile(r"\bBenha\s+University\b"), "[anonymised-affiliation]"),
    ("coauthor-name", re.compile(r"Mohammed\s+Khalaf\s+Salama"), "[anonymised-author]"),
    ("home-path", re.compile(r"/home/[A-Za-z0-9._-]+/"), "/home/[anonymised-user]/"),
    ("workspace-path", re.compile(r"/Users/[A-Za-z0-9._-]+/"), "/Users/[anonymised-user]/"),
    (
        "azure-subscription",
        re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
        "[anonymised-subscription-id]",
    ),
    (
        "azure-hostname",
        re.compile(r"\b[a-z0-9-]+\.(?:eastus|westus2|northcentralus|qatarcentral)\.azurecontainer\.io\b"),
        "[anonymised-endpoint]",
    ),
    (
        "azure-resource-group",
        re.compile(r"\brg-youseef[a-z0-9-]*\b|\bragin-honeypot-rg\b"),
        "[anonymised-resource-group]",
    ),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{12,20}\b"), _prefixed(_KEEP[0], "REDACTEDREDACTED")),
    ("openai-style-key", re.compile(r"\bsk-(?:proj|svc|admin)?-?[A-Za-z0-9_-]{16,}\b"), _prefixed(_KEEP[1], "REDACTEDREDACTED")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), _prefixed(_KEEP[2], "REDACTEDREDACTEDREDACTED")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), _prefixed(_KEEP[3], "REDACTEDREDACTED")),
    ("npm-token", re.compile(r"\bnpm_[A-Za-z0-9]{20,}\b"), _prefixed(_KEEP[4], "REDACTEDREDACTED")),
    ("sendgrid-key", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b"), _sendgrid),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), _jwt),
    (
        "private-key-block",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
        _pem,
    ),
]


def _drop_redacted_pem(body: str) -> str:
    """Remove a PEM block whose body is fully redacted; keep any other intact.

    The gate detects a key by its BEGIN/END scaffold, so a format-preserving
    redaction must keep the scaffold to stay verdict-faithful. The scaffold on
    its own is structure, not key material, so it is allowed only when the body
    between the markers carries the redaction marker.
    """
    return _PEM_RE.sub(lambda m: "" if "REDACTED" in m.group(0) else m.group(0), body)


TEXT_SUFFIXES = {".tex", ".py", ".json", ".jsonl", ".md", ".txt", ".cfg", ".yaml", ".yml", ".sh"}
REDACTION_LOG_NAME = "REDACTIONS.json"


def is_excluded(rel: str) -> bool:
    return rel.startswith(EXCLUDE_PREFIXES) or Path(rel).name in EXCLUDE_NAMES


def collect() -> tuple[list[str], list[str]]:
    wanted = PAPER_FILES + SCRIPT_FILES + RESULT_FILES + DOC_FILES + SUPPORT_FILES
    included, missing = [], []
    for rel in wanted:
        if is_excluded(rel):
            missing.append(f"{rel} (excluded by policy)")
        elif (ROOT / rel).is_file():
            included.append(rel)
        else:
            missing.append(f"{rel} (NOT FOUND)")
    return included, missing


def redact(text: str) -> tuple[str, dict[str, int]]:
    hits: dict[str, int] = {}
    for label, pattern, replacement in REDACTIONS:
        text, n = pattern.subn(replacement, text)
        if n:
            hits[label] = hits.get(label, 0) + n
    return text, hits


def build() -> int:
    included, missing = collect()
    print(f"version of record: {len(included)} files")
    for note in missing:
        print(f"  SKIP {note}")

    if DIST.exists():
        shutil.rmtree(DIST)
    bundle = DIST / BUNDLE_NAME
    bundle.mkdir(parents=True)

    redaction_log: dict[str, dict[str, int]] = {}
    failures: list[str] = []

    for rel in included:
        src = ROOT / rel
        dst = bundle / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in TEXT_SUFFIXES:
            original = src.read_text(errors="replace")
            cleaned, hits = redact(original)
            if hits:
                redaction_log[rel] = hits
            if cleaned == original and not rel.endswith(Path(__file__).name):
                # A file whose source contained a banned token but came through
                # unchanged would mean a rule silently failed. This file is exempt
                # because it defines the rules; the survivor scan still covers it.
                for label, pattern, _ in REDACTIONS:
                    if pattern.search(original):
                        failures.append(f"{rel}: rule '{label}' matched source but output unchanged")
                        break
            dst.write_text(cleaned)
        else:
            shutil.copy2(src, dst)

    (bundle / REDACTION_LOG_NAME).write_text(
        json.dumps(
            {
                "note": (
                    "Redaction applied to the anonymised mirror only; the author's "
                    "repository of record is unmodified. Credential-shaped strings "
                    "are redacted here because a public artifact must not ship "
                    "anything that reads as a live secret, including registered "
                    "bait canaries."
                ),
                "rules": [label for label, _, _ in REDACTIONS],
                "files": redaction_log,
            },
            indent=2,
        )
        + "\n"
    )

    # ── verification ───────────────────────────────────────────────────
    appendix = (ROOT / "paper/sections/sp_appendix.tex").read_text()
    targets = sorted(set(re.findall(r"\\path\{([^}]+)\}", appendix)))
    unresolved = []
    for target in targets:
        if not (bundle / target).exists():
            candidate = next((r for r in included if r.endswith(Path(target).name)), None)
            if candidate:
                unresolved.append(f"{target} (bundled as {candidate})")
            else:
                unresolved.append(f"{target} (absent from bundle)")
    if unresolved:
        failures.extend(f"appendix path unresolved: {u}" for u in unresolved)

    survivors: list[str] = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or path.name == REDACTION_LOG_NAME:
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        body = path.read_text(errors="replace")
        # A format-preserving placeholder still matches its own pattern, so scan
        # for material that is not a placeholder: drop every token carrying the
        # redaction marker first, then look for real secrets in what remains.
        body = _drop_redacted_pem(body)
        body = re.sub(r"\S*REDACTED\S*", " ", body)
        for label, pattern, _ in REDACTIONS:
            m = pattern.search(body)
            if m:
                survivors.append(f"{path.relative_to(bundle)}: {label} -> {m.group(0)[:40]!r}")
    if survivors:
        failures.extend(f"banned token survived: {s}" for s in survivors)

    manifest = {
        "artifact": BUNDLE_NAME,
        "purpose": "anonymised mirror of the S&P submission's version of record",
        "file_count": len(included),
        "sha256": {
            rel: hashlib.sha256((bundle / rel).read_bytes()).hexdigest() for rel in included
        },
        "appendix_path_targets": targets,
        "excluded_by_policy": missing,
        "redaction_log": REDACTION_LOG_NAME,
        "verification": {
            "appendix_paths_resolved": not unresolved,
            "banned_tokens_surviving": len(survivors),
            "redaction_failures": failures,
            "verdict": "PASS" if not failures else "FAIL",
        },
    }
    (bundle / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (DIST / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    tar_path = DIST / f"{BUNDLE_NAME}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(bundle, arcname=BUNDLE_NAME)

    print(f"\nappendix path targets: {len(targets)} checked")
    print(f"files redacted: {len(redaction_log)}")
    for rel, hits in sorted(redaction_log.items()):
        print(f"  {rel}: {', '.join(f'{k}x{v}' for k, v in sorted(hits.items()))}")
    print(f"\nbundle:  {bundle}")
    print(f"tarball: {tar_path}  ({tar_path.stat().st_size / 1024:.0f} KiB)")
    print(f"verdict: {manifest['verification']['verdict']}")
    for f in failures:
        print(f"  FAIL {f}")
    return 0 if not failures else 1


def verify_existing() -> int:
    manifest_path = DIST / "MANIFEST.json"
    if not manifest_path.exists():
        print("FAIL no mirror built; run without --check first")
        return 1
    manifest = json.loads(manifest_path.read_text())
    bundle = DIST / BUNDLE_NAME
    failures = []
    for rel, digest in manifest["sha256"].items():
        path = bundle / rel
        if not path.exists():
            failures.append(f"missing {rel}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            failures.append(f"hash mismatch {rel}")
    scans = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        body = _drop_redacted_pem(path.read_text(errors="replace"))
        body = re.sub(r"\S*REDACTED\S*", " ", body)
        scans.append({"rel": str(path.relative_to(bundle)), "probe": body})
    for label, pattern, _ in REDACTIONS:
        for path in scans:
            if pattern.search(path["probe"]):
                failures.append(f"banned token {label} in {path['rel']}")
    print(f"verdict: {'PASS' if not failures else 'FAIL'} ({len(manifest['sha256'])} files)")
    for f in failures:
        print(f"  FAIL {f}")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="verify an existing build without rebuilding")
    args = ap.parse_args()
    return verify_existing() if args.check else build()


if __name__ == "__main__":
    raise SystemExit(main())
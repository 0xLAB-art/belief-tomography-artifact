#!/usr/bin/env python3
"""Release artifact path validator — closes review finding F3/F10 locally.

Parses canonical artifact references (``\\path{...}``) out of the S&P
canonical appendix (``paper/sections/sp_appendix.tex``) and checks, from the
repository root:

1. Every reference that names an artifact/script/manuscript path must carry
   an explicit top-level prefix (``results/``, ``scripts/``, ``paper/``,
   ``data/``, ``docs/``). A bare name such as ``b4_baseline_zodiac_20260922.json``
   is flagged as a missing ``results/`` prefix defect — it does not resolve
   from the repo root as written.
2. Every prefixed reference must resolve to a file (or directory for
   ``*/``-suffixed entries) that exists at that resolved path.
3. Every bare reference must still have its payload present under
   ``results/`` — otherwise it is a missing-file defect as well as a
   prefix defect.

Read-only: never writes, copies, or edits any repository file. Fully offline.

Usage::

    python scripts/validate_release_artifacts.py
    python scripts/validate_release_artifacts.py --tex paper/sections/sp_appendix.tex \
        --results-dir results --root .

Exit codes: 0 — no path defects; 1 — at least one prefix or missing-file
defect, or the tex source could not be read.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Top-level prefixes that are valid for canonical artifact references.
CANONICAL_PREFIXES = ("results/", "scripts/", "paper/", "data/", "docs/")

_PATH_RE = re.compile(r"\\path\{([^}]+)\}")


@dataclass
class Finding:
    reference: str
    kind: str  # "missing_prefix" | "missing_file"
    detail: str


@dataclass
class ValidationReport:
    tex: Path
    references: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    def by_kind(self, kind: str) -> list[Finding]:
        return [f for f in self.findings if f.kind == kind]


def extract_references(tex_text: str) -> list[str]:
    """Return every ``\\path{...}`` payload, in document order, deduplicated."""
    seen: list[str] = []
    for match in _PATH_RE.finditer(tex_text):
        token = match.group(1).strip()
        if token and token not in seen:
            seen.append(token)
    return seen


def validate_references(
    references: list[str],
    *,
    root: Path,
    results_dir: Path,
) -> list[Finding]:
    """Check each reference for canonical prefixing and file existence."""
    findings: list[Finding] = []
    for ref in references:
        if ref.startswith(CANONICAL_PREFIXES):
            target = root / ref
            if not target.exists():
                findings.append(
                    Finding(
                        reference=ref,
                        kind="missing_file",
                        detail=f"prefixed path does not exist at {target}",
                    )
                )
            continue

        # Bare reference: first a prefix defect, then a payload check.
        findings.append(
            Finding(
                reference=ref,
                kind="missing_prefix",
                detail=(
                    f"no canonical top-level prefix ({', '.join(CANONICAL_PREFIXES)}); "
                    f"as written it does not resolve from the repository root"
                ),
            )
        )
        payload = results_dir / ref
        if not payload.exists():
            findings.append(
                Finding(
                    reference=ref,
                    kind="missing_file",
                    detail=f"bare payload not found under {results_dir}",
                )
            )
    return findings


def validate(
    tex: Path,
    *,
    root: Path,
    results_dir: Path,
) -> ValidationReport:
    report = ValidationReport(tex=tex)
    try:
        text = tex.read_text(encoding="utf-8")
    except OSError as exc:
        report.findings.append(
            Finding(reference=str(tex), kind="missing_file", detail=str(exc))
        )
        return report
    report.references = extract_references(text)
    report.findings = validate_references(report.references, root=root, results_dir=results_dir)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--tex",
        type=Path,
        default=ROOT / "paper" / "sections" / "sp_appendix.tex",
        help="Canonical appendix tex source (default: paper/sections/sp_appendix.tex).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root used to resolve prefixed references.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT / "results",
        help="Directory bare artifact names are expected to live under.",
    )
    args = parser.parse_args(argv)

    report = validate(args.tex, root=args.root, results_dir=args.results_dir)

    print(f"tex: {report.tex}")
    print(f"references extracted: {len(report.references)}")
    for ref in report.references:
        print(f"  - {ref}")

    prefix_findings = report.by_kind("missing_prefix")
    missing_findings = report.by_kind("missing_file")
    if prefix_findings:
        print(f"\nMISSING-PREFIX defects ({len(prefix_findings)}):")
        for finding in prefix_findings:
            print(f"  [missing results/ prefix] {finding.reference}")
    if missing_findings:
        print(f"\nMISSING-FILE defects ({len(missing_findings)}):")
        for finding in missing_findings:
            print(f"  [missing file] {finding.reference}: {finding.detail}")

    if report.ok:
        print("\nPASS: all canonical references resolve from the repository root.")
        return 0
    print(
        f"\nFAIL: {len(prefix_findings)} missing-prefix, "
        f"{len(missing_findings)} missing-file defect(s)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

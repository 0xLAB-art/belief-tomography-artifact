#!/usr/bin/env python3
"""Render the TDSC validation-status section of the results snapshot doc.

Reads the three validation artifact JSONs plus the persisted apmix quota
probe and emits markdown to stdout. azure_healthcheck.sh appends this to
results/azure_services_snapshot.md so the doc's numbers always come straight
from the artifacts — never hand-copied figures that rot.

Standalone usage: python3 scripts/render_validation_section.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(rel: str) -> dict | None:
    path = ROOT / rel
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _check(mark: bool | None) -> str:
    return "✅" if mark else ("❌" if mark is not None else "⚠️")


def main() -> int:
    c1 = _load("results/graph_consistency_bench.json")
    abl = _load("results/ablation_battery.json")
    c3 = _load("results/mtp_steering_eval.json")
    quota = _load("results/apmix_quota_status.json")

    lines = [
        "## TDSC validation artifacts",
        "",
        "Numbers are rendered directly from the artifact JSONs by",
        "`scripts/render_validation_section.py` — refresh via `scripts/azure_healthcheck.sh`.",
        "",
    ]

    # ── C1 ──
    if c1 and "c1_proofs" in c1:
        proofs = c1["c1_proofs"]
        rows = []
        for pid, pr in proofs.items():
            if pid == "C1_baseline_gap":
                # Coverage lives in the prose note (full=45/45, none=0) —
                # extract it rather than inventing a key.
                note = pr.get("note", "")
                import re

                m = re.search(r"full=([^,]+), none=([^,.]+)", note)
                coverage = f"verifier coverage full={m.group(1)} vs none={m.group(2)}" if m else pr.get("note", "")
                rows.append(f"| {pid} | {pr.get('metric', '')} | {coverage} | {_check(pr.get('passes'))} |")
            else:
                rows.append(
                    f"| {pid} | {pr.get('metric', '')} | {pr.get('value', '?')}"
                    f" (target {pr.get('target', '?')}) | {_check(pr.get('passes'))} |"
                )
        lines += [
            "### C1 — fiction-graph consistency (`graph_consistency_bench.json`)",
            "",
            "| Proof | Metric | Value | Status |",
            "|---|---|---|---|",
            *rows,
            "",
        ]
    else:
        lines += [
            "### C1 — fiction-graph consistency",
            "",
            "_artifact missing (`results/graph_consistency_bench.json`)_",
            "",
        ]

    # ── Ablations ──
    if abl and "ablation_proofs" in abl:
        rows = []
        for aid, pr in abl["ablation_proofs"].items():
            if pr.get("equivalent"):
                state = "✅ EQUIVALENT"
            elif pr.get("degrades"):
                state = "✅ DEGRADES-AS-EXPECTED"
            else:
                state = "❌"
            rows.append(f"| {aid} | {pr.get('metric', '')} | {state} |")
        lines += [
            "### §5 — ablation battery (`ablation_battery.json`)",
            "",
            "| Ablation | Target metric | Result |",
            "|---|---|---|",
            *rows,
            "",
        ]
    else:
        lines += ["### §5 — ablation battery", "", "_artifact missing (`results/ablation_battery.json`)_", ""]

    # ── C3 ──
    if c3 and "proofs" in c3:
        rows = [
            f"| {p['id']} | {p.get('claim', '')} | {p.get('value', '?')}"
            f" (target {p.get('target', '?')}) | {_check(p.get('pass'))} |"
            for p in c3["proofs"]
        ]
        acc = c3.get("next_ttp_accuracy", {})
        lines += [
            "### C3 — MITRE predictive baiting (`mtp_steering_eval.json`)",
            "",
            f"Next-TTP accuracy: top-1 {acc.get('top1_accuracy', '?')}"
            f" · top-3 {acc.get('top3_accuracy', '?')} · MRR {acc.get('mrr', '?')}"
            f" over {acc.get('predictions', '?')} predictions",
            "",
            "| Proof | Claim | Value | Status |",
            "|---|---|---|---|",
            *rows,
            "",
        ]
    else:
        lines += ["### C3 — MITRE predictive baiting", "", "_artifact missing (`results/mtp_steering_eval.json`)_", ""]

    # ── Bootstrap/Wilson CIs ──
    ci = _load("results/bootstrap_ci.json")
    if ci and "proofs" in ci:
        rows = [f"| {p['id']} | {p.get('detail', '')} | {_check(p.get('ok'))} |" for p in ci["proofs"]]
        live = ci.get("live_audited", {})
        comp = live.get("composite", {}).get("mean_ci", {})
        ci_lines = [
            "### Statistical intervals (`bootstrap_ci.json`)",
            "",
            f"Disk-provable 218-row composite: **{comp.get('point', '?')}"
            f" [{comp.get('lo', '?')}, {comp.get('hi', '?')}]** (95%).",
            "",
            "| Proof | Detail | Status |",
            "|---|---|---|",
            *rows,
            "",
        ]
        prov = ci.get("headline_provenance", {})
        if prov:
            status = prov.get("status", "")
            if status.startswith("RESOLVED"):
                src = ci.get("live_audited", {}).get("source", "?")
                ci_lines += [
                    f"✅ 0.855 provenance **resolved**: superseded by the persisted `{src}` run —",
                    "cite that artifact's composite instead.",
                    "",
                ]
            elif prov.get("claimed_composite_0.855", "").startswith("PROVENANCE_MISSING"):
                ci_lines += [
                    "⚠️ The reported **0.855** live composite cites a deleted `/tmp` artifact and is not",
                    "re-derivable offline — re-derive at the quota-gated re-run before citing.",
                    "",
                ]
        lines += ci_lines
    else:
        lines += [
            "### Statistical intervals",
            "",
            "_artifact missing (`results/bootstrap_ci.json`) — run `scripts/bootstrap_ci.py`_",
            "",
        ]

    # ── Run-to-run stability ──
    stab = _load("results/stability_run1_vs_run2.json")
    if stab and "composite" in stab:
        comp = stab["composite"]
        icon = "✅" if comp.get("verdict") == "stable" else "⚠️"
        lines += [
            "### Run-to-run stability (`stability_run1_vs_run2.json`)",
            "",
            f"{icon} Two independent 218-query runs (same corpus/engine/wiring): composite "
            f"**{comp.get('composite_run_a')} vs {comp.get('composite_run_b')}** "
            f"(delta {comp.get('delta'):+.4f}, per-row MAD {comp.get('mean_abs_row_diff'):.4f}, "
            f"pass-decision agreement {comp.get('pass_agreement'):.3f}) — verdict **{comp.get('verdict')}**.",
            "",
        ]

    # ── Quota / live re-run ──
    lines += ["### Live-LLM re-run readiness (apmix)", ""]
    if quota:
        # Two writers share this file: check_apmix_catalog.py (rich schema:
        # quota_status/quota_http/models_wired) and run_zodiac_eval.sh gate 5
        # (now the same rich schema; legacy status/http_code/model kept).
        # Read both either way.
        status = quota.get("status") or quota.get("quota_status", "unknown")
        http_code = quota.get("http_code") or quota.get("quota_http", "?")
        model = quota.get("model") or ", ".join(dict.fromkeys(quota.get("models_wired", []))) or "?"
        icon = {"live": "✅", "exhausted": "⏳"}.get(status, "⚠️")
        lines.append(
            f"- {icon} quota **{status}** (probed {quota.get('checked_at', '?')}, "
            f"model `{model}`, HTTP {http_code})"
        )
        if quota.get("catalog_status") == "ok" and status != "live":
            n_models = len(quota.get("catalog_models", []))
            lines.append(
                f"- catalog **ok** ({n_models} models, wired models present) — only quota blocks the re-run"
            )
    else:
        lines.append("- ⚠️ no quota probe recorded yet — run `scripts/run_zodiac_eval.sh --smoke` to probe")
    lines += [
        "- Wiring: generator/don `deepseek-v4-flash-free`, judge `grok-4.7-free` (independent judge)",
        "- One command at reset: `./scripts/run_zodiac_eval.sh --smoke` → full run if clean",
        "",
    ]

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

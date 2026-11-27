"""Panel program orchestrator — one detached process, gate-serialized.

Phase 1: out-of-sample verifier probes (fast deliverable).
Phase 2: cross-family jury (claude-sonnet-5-5, 120 cases, ~2 h).
Phase 3: v3 A/B run (10 sessions per arm, interleaved, ~7-9 h).

All three share the beatapi 1-successful-request-per-minute budget through
scripts/beatapi_gate.py; this process runs them strictly sequentially so the
budget is never contended. Jobs are invoked as in-process function calls
(no subprocess); dynamic values are whitelisted identifiers and integers.
State checkpoints to results/panel_v3/program_state.json.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

STATE = ROOT / "results/panel_v3/program_state.json"

PERSONAS = ("novice_scriptkiddie", "recon_operator", "credential_hunter",
            "apt_patient", "evasion_probe")
ARMS = ("A", "C")


def _save(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps(state, indent=2))


def main() -> int:
    state = json.loads(STATE.read_text()) if STATE.exists() else {
        "phase": 0, "started_at": datetime.now(timezone.utc).isoformat(),
        "v3": {"pairs_done": []}}
    _save(state)

    if state["phase"] < 1:
        import panel_out_of_sample
        state["oos_rc"] = panel_out_of_sample.main()
        state["phase"] = 1
        _save(state)

    if state["phase"] < 2:
        import ai_jury_crossfamily
        state["jury_rc"] = ai_jury_crossfamily.main()
        state["phase"] = 2
        _save(state)

    if state["phase"] < 3:
        import hashlib
        import field_attack_driver_v3 as d3
        pairs = [(p, r) for r in (1, 2) for p in PERSONAS]
        order = sorted(pairs, key=lambda pr: hashlib.sha256(
            f"20261030:{pr[0]}:{pr[1]}".encode()).hexdigest())
        for persona, run_id in order:
            assert persona in PERSONAS and isinstance(run_id, int)
            done = state["v3"].get("pairs_done", [])
            for arm in ARMS:
                if [persona, run_id, arm] in done:
                    continue
                port = 2221 if arm == "A" else 2223
                rc = d3.main(["--persona", persona, "--run-id", str(run_id),
                              "--arm", arm, "--port", str(port)])
                state["v3"].setdefault("pairs_done", []).append(
                    [persona, run_id, arm])
                state["v3"][f"rc_{arm}_{persona}_{run_id}"] = rc
                _save(state)
        state["phase"] = 3
        _save(state)

    if state["phase"] >= 3:
        import field_attack_stats_v3
        state["stats_rc"] = field_attack_stats_v3.main([])
        _save(state)
    print("[program] complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

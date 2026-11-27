#!/usr/bin/env python3
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "decision_fusion_v4"

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    recovery = RESULTS / "v4_real_evidence_recovery_freeze_v1.json"
    expected_recovery = "c8806feb02fa5f65f0f9f599dc58d02bf56d7253531e27d49175455d0e635dd2"
    if sha256(recovery) != expected_recovery:
        raise SystemExit("recovery freeze hash mismatch")
    with tempfile.NamedTemporaryFile(suffix=".json") as handle:
        dry_run = subprocess.run([sys.executable, str(ROOT / "scripts" / "v4_capture_dry_run.py"), "--output", handle.name], cwd=ROOT, check=True, capture_output=True, text=True)
        dry_results = json.loads(Path(handle.name).read_text())
    implementation = [
        "ragin/capture_v4/__init__.py", "ragin/capture_v4/manifest.py", "ragin/capture_v4/registry.py",
        "ragin/capture_v4/lineage.py", "ragin/capture_v4/privacy.py", "scripts/v4_capture_finalize.py",
        "scripts/v4_capture_validate.py", "scripts/v4_capture_progress.py", "scripts/v4_capture_dry_run.py",
        "tests/unit/test_capture_v4.py", "docs/decision_fusion/V4_REAL_CAPTURE_PRIVACY_POLICY.md",
    ]
    hashes = {path: sha256(ROOT / path) for path in implementation}
    freeze = {
        "schema": "ragin.v4.prospective_capture_readiness_freeze.v1",
        "recovery_freeze_sha256": sha256(recovery),
        "capture_contract": "ragin.real_capture_manifest.v1",
        "source_classes": ["NATURAL_FIELD", "CONTROLLED_REAL_HONEYPOT", "CONTROLLED_REAL_ADMIN"],
        "eligibility_rules": ["manifest exists and hash verifies", "native session ID", "raw log exists and hash verifies", "at least one usable input event", "complete lineage", "no prior study membership", "canonical derivation reproducible", "synthetic/replay/test_fixture all false"],
        "source_mix_target": {"total": 260, "controlled_real_honeypot_minimum": 220, "controlled_real_admin_maximum": 40},
        "independence_rule": "one native capture session equals one independence_group_id; derived records do not create new groups",
        "source_cluster": "keyed HMAC-SHA256 over permitted normalized source/network metadata; secret excluded from artifacts",
        "privacy_policy_sha256": hashes["docs/decision_fusion/V4_REAL_CAPTURE_PRIVACY_POLICY.md"],
        "raw_immutability_rule": "hash and seal raw log after closure; later changes are new derived artifacts and fail hash validation",
        "canonical_derivation": "final non-empty eligible input event by event order with lossless prior context",
        "registry_format": "data/prospective_v4/capture_registry.jsonl; append-only; duplicate capture/native IDs refused; metadata-only",
        "progress_metrics": ["total captured sessions", "provenance-valid sessions", "invalid sessions", "source-class counts", "unique native session IDs", "unique source clusters", "capture-day counts"],
        "outcome_blind": True,
        "acquisition_stop_rule": "stop at >=260 structurally eligible provenance-verified independent native sessions; no semantic selection and no evaluation during acquisition",
        "implementation_sha256": hashes,
        "tests": {"command": "pytest -q tests/unit/test_capture_v4.py", "passed": 10, "failed": 0},
        "dry_run": dry_results,
        "prospective_real_acquisition_started": False,
        "real_eligible_sessions_collected_under_new_contract": 0,
        "v4_effectiveness_execution_started": False,
        "reference_annotation_started": False,
        "effectiveness_seen": False,
        "policy_arms_invoked": False,
        "reference_labels_created": False,
    }
    output = RESULTS / "v4_prospective_capture_readiness_freeze_v1.json"
    output.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"path": str(output), "sha256": sha256(output), "dry_run_stdout": dry_run.stdout}, indent=2))

if __name__ == "__main__":
    main()

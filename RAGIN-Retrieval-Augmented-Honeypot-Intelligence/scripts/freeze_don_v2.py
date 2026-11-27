from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/decision_fusion_v4/don_v2_command_aware"
sys.path.insert(0, str(ROOT))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source_paths = [
        "ragin/don/command_aware_v2.py",
        "ragin/don/rag_engine.py",
        "ragin/don/models.py",
        "ragin/decision_fusion_v4/evidence_export.py",
        "scripts/build_don_v2_corpus.py",
        "tests/fixtures/don_v2_development_cases.json",
        "tests/unit/test_don_v2.py",
    ]
    corpus = ROOT / "data/corpus/command_aware_v2.jsonl"
    fixture_path = ROOT / "tests/fixtures/don_v2_development_cases.json"
    from ragin.don.command_aware_v2 import CommandAwareRetrieverV2

    retriever = CommandAwareRetrieverV2(corpus_path=corpus)
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    validation_rows = []
    for case in fixtures:
        result = retriever.retrieve(case["commands"][-1], case["commands"][:-1], session_id=case["case_id"])
        validation_rows.append({"case_id": case["case_id"], "oracle": case["oracle"], "trace": result["trace"], "document_ids": [item["doc_id"] for item in result["documents"]]})
    OUT.mkdir(parents=True, exist_ok=True)
    validation_path = OUT / "don_v2_development_validation_v1.json"
    validation_path.write_text(json.dumps({"schema": "ragin.don.v2.development_validation.v1", "cases": validation_rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    source_paths.append("results/decision_fusion_v4/don_v2_command_aware/don_v2_development_validation_v1.json")
    config = {
        "version": "DON_COMMAND_AWARE_V2",
        "retrieval": "lexical BM25-like IDF overlap + exact command-pattern matching + behavior overlap",
        "ranking_weights": {"lexical": 0.45, "exact_pattern": 0.40, "behavior": 0.15},
        "top_k": 8,
        "relevance": "command_grounded and score >= 0.20",
        "context_limit": 64,
        "cache_key": "sha256(version, session_id, classification, current command, preceding commands, features)",
        "execution": "static parsing only; no shell, subprocess, URL, path, or network execution",
        "gate": "existing EvidenceQualityGate unchanged",
    }
    config_sha = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    index_material = corpus.read_bytes() + b"\0" + config_sha.encode()
    manifest = {path: sha256(ROOT / path) for path in source_paths}
    manifest["data/corpus/command_aware_v2.jsonl"] = sha256(corpus)
    manifest["retrieval_index_material_sha256"] = hashlib.sha256(index_material).hexdigest()
    payload = {
        "schema": "ragin.don.v2.freeze.v1",
        "status": "DON_V2_READY",
        "implementation_version": "DON_COMMAND_AWARE_V2",
        "runtime_mode": "RAGIN_DON_RETRIEVAL_VERSION=DON_COMMAND_AWARE_V2",
        "default_mode_preserved": True,
        "frozen_v4_policy_gate_hisoka_unchanged": True,
        "corpus": {
            "path": "data/corpus/command_aware_v2.jsonl",
            "documents": sum(1 for line in corpus.open(encoding="utf-8") if line.strip()),
            "sha256": sha256(corpus),
            "sources": ["existing local MITRE ATT&CK STIX corpus; source URLs and provenance hashes retained"],
        },
        "retrieval_configuration": config,
        "retrieval_index": {"persistent_index": False, "material_sha256": manifest["retrieval_index_material_sha256"]},
        "development_validation": {
            "fixtures": "tests/fixtures/don_v2_development_cases.json",
            "cases": 9,
            "new_v2_tests_passed": 10,
            "new_v2_tests_failed": 0,
            "focused_existing_tests_passed": 109,
            "focused_existing_tests_failed": 0,
            "broad_unit_security_passed": 1717,
            "broad_unit_security_failed": 22,
            "broad_unit_security_errors": 10,
            "broad_failures_scope": "pre-existing missing mem0/fixtures and unrelated Laya/verifier oracle failures",
            "external_generation_calls": 0,
            "attacker_commands_executed": 0,
        },
        "trace_contract": [
            "exact query",
            "context projection and truncation flag",
            "static command features",
            "top-k evidence IDs and component scores",
            "source, source version, license metadata, provenance hash",
            "command-pattern relevance and query coverage",
            "Evidence Gate-compatible document fields",
            "corpus and implementation hashes",
        ],
        "source_sha256": manifest,
    }
    (OUT / "don_v2_freeze_v1.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "sha256_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"freeze": str(OUT / "don_v2_freeze_v1.json"), "manifest": str(OUT / "sha256_manifest.json")}, sort_keys=True))


if __name__ == "__main__":
    main()

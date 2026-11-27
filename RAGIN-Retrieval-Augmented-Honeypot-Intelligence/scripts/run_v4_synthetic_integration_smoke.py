from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ragin.cycle.adapters import DonAdapter
from ragin.cycle.graph import DeceptionGraph
from ragin.decision_fusion_v4.benchmark import EvidenceQualityGate, generate_corpus
from ragin.decision_fusion_v4.policy import DeterministicPolicySelector
from ragin.decision_fusion_v4.evidence_export import sha256_json
from ragin.don.models import ClassificationLabel, IntelDocument, MITRETactic, SeverityLevel, ThreatAnalysis


class Classifier:
    def classify(self, attacker_input, session_context):
        return {"skill_level": "advanced", "confidence": 0.9}


class Analyzer:
    def __init__(self, bundle):
        self.bundle = bundle

    def analyze(self, attacker_input, session_context):
        return {"extracted_techniques": ["T1046"], "evidence_bundle": self.bundle}


class Deceiver:
    def __init__(self):
        self.contexts = []

    def generate_response(self, attacker_input, session_context):
        self.contexts.append(session_context)
        return {"response_text": "synthetic verified response", "persona_used": "advanced"}


class Verifier:
    def __init__(self):
        self.calls = 0

    def verify(self, response, session_context):
        self.calls += 1
        return {"passed": True, "issues": [], "deterministic": True}


class Engine:
    def analyze(self, request, session_log):
        return ThreatAnalysis(
            analysis_id="synthetic-analysis",
            session_id=request.session_id,
            classification=ClassificationLabel.MALICIOUS,
            severity=SeverityLevel.HIGH,
            confidence=0.9,
            sophistication_score=0.8,
            tactics=[MITRETactic(tactic_id="TA0043", tactic_name="recon", confidence=0.9, techniques=["T1046"])],
            threat_actors=[],
            iocs=[],
            intel_documents=[IntelDocument(doc_id="SMOKE-D1", title="Recon", content="network reconnaissance", source="synthetic")],
            recommendations=[],
        )


def main() -> None:
    case = next(item for item in generate_corpus("V4D-", 1, 17) if item.stratum == "valid_recon")
    bundle = case.state
    export = DonAdapter(engine=Engine()).analyze("nmap -sV 10.0.0.0/24", {"session_id": "smoke", "classification": {"skill_level": "advanced", "confidence": 0.9}})
    exported_bundle = export["evidence_bundle"]
    smoke = {
        "synthetic_only": True,
        "old_120_used": False,
        "old_169_used": False,
        "don_export_schema": exported_bundle["schema"],
        "don_export_hash": sha256_json(exported_bundle),
        "gate_export_state": EvidenceQualityGate().evaluate(bundle)["gate_state"],
        "arms": {},
    }
    for arm in ("RAGIN_V4_DETERMINISTIC", "RAGIN_V4_LOGISTIC"):
        deceiver = Deceiver()
        verifier = Verifier()
        graph = DeceptionGraph(
            classifier=Classifier(),
            analyzer=Analyzer(bundle),
            deceiver=deceiver,
            verifier=verifier,
            decision_arm=arm,
            max_retries=1,
        )
        result = graph.invoke(f"{arm}-synthetic", "nmap -sV 10.0.0.0/24", {})
        smoke["arms"][arm] = {
            "gate_state": result["policy_decision"]["gate_state"],
            "selected_response_strategy": result["policy_decision"]["selected_response_strategy"],
            "strategy_reached_generator": result["policy_decision"]["strategy_reached_generator"],
            "verification_passed": result["verification"]["passed"],
            "verifier_calls": verifier.calls,
            "accepted_response_present": bool(result["deception_response"].get("response_text")),
            "generation_strategy_block": deceiver.contexts[0]["strategy_block"],
        }
    invalid = dict(bundle)
    invalid["retrieval"] = dict(bundle["retrieval"])
    invalid["retrieval"]["retrieval_status"] = "FAILURE"
    invalid_decision = DeterministicPolicySelector().select(invalid)
    smoke["invalid_evidence"] = {
        "gate_state": invalid_decision["gate_state"],
        "selected_response_strategy": invalid_decision["selected_response_strategy"],
        "fallback_reason": invalid_decision["fallback_reason"],
    }
    path = Path("results/decision_fusion_v4/v4_synthetic_integration_smoke_v1.json")
    path.write_text(json.dumps(smoke, indent=2, sort_keys=True) + "\n")
    print(json.dumps(smoke, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

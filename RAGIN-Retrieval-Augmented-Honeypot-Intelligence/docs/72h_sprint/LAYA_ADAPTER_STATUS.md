# Laya Adapter Status

Status: CONTRACT IMPLEMENTED AND FIXTURE-TESTED; real inference deferred.

No Laya weights were downloaded or served during this phase. The optional decision-provider boundary remains separate from Hisoka generation and from the deterministic verifier. No historical JEV/OpenCode result was relabeled as Laya.

`ragin/decision/optional.py` provides a bounded `LayaAssessmentAdapter` over the existing typed `JevAssessment` contract. It records provider/model provenance, bounds input size and inference time, validates typed answers, and returns explicit `NO_SIGNAL` on timeout, malformed output, or provider failure. Three fixture tests passed; this is adapter evidence only, not Laya model evidence. Laya therefore does not block the verified serving path.

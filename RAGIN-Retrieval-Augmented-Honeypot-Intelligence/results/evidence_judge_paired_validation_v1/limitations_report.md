# Evidence Judge V1 paired validation limitations

This is a 60-scenario synthetic development comparison derived from the provenance-verified Don V2 command-aware corpus. The cases and category rules were frozen before the paired arms ran. The fixture oracle is an explicit deterministic rule, not human annotation or independent ground truth.

Arm A and Arm B use the same frozen commands, preceding command context, candidate document set, corpus hash, retrieval traces, and Evidence Gate implementation. The comparison measures filtering behavior on these fixtures only. It does not estimate real-world classification accuracy, policy correctness, retrieval effectiveness, or deployment performance.

The benchmark does not compare against Jev, Laya, learned rerankers, or standard RAG. No model inference, paid API, AWS operation, network change, or captured command execution was used. Policy V2 remains inactive, and previous frozen results were not rerun or modified.

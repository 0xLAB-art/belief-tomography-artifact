# Laya Feasibility and Adapter

## Current result

DEFERRED, not failed and not integrated. The Laya repository was inspected read-only via its Git remote. Available workstation GPU evidence: Quadro RTX 4000, 8192 MiB total, 7739 MiB free, driver `595.91.07`. No model weights were downloaded and no Laya inference was started during this checkpoint.

The read-only checkout was `NandhaKishorM/laya` main at `1adc59f7e371deb601fcfa18a14e25db238addcc`. It describes Laya as a non-autoregressive typed-decision engine, not a text generator. The published checkpoints are listed as roughly 322M and 421M parameters and the first `Router()` call downloads a checkpoint, so a reliable local benchmark needs dependency and weight acquisition before any latency/VRAM conclusion. No weights were downloaded overnight.

The existing code still contains a historical JEV assessment implementation. It was not enabled on AWS, and no JEV/OpenCode completion call was made. Laya is not Hisoka and cannot replace the deterministic verifier.

## Safe continuation contract

The next implementation step is a provider-neutral optional assessment adapter with typed outcomes:

- provider identity, model/version, and input hash;
- bounded timeout and input size;
- `NO_SIGNAL` on unavailable/timeout/error;
- no serving authorization from the assessment result;
- deterministic verifier remains mandatory;
- separate result namespace from historical JEV/OpenCode evidence.

Until that adapter and real local inference are tested, all staging response claims remain fallback-backed or directly verified application-path claims.

# Real Model Inference Results (RAGIN × Laya)

Date: 2026-10-12. These results come from an actual forward pass on real downloaded
weights — not a mock adapter, not routing-only, not cache-existence proof.

## Proof chain

1. Package: `laya==0.4.2` imported from `.venv/lib/python3.12/site-packages/laya`.
2. Weights: `~/.cache/huggingface/hub/models--convaiinnovations--laya/blobs/`
   `891102d3726…` — 842,609,210 bytes, sha256 recomputed locally and matching the
   HF blob name: `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`.
3. Revision pinned at Router construction: `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`.
4. Device: `cpu` (torch `2.14.0+cpu`; CUDA unavailable — CPU-only torch build + broken
   NVML on this workstation).
5. Raw evidence: `results/laya_research/real_inference_cpu_pilot.jsonl`
   (45 per-case records with full typed answers and latencies).

## Setup

- One `Router(device="cpu", max_loaded=1, preload=False)`, revision-pinned.
- Three typed questions mirroring the Jev contract:
  - `attack` (noul): "Is the SSH session malicious?" → `P(true)`.
  - `stage` (choice, 7 options): benign_administration / recon / persistence /
    credential_theft / lateral_movement / exfiltration / cleanup.
  - `severity` (score, 4 levels): none → low → moderate → high.
- Dataset: 45 synthetic SSH sessions with by-construction labels (25 benign admin
  transcripts, 20 malicious ones: recon, takeover, persistence, exfil, cleanup).

## Measured performance (CPU)

| metric | value |
|---|---|
| First call (route + load + infer) | 6.6–9.4 s (dominated by weight load) |
| Warm inference p50 | 1.30 s |
| Warm inference mean | 1.32 s |
| Warm inference p95 | 1.41 s |
| min / max | 1.18 s / 1.65 s |
| 45-case total | 59.6 s |
| RSS after load | ≈ 2.1 GB (2,180,076 KB) |
| Peak VRAM | n/a (CPU-only) |

## Classification quality (threshold 0.5 on noul P(true))

| metric | value |
|---|---|
| Accuracy | 0.778 (35/45) |
| Balanced accuracy | 0.76 |
| Precision | 0.857 |
| Recall | 0.60 |
| F1 | 0.706 |
| Brier | 0.151 |
| NO_SIGNAL / abstain | 0 |

Confusion: tp 12, fp 2, tn 23, fn 8 — misses cluster on subtle sessions (tar/ssh pivots
modeled as admin, single-line `sudo -l`, `iptables -F`). Notable FP: the `ping 8.8.8.8`
benign transcript (external connection reads as exfil).

Stage choice is directionally right where the model does flag malicious (recon,
persistence, credential_theft, exfiltration), but the stage head also produced false
`exploitation`/`cleanup` labels on benign transcripts — treated as advisory only.

## Calibration caveat (carried into every downstream use)

The checkpoint ships an invalid temperature for at least the `choice:11+` bucket; laya
0.4.2 itself warns confidence is uncalibrated. Consequence enforced in RAGIN: Laya's
output is an advisory signal, Jev thresholds are not transferred, and any decision
threshold must be re-fitted on held-out cybersecurity data before promotion.

## What was NOT done

No AWS, no serving endpoint, no further checkpoint downloads, no fine-tuning.

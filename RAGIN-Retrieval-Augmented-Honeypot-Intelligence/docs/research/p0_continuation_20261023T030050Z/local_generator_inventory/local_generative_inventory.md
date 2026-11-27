# Local generative-model inventory (read-only, 2026-10-23)

Scope: existing local model files/servers and hardware only. No model was loaded,
downloaded, run, or probed; no external URL was contacted; no secret/env value or
raw attacker record was read. Model file inspection is limited to names, sizes,
and small config manifests.

Artifact root: `docs/research/p0_continuation_20261023T030050Z/local_generator_inventory/`
(raw command output: `inventory.txt`).

## Bottom line

**No local open-weight generative LLM was found.** The only generative models
visible to the local Ollama daemon are `:cloud` aliases (remote inference through
Ollama cloud), not local weights. The local model assets are Laya encoder/scoring
models and Chrollo/other encoders/classifiers. Therefore B1–B3 **model execution
remains NOT ESTABLISHED**; there is no verified local generative backend for a
real LLM arm on this host as inventoried.

## Hardware

| Resource | Value |
|---|---|
| CPU | Intel Core i7-9850H, 12 logical CPUs (6 cores), x86_64 |
| RAM | 15 GiB total, ~7.5 GiB available at inventory time; 4.3 GiB swap |
| GPU | NVIDIA Quadro RTX 4000, 8192 MiB, driver 595.99.02, CUDA 13.2 |
| GPU state | ~4 MiB used, 0% utilization (no model process resident) |

This is a modest single-GPU laptop-class host. A small quantized generative
model could potentially fit, but **none is present and none was run**; capacity
is not evidence of execution.

## Generative LLM inventory

| Item | Tag | Evidence |
|---|---|---|
| `ollama serve` (PID 2672, user `ollama`, loopback `127.0.0.1:11434`) | **server, local; models remote** | process + loopback listener |
| `kimi-k3:cloud`, `kimi-k2.7-code:cloud`, `glm-5.2:cloud`, `glm-5.1:cloud`, `nemotron-3-ultra:cloud`, `nemotron-3-super:cloud`, `minimax-m3:cloud`, `minimax-m2.7:cloud`, `deepseek-v4-flash:cloud`, `gpt-oss:120b-cloud`, `qwen3.5:397b-cloud`, `gemma4:31b-cloud` | **cloud generative aliases, NOT local weights** | `ollama list` shows `:cloud`; Ollama model store is ~164 KiB of metadata blobs, no weight-sized blobs |
| Any local GGUF/SFT generative model | **none found** | no `*.gguf`/`*.ggml` under `$HOME` (maxdepth 5) or repo; no weight-sized Ollama blob |
| `vllm`, `llama.cpp`/`llama-server`, TGI, SGLang, LM Studio, LocalAI | **absent** | binaries absent; no matching process |
| `transformers` / `torch` / `sentence-transformers` Python packages | **present** | installed-package metadata only; no generative checkpoint found |

Important distinction: the Ollama server is local, but every listed model name is
a cloud alias. A successful local HTTP call would still be **cloud inference**
and is outside the allowed scope of this pass.

## Local non-generative model assets (do not count as a generative arm)

| Asset | Tag | Notes |
|---|---|---|
| `models/laya_*` (v3–v12; `model.safetensors` ~842 MB; `encoder/config.json` says `ModernBertForMaskedLM`, hidden 1024) | **local encoder/scoring model**, not a generative LLM | Laya fixed-choice/scoring runtime; disabled by default; no load/inference performed |
| `~/.cache/huggingface/hub/models--convaiinnovations--laya` (~2.6 GB with snapshots/blobs) | **local encoder cache** | same Laya family; no inference |
| `models/chrollo/rf_classifier.joblib` (~8.1 MB) and scaler/features | **local Random Forest classifier**, not generative | Chrollo skill classifier; manifest says baseline+ngram, 42 features |
| HF cache `answerdotai/ModernBERT-base`, `chopratejas/kompress-v2-base`, `sentence-transformers/all-MiniLM-L6-v2` | **local encoders/embedding**, not generative | names only; no loading |
| `results/decision_fusion_v4/*.joblib` | **local logistic policy artifacts**, not generative | decision fusion |

## Scope / claim boundary

- This inventory establishes **presence/absence at file/process level only**.
- It does **not** establish that any model can be loaded, fits in 8 GiB VRAM,
  produces valid SSH replies, or satisfies the strict verifier.
- No model weights were hashed as "validated" beyond file presence; a future
  B0–B3 pilot must load and verify a pinned local checkpoint explicitly.
- No local generative backend is available for a "true LLM arm" without a
  download (forbidden this pass) or cloud inference (forbidden/out of scope).

## Exact verifier policy hooks for eval integration

| Hook | Values / default | Notes |
|---|---|---|
| `RAGIN_VERIFIER_PROFILE` | `legacy` (default) or `research_strict_v1` | Same value across B1–B5; invalid value raises at harness construction (fail closed). |
| `RAGIN_VERIFIER_DEADLINE_S` | float, `0 < x <= 60`, research default `1.0` | Wall-clock bound for the whole verification call, including input snapshot; invalid value raises. |
| Python override | `Harness(..., verifier_profile=..., verifier_deadline_s=...)` | Explicit args take precedence over env; useful for tests. |
| Policy introspection | `harness.verification_policy` / `Harness._strict_verify` verdict key `verification_policy` | Reports `{profile, deadline_s, deadline_enforced, source}`. |

Strict profile requires an authoritative pinned identity snapshot injected by
the harness (`pinned_identity`); it does not fall back to skill-derived identity.
Current v1 contract covers only exact `whoami`, `id` variants, `hostname`
variants, `uname` variants, and `cat /etc/os-release`/`/usr/lib/os-release` with
pinned Ubuntu 22.04 identity. `date`/`uptime` are intentionally excluded from v1
because shape alone is not pinned evidence. Unsupported/compound/encoded/
wrapper inputs fail closed rather than being reduced to a supported command.

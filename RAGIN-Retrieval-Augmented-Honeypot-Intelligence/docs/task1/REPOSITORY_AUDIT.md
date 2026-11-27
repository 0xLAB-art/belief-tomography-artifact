# RAGIN Task 1: Repository Audit

**Audit date:** 2026-10-08
**Audited repository:** `/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence`
**Auditor scope:** read-only repository, source, configuration, test, and persisted-evidence inspection. No AWS, deployment, external target, paid API, or business-logic changes were performed.

## Executive result

The repository contains a substantial Python/Rust research prototype and several partially overlapping serving paths. The intended verified pipeline is present as a LangGraph implementation, but it is not the path used by `server_v2`'s field entry point, and the legacy HTTP server serves generated text without a verifier gate. The proposed EDGE/CORE/LOCAL deployment is not represented as an AWS/VPC/IaC configuration. A safe public deployment is therefore **blocked**.

## Repository boundary and status

The working directory is a wrapper containing a nested Git repository. The audited Git root is the nested path above.

| Item | Observed value |
|---|---|
| HEAD | `f01a4a98d8fc0cdbf1f031d915385294675e3b1b` |
| Last commit | `2026-09-29 17:52:32 +0300`, `paper: three reviewer fixes before freeze - attribution claim, corpus wording, hyphen` |
| Pre-existing tracked modifications | 50 modified/staged paths at audit start; preserved |
| Pre-existing untracked entries | 2,010 entries at audit start; preserved |
| Tracked inventory | 4,733 `.jsonl`, 395 `.json`, 230 `.py`, 194 result paths, 55 `.md`, 36 `.pdf`, 24 `.tex`, 22 `.yml`, 10 `.rs` files, among other extensions |
| Audit mutation | Only the seven files in `docs/task1/` were created |

The worktree is not a clean release snapshot. Existing results, session records, manuscript artifacts, scripts, and application changes must not be attributed to this audit.

## Top-level structure

| Path | Role observed from source |
|---|---|
| `ragin/` | Python package: classification, CTI/RAG, deception, graph, gateway client, JEV, session/cycle, monitoring, auth, and servers |
| `ragin/server.py` | Legacy component server; Docker default entry point |
| `ragin/server_v2.py` | Field/pipeline HTTP server and Cowrie-compatible bridge |
| `ragin/cycle/` | `Harness`, `Sandbox`, `Session`, verifier, HITL, LangGraph orchestration, adapters |
| `ragin/chrollo/`, `ragin/don/`, `ragin/hisoka/` | Behavioral classifier, CTI/retrieval analysis, generative deception |
| `ragin/graph/` | Fiction and host-fiction state/verifier implementations |
| `ragin/jev/` | JEV client, typed schema, assessment, and additive routing/review wrappers |
| `ragin/gateway/` | OpenAI-compatible provider client and retry/timeout behavior |
| `llm-gateway/` | Separate Rust gateway with provider routing, rate limiting, validation, metrics, and model catalog |
| `data/`, `models/`, `results/` | Training/evaluation inputs, model artifacts, generated/persisted research outputs |
| `scripts/` | Benchmarks, audits, deployment/provisioning, data collection, and historical experiments |
| `tests/` | Pytest unit, integration, security, benchmark, and artifact tests |
| `paper/` | Manuscript sources and generated publication artifacts |
| `docker-compose*.yml`, `Dockerfile*` | Main, production, field, VM, and Python/Rust container variants |
| `docs/` | Architecture, ethics, results ledgers, release manifests, plans, and audit notes |

## Entry points and execution modes

1. `Dockerfile.python` runs `python3 -m ragin.server`.
2. Main `docker-compose.yml` runs `ragin.server --component chrollo|don|hisoka|jev` as separate services and publishes multiple ports.
3. `docker-compose.field.yml` publishes only the Cowrie SSH listener and runs `python -m ragin.server_v2 --mode pipeline` for the RAGIN arm. Its comments describe a verified loop, but `server_v2._init_pipeline` constructs `Harness` without a verifier.
4. `docker-compose.vm.yml` is an Azure-oriented component deployment, not the requested AWS two-node architecture.
5. `scripts/install_zodiac_stack.sh` is a local/Tailscale-oriented component stack and does not wire `server_v2` or the verifier.
6. `llm-gateway/` is a separate Rust service, configured by `llm-gateway/config.toml`, with `llm-gateway/src/main.rs` as its HTTP entry point.

## Languages and dependencies

### Python

`pyproject.toml` declares project version `1.0.0`, Python `>=3.10`, and runtime dependencies including Pydantic, scikit-learn, NumPy, pandas, sentence-transformers, HTTP clients, PyYAML, dotenv, aiohttp, Prometheus, Mem0, and LangGraph. Test/development extras include pytest, pytest-asyncio, pytest-cov, pytest-xdist, Ruff, Bandit, pip-audit, mypy, and pre-commit.

The active virtual environment was inspected without installation. It reports Python 3.12.3 and, among others: Pydantic 2.13.5, scikit-learn 1.9.1, NumPy 2.5.3, pandas 3.0.5, sentence-transformers 6.0.1, httpx 0.28.1, aiohttp 3.14.3, LangGraph 1.2.11, pytest 9.1.1, pytest-asyncio 1.4.0, pytest-cov 7.1.0, Ruff 0.16.7, and mypy 2.3.1. These are environment observations, not a lockfile or reproducibility guarantee.

### Rust

`llm-gateway/Cargo.toml` declares edition 2021, version `0.1.0`, Tokio, Axum, Reqwest/rustls, Tower, Governor, Serde, Figment, secrecy, Prometheus/metrics, tracing, UUID/chrono, circuit-breaker/cache helpers, and validation/security crates. No Cargo build/test was run because it would create build artifacts outside the requested documentation scope.

## Configuration and deployment artifacts

- Python container: `Dockerfile.python` exposes 8080 and defaults to the legacy server.
- Rust container: `Dockerfile.gateway` exposes 8080 and copies `llm-gateway/config.toml`.
- Main Compose publishes gateway, component, JEV, observability, nginx, and Cowrie ports across a normal external bridge plus an internal bridge (`docker-compose.yml`).
- `docker-compose.prod.yml` adds resource limits, read-only/rootless-related hardening, tmpfs, and logging limits, but does not turn the main service set into a private CORE.
- `docker-compose.field.yml` has an internal Docker network and relies on `scripts/field_provision.sh` for host firewall/egress controls. This is a runbook plus Compose design; no executed host state was available to prove it.
- No Terraform, CloudFormation, CDK, AWS security-group, VPC, subnet, private-link, or instance-discovery configuration was found for `RAGIN-EDGE`/`RAGIN-CORE`.

## Generated versus source-controlled artifacts

The repository mixes source and generated material. Examples include tracked manuscript PDFs/auxiliary files, result JSON/JSONL, algorithm artifacts, session records, model files, logs, and graph/benchmark outputs. Many current results/session artifacts are untracked. The runtime does not enforce one immutable evidence manifest for all serving or benchmark inputs. Existing manifests/ledgers under `docs/` provide useful human process controls but do not prove that every result was regenerated from a clean checkout.

## Tests and benchmark runners

- Framework: pytest, configured in `pyproject.toml` with `tests/`, auto asyncio, unit/integration/security/slow markers, and a 75% coverage threshold.
- Benchmark runners are primarily scripts in `scripts/`, including ablations, verifier red-team suites, cross-session consistency, live benchmark replay, JEV experiments, CTI scorer audits, stability/determinism checks, and rescue benchmarks.
- Rust tests/builds were not run.
- Docker Compose, AWS, provider, and external-target checks were not run.

Actual read-only validation performed during this audit:

| Check | Result |
|---|---|
| `pytest --collect-only -q -p no:cacheprovider` | 1,743 tests collected; collection emitted unknown `e2e` mark warnings |
| Focused verifier/server/JEV/artifact suite | 250 passed in 17.49 seconds |
| `git diff --check` | Exit 0 before and after the audit checks |
| Full pytest suite | Not run; collection count and existing worktree drift require a controlled rerun |

The repository README still states a 1,715-test historical count (`README.md:13,127`), so documentation and current collection are inconsistent.

## Documentation inventory

Relevant existing documentation includes `README.md`, `PROJECT_STATUS.md`, `docs/RAGIN_RESULTS_LEDGER_2026-10-08.md`, `docs/RAGIN_RELEASE_MANIFEST_2026-10-08.md`, `docs/RAGIN_THREAT_MODEL_2026-10-08.md`, `docs/SP2027_AUDIT_2026-10-03.md`, `docs/FIELD_ETHICS.md`, and multiple manuscript/research plans. These are treated as claims or process records and were checked against code; comments and plans are not treated as proof of deployed controls.

## Bottom line

RAGIN has the components needed for a research prototype, but not one authoritative, deployment-ready serving path. The most consequential baseline facts are: active `server_v2` does not receive a verifier; the legacy server serves directly from the deceiver; default authentication can be disabled by empty/placeholder configuration; the Rust gateway has no visible request-authentication layer; the main Compose file publishes backend/control-plane ports; and the AWS two-node boundary is absent. These facts drive the P0/P1 findings in the companion documents.

"""Enforceable B0-B3 run contract and offline preflight.

The historical ``configs/ablation/*.json`` files are design/startup metadata.
This module does not rewrite them and does not pretend their proposed generation
settings are applied. It distinguishes two questions:

* **Design validation** -- is the contract internally coherent (arms, retrieval
  modes, shared bundle, allocation arithmetic, split disjointness, hashes)?
* **Execution readiness** -- can a real run start *now*, with resolved model,
  checkpoint, prompt, persona, data, allocation, verification profile,
  enforceable resources and no mock substitution?

A design can validate while execution is ``NOT_READY``. Only explicit,
resolved evidence produces ``EXECUTION_READY``. Missing or unknown facts never
become ready by default and are never replaced by a mock.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DESIGN_VALID = "DESIGN_VALID"
DESIGN_INVALID = "DESIGN_INVALID"
EXECUTION_READY = "EXECUTION_READY"
EXECUTION_NOT_READY = "NOT_READY"

UNRESOLVED_MARKERS = ("UNRESOLVED", "UNKNOWN", "PLACEHOLDER", "TBD", "NONE_SELECTED")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
FORBIDDEN_ENV_PREFIXES = (
    "OPENROUTER",
    "OPENAI",
    "ANTHROPIC",
    "AZURE_",
    "AWS_",
    "GOOGLE_",
    "HF_TOKEN",
    "HUGGINGFACE_",
    "COHERE",
    "MISTRAL",
    "DEEPSEEK",
)
SECRET_ENV_RE = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|PROVIDER|API)", re.IGNORECASE)
ARM_ORDER = ("B0", "B1", "B2", "B3")
RETRIEVAL_MODES = {"B1": "none", "B2": "bm25", "B3": "dense"}
SHARED_KEYS = (
    ("generator", "model"),
    ("generator", "decoding"),
    ("resources", "budget_id"),
    ("resources", "cpu"),
    ("resources", "memory_mb"),
    ("resources", "gpu"),
    ("verification", "kind"),
)
ENFORCED_RESOURCE_MODES = {"CGROUP_V2", "CONTAINER_LIMITS", "SYSTEMD_SCOPE", "PROCESS_RLIMIT"}


class ContractRefusal(RuntimeError):  # noqa: N818 - public API name is already frozen
    """Raised when a caller tries to execute an unresolved or invalid contract."""

    def __init__(self, report: ReadinessReport) -> None:
        self.report = report
        codes = ", ".join(sorted({blocker.code for blocker in report.blockers})) or "UNKNOWN"
        super().__init__(f"run contract is not executable ({report.execution_status}): {codes}")


@dataclass(frozen=True)
class Blocker:
    code: str
    scope: str
    detail: str
    integration_request: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "scope": self.scope,
            "detail": self.detail,
        }
        if self.integration_request:
            payload["integration_request"] = self.integration_request
        return payload


@dataclass
class DesignReport:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "errors": list(self.errors), "warnings": list(self.warnings)}


@dataclass
class ReadinessReport:
    contract_id: str
    design: DesignReport
    execution_status: str
    blockers: list[Blocker] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    resolved: dict[str, Any] = field(default_factory=dict)
    claim_boundary: dict[str, Any] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.execution_status == EXECUTION_READY and not self.blockers

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ragin.ablation.preflight.v1",
            "contract_id": self.contract_id,
            "execution_status": self.execution_status,
            "ready": self.ready,
            "design": self.design.to_dict(),
            "blockers": [blocker.to_dict() for blocker in self.blockers],
            "blocker_codes": sorted({blocker.code for blocker in self.blockers}),
            "warnings": list(self.warnings),
            "resolved": self.resolved,
            "claim_boundary": self.claim_boundary,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_corpus_dir_sha256(path: Path) -> str:
    """Canonical *content* hash of a corpus directory.

    Hashes sorted relative paths and each file's bytes. This is deliberately not
    an index-byte hash: BM25 and FAISS indexes can differ while the underlying
    corpus is identical, and equal index bytes are not proof of equal content.
    """
    entries = []
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        entries.append(
            {
                "path": item.relative_to(path).as_posix(),
                "sha256": sha256_file(item),
                "size": item.stat().st_size,
            }
        )
    return canonical_sha256(entries)


def canonical_document_ids_sha256(value: Any) -> str:
    """Canonical document-ID hash for a list/dict of documents.

    Accepts common ``documents.json`` shapes (list of objects, or an object with
    ``documents``); extracts ``id``/``doc_id``/``document_id`` fields. Unknown
    shapes are hashed canonically rather than guessed into a false match.
    """
    documents = value.get("documents") if isinstance(value, dict) else value
    ids: list[str] = []
    if isinstance(documents, list):
        for document in documents:
            if isinstance(document, dict):
                for key in ("id", "doc_id", "document_id"):
                    if document.get(key) is not None:
                        ids.append(str(document[key]))
                        break
    if ids:
        return canonical_sha256(sorted(ids))
    return canonical_sha256(value)


def _is_unresolved(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        upper = value.strip().upper()
        return not upper or any(marker in upper for marker in UNRESOLVED_MARKERS)
    return False


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_contract(path: Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Load a run contract and resolve referenced arm files with hash checks.

    A referenced arm hash mismatch raises ``ValueError`` immediately: silently
    running a different file than the contract names would invalidate the run.
    """
    root = repo_root or Path(__file__).resolve().parents[2]
    contract_path = path if path.is_absolute() else root / path
    contract = load_json(contract_path)
    contract["_contract_path"] = str(contract_path)
    contract["_contract_sha256"] = sha256_file(contract_path)
    arms = contract.get("arms") or {}
    resolved_arms: dict[str, Any] = {}
    for arm_id, spec in arms.items():
        if not isinstance(spec, dict) or not spec.get("file"):
            resolved_arms[arm_id] = {"spec": spec, "content": None, "path": None, "sha256": None}
            continue
        arm_path = root / str(spec["file"])
        if not arm_path.exists():
            resolved_arms[arm_id] = {
                "spec": spec,
                "content": None,
                "path": str(spec["file"]),
                "sha256": None,
                "missing": True,
            }
            continue
        actual = sha256_file(arm_path)
        expected = spec.get("sha256")
        if expected and expected != actual:
            raise ValueError(f"arm {arm_id} hash mismatch: contract={expected} actual={actual}")
        resolved_arms[arm_id] = {
            "spec": spec,
            "content": load_json(arm_path),
            "path": str(spec["file"]),
            "sha256": actual,
        }
    contract["_resolved_arms"] = resolved_arms
    return contract


def _arm_content(contract: dict[str, Any], arm_id: str) -> dict[str, Any]:
    entry = (contract.get("_resolved_arms") or {}).get(arm_id) or {}
    content = entry.get("content")
    return content if isinstance(content, dict) else {}


def _nested(mapping: dict[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def validate_design(contract: dict[str, Any]) -> DesignReport:
    """Validate contract coherence independently of resolved execution facts."""
    errors: list[str] = []
    warnings: list[str] = []

    if contract.get("schema") != "ragin.ablation.run_contract.v1":
        errors.append(f"unsupported contract schema: {contract.get('schema')!r}")
    if contract.get("version") != "v1":
        warnings.append(f"contract version is {contract.get('version')!r}, expected 'v1'")

    resolved_arms = contract.get("_resolved_arms") or {}
    for arm_id in ARM_ORDER:
        if arm_id not in resolved_arms:
            errors.append(f"missing arm {arm_id}")
            continue
        entry = resolved_arms[arm_id]
        if entry.get("missing"):
            errors.append(f"arm {arm_id} file is missing: {entry.get('path')}")
        elif entry.get("content") is None:
            errors.append(f"arm {arm_id} has no resolvable config content")

    # Retrieval modes must match the frozen semantics exactly.
    for arm_id, expected_mode in RETRIEVAL_MODES.items():
        mode = _nested(_arm_content(contract, arm_id), "retrieval", "mode")
        if mode != expected_mode:
            errors.append(f"arm {arm_id} retrieval.mode={mode!r}; protocol requires {expected_mode!r}")
    b0_content = _arm_content(contract, "B0")
    b0_retrieval = b0_content.get("retrieval") or {}
    # B0 may carry an explanatory ``mode=not_applicable`` marker, but it must
    # not declare a real RAGIN retrieval mode or retrieval environment.
    if b0_retrieval and (
        b0_retrieval.get("mode") not in {None, "not_applicable"}
        or b0_retrieval.get("env")
        or b0_retrieval.get("top_k") is not None
        or b0_retrieval.get("context_budget_tokens") is not None
    ):
        errors.append("B0 native Cowrie must not declare a RAGIN retrieval mode")
    b1_content = _arm_content(contract, "B1")
    if _nested(b1_content, "retrieval", "env", "RAGIN_VECTOR_STORE_PATH") is not None:
        errors.append("B1 (retrieval off) must not carry a vector-store path")
    b3_store = _nested(_arm_content(contract, "B3"), "retrieval", "env", "RAGIN_VECTOR_STORE_PATH")
    b3_embed = _nested(_arm_content(contract, "B3"), "retrieval", "env", "RAGIN_EMBED_MODEL")
    if b3_store is None or b3_embed is None:
        errors.append("B3 must declare RAGIN_VECTOR_STORE_PATH and RAGIN_EMBED_MODEL")

    # Shared bundle: B1-B3 must be identical on model, decoding, budget,
    # verification and persona. A drift here changes the causal contrast.
    for path in SHARED_KEYS:
        values = {arm_id: _nested(_arm_content(contract, arm_id), *path) for arm_id in ("B1", "B2", "B3")}
        if len({json.dumps(value, sort_keys=True, default=str) for value in values.values()}) != 1:
            errors.append(f"B1-B3 shared field {'/'.join(path)} differs: {values}")
    personas = {
        _nested(_arm_content(contract, arm_id), "persona", "host_fiction_path")
        for arm_id in ("B1", "B2", "B3")
    }
    if len(personas) != 1:
        errors.append(f"B1-B3 persona paths differ: {sorted(str(p) for p in personas)}")

    # Allocation arithmetic is fixed by protocol v2.
    allocation = contract.get("allocation") or {}
    expected_alloc = contract.get("allocation", {}).get("expected_sessions", 32)
    product = 1
    for key in ("scenarios", "attacker_profiles", "seeds", "arms"):
        value = allocation.get(key)
        if not isinstance(value, int) or value < 1:
            errors.append(f"allocation.{key} must be a positive integer, got {value!r}")
        else:
            product *= value
    if product != expected_alloc:
        errors.append(f"allocation product {product} != expected_sessions {expected_alloc}")
    if allocation.get("turn_cap") != 12:
        errors.append(f"turn cap must be 12, got {allocation.get('turn_cap')!r}")
    if allocation.get("arms") != 4:
        errors.append(f"pilot arm count must be 4, got {allocation.get('arms')!r}")
    if not _is_sha256(allocation.get("sequence_sha256")) and not _is_unresolved(allocation.get("sequence_sha256")):
        errors.append("allocation.sequence_sha256 is neither a SHA-256 nor an explicit unresolved marker")

    # Split disjointness and development-only infrastructure.
    splits = contract.get("data_splits") or {}
    seen: dict[str, str] = {}
    for split_name in ("development", "calibration", "holdout"):
        families = splits.get(split_name) or []
        if not isinstance(families, list):
            errors.append(f"data_splits.{split_name} must be a list")
            continue
        for family in families:
            if family in seen:
                errors.append(f"family {family!r} appears in both {seen[family]} and {split_name}")
            seen[family] = split_name
    if splits and not splits.get("development"):
        errors.append("at least one development family is required for infrastructure smoke")

    # B0 native transport rules.
    b0 = contract.get("b0_native") or {}
    image_id = b0.get("image_id")
    if not isinstance(image_id, str) or not IMAGE_ID_RE.fullmatch(image_id):
        errors.append("B0 image_id must be a full cached sha256:<64 hex> ID")
    if b0.get("pull") != "never":
        errors.append("B0 image pull policy must be 'never'")
    bind = b0.get("listen") or {}
    if bind.get("host") not in LOOPBACK_HOSTS:
        errors.append(f"B0 listen host must be loopback, got {bind.get('host')!r}")
    if bind.get("public") is not False:
        errors.append("B0 must explicitly declare public=false")
    baseline = b0.get("baseline_identity") or {}
    if not isinstance(baseline, dict):
        errors.append("B0 baseline_identity must be an object")
    else:
        for key in ("status", "matched_to_b1_b3", "observed", "b1_b3_reference"):
            if key not in baseline:
                errors.append(f"B0 baseline_identity missing {key}")
        if not isinstance(baseline.get("observed"), dict):
            errors.append("B0 baseline_identity.observed must be an object of observed native fields")

    # B2/B3 must name the same canonical corpus content/document IDs and the
    # same top_k/context budget. An index-byte hash is not a corpus identity.
    retrieval_freeze = contract.get("retrieval_freeze") or {}
    shared_corpus = retrieval_freeze.get("shared_corpus") or {}
    if not isinstance(shared_corpus, dict):
        errors.append("retrieval_freeze.shared_corpus must be an object")
    else:
        for key in ("content_sha256", "document_ids_sha256", "top_k", "context_budget_tokens", "canonicalization"):
            if key not in shared_corpus:
                errors.append(f"retrieval_freeze.shared_corpus missing {key}")
        if not shared_corpus.get("canonicalization"):
            errors.append("shared corpus canonicalization must be described")
    declared_corpus = {}
    for arm_id in ("B2", "B3"):
        retrieval = _nested(_arm_content(contract, arm_id), "retrieval") or {}
        for key in ("corpus_content_sha256", "document_ids_sha256", "top_k", "context_budget_tokens"):
            if key in retrieval:
                declared_corpus[(arm_id, key)] = retrieval.get(key)
    for key in ("corpus_content_sha256", "document_ids_sha256", "top_k", "context_budget_tokens"):
        values = {arm: declared_corpus.get((arm, key)) for arm in ("B2", "B3") if (arm, key) in declared_corpus}
        if len(set(json.dumps(value, sort_keys=True, default=str) for value in values.values())) > 1:
            errors.append(f"B2/B3 {key} differs; contrasts across different corpora/budgets are forbidden: {values}")
        shared_value = shared_corpus.get(key)
        for arm, value in values.items():
            if (
                value is not None
                and shared_value is not None
                and json.dumps(value, sort_keys=True, default=str)
                != json.dumps(shared_value, sort_keys=True, default=str)
            ):
                errors.append(f"{arm} {key}={value!r} differs from shared corpus declaration {shared_value!r}")

    # Verification profile must be named and its hook declared. Readiness
    # decides whether the integration is actually available.
    profile = _nested(contract, "verification", "profile")
    if not profile:
        errors.append("verification.profile is required")
    elif not _nested(contract, "verification", "hook_env"):
        errors.append("verification.hook_env is required so the core profile can be selected explicitly")

    # Primary analysis must be declared in the same contract.
    analysis = contract.get("analysis") or {}
    if analysis.get("primary_cause") != "DETECTION":
        errors.append("analysis.primary_cause must be DETECTION")
    if analysis.get("horizon_turns") != 12:
        errors.append("analysis.horizon_turns must be 12")
    expected_contrasts = {"B2_vs_B1", "B3_vs_B1", "B3_vs_B2"}
    declared = set(analysis.get("retrieval_contrasts") or [])
    if declared != expected_contrasts:
        errors.append(f"analysis.retrieval_contrasts must be {sorted(expected_contrasts)}, got {sorted(declared)}")

    status = DESIGN_INVALID if errors else DESIGN_VALID
    return DesignReport(status=status, errors=errors, warnings=warnings)


def _add(blockers: list[Blocker], code: str, scope: str, detail: str, request: str | None = None) -> None:
    blockers.append(Blocker(code=code, scope=scope, detail=detail, integration_request=request))


def _check_hashes(contract: dict[str, Any], root: Path, blockers: list[Blocker], resolved: dict[str, Any]) -> None:
    checks = [
        ("prompt", _nested(contract, "bundle", "prompt", "sha256"), _nested(contract, "bundle", "prompt", "id")),
        ("persona", _nested(contract, "bundle", "persona", "sha256"), _nested(contract, "bundle", "persona", "path")),
        ("data", _nested(contract, "bundle", "data", "sha256"), _nested(contract, "bundle", "data", "path")),
        (
            "allocation",
            _nested(contract, "allocation", "sequence_file_sha256"),
            _nested(contract, "allocation", "sequence_path"),
        ),
        (
            "track_a",
            _nested(contract, "bundle", "track_a", "sha256"),
            _nested(contract, "bundle", "track_a", "path"),
        ),
    ]
    for label, digest, source in checks:
        if _is_unresolved(digest):
            _add(
                blockers,
                f"UNRESOLVED_{label.upper()}",
                label,
                f"{label} hash is unresolved ({digest!r})",
                f"freeze {label} ({source!r}) and record its SHA-256 in the run contract",
            )
            continue
        if not _is_sha256(digest):
            _add(blockers, f"INVALID_{label.upper()}_HASH", label, f"{label} hash is not a SHA-256: {digest!r}")
            continue
        if isinstance(source, str) and not _is_unresolved(source):
            path = root / source
            if not path.exists():
                _add(blockers, f"MISSING_{label.upper()}_ARTIFACT", label, f"{label} artifact not found: {source}")
            elif sha256_file(path) != digest:
                _add(
                    blockers,
                    f"{label.upper()}_HASH_MISMATCH",
                    label,
                    f"{label} artifact hash differs from contract for {source}",
                )
            else:
                resolved[label] = {"path": source, "sha256": digest}
        else:
            resolved[label] = {"path": None, "sha256": digest}


def _check_generation(contract: dict[str, Any], root: Path, blockers: list[Blocker], resolved: dict[str, Any]) -> None:
    generation = contract.get("generation") or {}
    decoding = generation.get("decoding") or {}
    adapter = generation.get("adapter") or {}
    supported = set(adapter.get("supported_decoding") or [])
    requested = {key for key in decoding if key in {"temperature", "top_p", "max_tokens", "seed"}}
    unsupported = sorted(requested - supported)

    # The applied-decoding owner publishes effective config/exposure metadata.
    # Consume it when present; otherwise block rather than claiming compliance.
    effective = generation.get("effective_config") or {}
    effective_ready = False
    if effective:
        path = effective.get("path")
        digest = effective.get("sha256")
        target = root / str(path) if path else None
        if target is not None and target.exists() and _is_sha256(digest) and sha256_file(target) == digest:
            payload = load_json(target)
            applied = payload.get("applied_decoding") or payload.get("effective_decoding") or {}
            mismatch = {
                key: {"requested": decoding.get(key), "applied": applied.get(key)}
                for key in requested
                if key in applied and applied.get(key) != decoding.get(key)
            }
            exposure = payload.get("model_exposure") or {}
            if mismatch:
                _add(
                    blockers,
                    "BLOCKED_GENERATION_CONFIG",
                    "generation",
                    f"applied decoding differs from the contract: {mismatch}",
                    "reconcile the applied decoding with the frozen contract or revise the contract",
                )
            elif exposure.get("require_model_exposure") is not True:
                _add(
                    blockers,
                    "MODEL_EXPOSURE_NOT_ENFORCED",
                    "generation",
                    "effective config does not require observed model exposure",
                    "consume the require-model-exposure contract from the deception/provider owner",
                )
            else:
                effective_ready = True
                resolved["generation_config"] = {
                    "path": str(path),
                    "sha256": digest,
                    "applied_decoding": applied,
                    "require_model_exposure": True,
                }
        else:
            _add(
                blockers,
                "UNRESOLVED_EFFECTIVE_GENERATION_CONFIG",
                "generation",
                "effective generation config artifact is missing or its hash does not match",
            )

    if _is_unresolved(generation.get("model_id")) or _is_unresolved(generation.get("adapter", {}).get("name")):
        _add(
            blockers,
            "UNRESOLVED_MODEL",
            "generation",
            "generator identity/adapter is unresolved",
            "record the exact frozen generator identity, revision, adapter class and price",
        )
    if not effective_ready and (
        adapter.get("config_enforced") is not True or unsupported or adapter.get("hardcoded_decoding")
    ):
        _add(
            blockers,
            "BLOCKED_GENERATION_CONFIG",
            "generation",
            (
                "requested decoding is not enforced by the adapter and no effective-config artifact resolved it "
                f"(config_enforced={adapter.get('config_enforced')!r}, unsupported={unsupported}, "
                f"hardcoded={adapter.get('hardcoded_decoding')!r})"
            ),
            (
                "consume the pure effective config/model-exposure metadata from the Hisoka/provider owner "
                "once its env names are published; do not claim the proposed values are applied before then"
            ),
        )
    exposure_contract = generation.get("exposure_contract") or {}
    if exposure_contract.get("require_model_exposure") is not True:
        _add(
            blockers,
            "MODEL_EXPOSURE_NOT_ENFORCED",
            "generation",
            f"model-exposure contract status={exposure_contract.get('status')!r}",
            "consume the require-model-exposure metadata from the applied-decoding owner; "
            "B1-B3 must fail closed without observed model identity/hash",
        )
    if generation.get("fallback", "none") == "none" and adapter.get("template_fallback_available") is not False:
        _add(
            blockers,
            "FALLBACK_NOT_DISABLED",
            "generation",
            "contract requires fallback=none but the runtime still exposes a template/static fallback",
            "expose a fail-closed no-fallback switch through the existing generator seam, or revise the contract",
        )
    if _is_unresolved(generation.get("prompt_id")):
        _add(blockers, "UNRESOLVED_PROMPT_ID", "generation", "prompt id is unresolved")
    invocation = generation.get("invocation") or {}
    kind = invocation.get("kind")
    if kind == "UNRESOLVED" or not kind:
        _add(
            blockers,
            "MODEL_INVOCATION_UNAVAILABLE",
            "generation",
            f"model invocation kind is {kind!r}",
            "provide a resolved local invocation and attest availability; no mock is substituted",
        )
    elif kind == "EXTERNAL_PROVIDER":
        _add(
            blockers,
            "EXTERNAL_INVOCATION_NOT_AUTHORIZED",
            "generation",
            "external provider invocation is not authorized in this phase",
        )
    elif kind == "LOCAL_FILE_MODEL":
        path = invocation.get("path")
        digest = invocation.get("sha256")
        if _is_unresolved(path) or not isinstance(path, str):
            _add(blockers, "MODEL_INVOCATION_UNAVAILABLE", "generation", "local model path unresolved")
        else:
            model_path = Path(path)
            if not model_path.exists():
                _add(
                    blockers,
                    "MODEL_INVOCATION_UNAVAILABLE",
                    "generation",
                    f"local model path does not exist: {path}",
                )
            elif _is_unresolved(digest) or not _is_sha256(digest):
                _add(blockers, "UNRESOLVED_CHECKPOINT", "generation", "local model/checkpoint hash unresolved")
            elif model_path.is_file() and sha256_file(model_path) != digest:
                _add(blockers, "CHECKPOINT_HASH_MISMATCH", "generation", "local checkpoint hash mismatch")
            else:
                resolved["model"] = {"kind": kind, "path": path, "sha256": digest}
    elif kind == "LOCAL_HTTP_LOOPBACK":
        endpoint = invocation.get("endpoint") or {}
        host = endpoint.get("host")
        if host not in LOOPBACK_HOSTS:
            _add(
                blockers,
                "NON_LOOPBACK_INVOCATION_FORBIDDEN",
                "generation",
                f"local HTTP invocation host must be loopback, got {host!r}",
            )
        if invocation.get("attested_available") is not True:
            _add(
                blockers,
                "MODEL_INVOCATION_UNAVAILABLE",
                "generation",
                "loopback model serving is not attested as available",
                "attest availability from the serving process owner; offline preflight does not probe it",
            )
        elif invocation.get("offline_attested") is not True or _is_unresolved(invocation.get("weights_identity")):
            _add(
                blockers,
                "MODEL_INVOCATION_UNAVAILABLE",
                "generation",
                "a loopback endpoint is not proof of offline/local-weight inference "
                f"(offline_attested={invocation.get('offline_attested')!r}, "
                f"weights_identity={invocation.get('weights_identity')!r})",
                "record local-weight identity/provenance and offline attestation, or obtain explicit external "
                "data-sharing authorization; cloud aliases on localhost are not local generative evidence",
            )
        elif not _is_unresolved(invocation.get("model_sha256")):
            resolved["model"] = {
                "kind": kind,
                "host": host,
                "sha256": invocation.get("model_sha256"),
                "weights_identity": invocation.get("weights_identity"),
            }
        else:
            _add(blockers, "UNRESOLVED_CHECKPOINT", "generation", "loopback model/checkpoint hash unresolved")
    else:
        _add(blockers, "MODEL_INVOCATION_UNAVAILABLE", "generation", f"unknown invocation kind {kind!r}")


def _deadline_seconds(value: Any, *, allow_string: bool = False) -> float | None:
    """Validate the core profile's 0 < seconds <= 60 contract.

    ``bool`` is rejected explicitly because ``float(True) == 1.0`` would
    otherwise silently accept a boolean as a duration. NaN and infinity are
    rejected before the core resolver is called.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        if not allow_string:
            return None
        try:
            value = float(value)
        except ValueError:
            return None
    if not isinstance(value, (int, float)):
        return None
    seconds = float(value)
    if not math.isfinite(seconds) or not (0.0 < seconds <= 60.0):
        return None
    return seconds


def _check_verification(contract: dict[str, Any], blockers: list[Blocker], resolved: dict[str, Any]) -> None:
    verification = contract.get("verification") or {}
    profile = verification.get("profile")
    status = verification.get("integration_status")
    source = verification.get("source_sha256")
    deadline = verification.get("deadline") or {}
    if not profile:
        _add(blockers, "UNRESOLVED_VERIFICATION", "verification", "verification profile is unnamed")
        return
    if status != "AVAILABLE":
        _add(
            blockers,
            "VERIFICATION_PROFILE_INTEGRATION_REQUIRED",
            "verification",
            f"profile {profile!r} integration_status={status!r}",
            verification.get("integration_request")
            or (
                "peer core-verification stream must land research_strict_v1 plus wall-clock deadline and expose "
                f"it through {verification.get('hook_env')}; this stream consumes, but does not implement, that seam"
            ),
        )
    if _is_unresolved(source) or not _is_sha256(source):
        _add(
            blockers,
            "UNRESOLVED_VERIFICATION_HASH",
            "verification",
            f"verification source hash is {source!r}",
            "freeze the verifier source hash after the core profile lands",
        )

    resolved_policy = None
    deadline_seconds = _deadline_seconds(deadline.get("seconds"))
    if deadline.get("enforcement") != "WALL_CLOCK" or deadline_seconds is None:
        _add(
            blockers,
            "VERIFIER_DEADLINE_NOT_ENFORCED",
            "verification",
            f"deadline metadata is not a finite wall-clock value: {deadline!r}",
            "consume the bounded wall-clock deadline field from the core profile; "
            "a simulated exception is not enforcement",
        )
    else:
        try:
            from ragin.cycle.verification_deadline import resolve_verification_policy

            resolved_policy = resolve_verification_policy(profile=profile, deadline_s=deadline_seconds)
        except (ImportError, ValueError) as exc:
            _add(
                blockers,
                "VERIFIER_DEADLINE_NOT_ENFORCED",
                "verification",
                f"core verification policy resolver rejected the contract: {exc}",
                "consume the core pure resolver; do not duplicate its deadline validation",
            )

    hook_fields = verification.get("hook_env_fields") or {}
    hook_profile = hook_fields.get("RAGIN_VERIFIER_PROFILE")
    hook_seconds = _deadline_seconds(hook_fields.get("RAGIN_VERIFIER_DEADLINE_S"), allow_string=True)
    hook_ok = False
    if status == "AVAILABLE":
        if hook_profile != profile or hook_seconds is None:
            _add(
                blockers,
                "VERIFICATION_HOOK_MISMATCH",
                "verification",
                f"hook fields do not select the named profile/deadline: {hook_fields!r}",
                "use the peer-confirmed RAGIN_VERIFIER_PROFILE and RAGIN_VERIFIER_DEADLINE_S hooks",
            )
        elif resolved_policy is not None:
            try:
                from ragin.cycle.verification_deadline import resolve_verification_policy

                hook_policy = resolve_verification_policy(profile=hook_profile, deadline_s=hook_seconds)
            except (ImportError, ValueError) as exc:
                _add(
                    blockers,
                    "VERIFICATION_HOOK_MISMATCH",
                    "verification",
                    f"hook policy is invalid: {exc}",
                    "make the hook select the same core-resolved profile and deadline",
                )
            else:
                if (
                    hook_policy.profile != resolved_policy.profile
                    or not math.isclose(hook_policy.deadline_s, resolved_policy.deadline_s, rel_tol=0.0, abs_tol=1e-9)
                ):
                    _add(
                        blockers,
                        "VERIFICATION_HOOK_MISMATCH",
                        "verification",
                        f"hook policy {hook_policy.to_dict()} differs from contract policy "
                        f"{resolved_policy.to_dict()}",
                        "make the hook select the same core-resolved profile and deadline",
                    )
                else:
                    hook_ok = True
    if (
        status == "AVAILABLE"
        and _is_sha256(source)
        and resolved_policy is not None
        and hook_ok
    ):
        resolved["verification"] = {
            "profile": resolved_policy.profile,
            "source_sha256": source,
            "deadline": resolved_policy.to_dict(),
            "hook_env_fields": hook_fields,
        }


def _check_resources(contract: dict[str, Any], blockers: list[Blocker], resolved: dict[str, Any]) -> None:
    resources = contract.get("resources") or {}
    enforcement = resources.get("enforcement")
    if enforcement not in ENFORCED_RESOURCE_MODES:
        _add(
            blockers,
            "RESOURCE_LIMITS_NOT_ENFORCED",
            "resources",
            f"resource metadata enforcement={enforcement!r}; JSON fields are not process/container limits",
            "run each arm under an actual cgroup/container/systemd/rlimit mechanism and record its identifier",
        )
        return
    spec = resources.get("enforcement_spec") or {}
    if not spec.get("mechanism") or not spec.get("identifier"):
        _add(
            blockers,
            "RESOURCE_LIMITS_NOT_ENFORCED",
            "resources",
            "enforcement mode is claimed without a mechanism/identifier",
        )
        return
    resolved["resources"] = {"enforcement": enforcement, "spec": spec}


def _check_retrieval(contract: dict[str, Any], root: Path, blockers: list[Blocker], resolved: dict[str, Any]) -> None:
    shared = _nested(contract, "retrieval_freeze", "shared_corpus") or {}
    content_hash = shared.get("content_sha256")
    ids_hash = shared.get("document_ids_sha256")
    top_k = shared.get("top_k")
    context_budget = shared.get("context_budget_tokens")
    if _is_unresolved(content_hash) or not _is_sha256(content_hash):
        _add(
            blockers,
            "UNRESOLVED_SHARED_CORPUS_CONTENT",
            "retrieval",
            f"B2/B3 shared canonical corpus-content hash is {content_hash!r}",
            "freeze one canonical corpus-content hash over sorted document IDs + normalized content; BM25 and FAISS "
            "index-byte hashes are not acceptable substitutes",
        )
    if _is_unresolved(ids_hash) or not _is_sha256(ids_hash):
        _add(
            blockers,
            "UNRESOLVED_SHARED_DOCUMENT_IDS",
            "retrieval",
            f"B2/B3 shared document-ID hash is {ids_hash!r}",
            "freeze the shared document-ID set/hash used by both BM25 and dense retrieval",
        )
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        _add(blockers, "UNRESOLVED_RETRIEVAL_TOP_K", "retrieval", f"shared top_k is {top_k!r}")
    if not isinstance(context_budget, int) or isinstance(context_budget, bool) or context_budget < 1:
        _add(
            blockers,
            "UNRESOLVED_RETRIEVAL_CONTEXT_BUDGET",
            "retrieval",
            f"shared context token budget is {context_budget!r}",
        )
    if isinstance(top_k, int) and isinstance(context_budget, int) and context_budget > 0:
        resolved["shared_retrieval_budget"] = {"top_k": top_k, "context_budget_tokens": context_budget}

    b3 = _arm_content(contract, "B3")
    env = _nested(b3, "retrieval", "env") or {}
    store = env.get("RAGIN_VECTOR_STORE_PATH")
    embed = env.get("RAGIN_EMBED_MODEL")
    store_hash = _nested(contract, "retrieval_freeze", "store_sha256")
    embed_hash = _nested(contract, "retrieval_freeze", "embed_model_sha256")
    if _is_unresolved(store):
        _add(blockers, "UNRESOLVED_B3_STORE", "retrieval", f"B3 store path is {store!r}")
    else:
        store_path = Path(str(store))
        if not store_path.is_dir() or not (store_path / "index.faiss").exists() or not (
            store_path / "documents.json"
        ).exists():
            _add(
                blockers,
                "B3_STORE_INCOMPLETE",
                "retrieval",
                f"B3 store must contain index.faiss and documents.json: {store}",
            )
        elif _is_unresolved(store_hash) or not _is_sha256(store_hash):
            _add(blockers, "UNRESOLVED_B3_STORE_HASH", "retrieval", "B3 exact-store hash is unresolved")
        else:
            observed = canonical_sha256(
                {
                    "index.faiss": sha256_file(store_path / "index.faiss"),
                    "documents.json": sha256_file(store_path / "documents.json"),
                }
            )
            if observed != store_hash:
                _add(blockers, "B3_STORE_HASH_MISMATCH", "retrieval", "B3 exact-store hash mismatch")
            else:
                resolved["b3_store"] = {"path": str(store), "sha256": store_hash}
    if _is_unresolved(embed):
        _add(blockers, "UNRESOLVED_EMBED_MODEL", "retrieval", f"B3 embedding model is {embed!r}")
    elif not Path(str(embed)).is_dir():
        _add(blockers, "EMBED_MODEL_MISSING", "retrieval", f"embedding model directory missing: {embed}")
    elif _is_unresolved(embed_hash) or not _is_sha256(embed_hash):
        _add(blockers, "UNRESOLVED_EMBED_MODEL_HASH", "retrieval", "embedding model hash unresolved")
    else:
        resolved["embed_model"] = {"path": str(embed), "sha256": embed_hash}
    b2 = _arm_content(contract, "B2")
    corpus = _nested(b2, "retrieval", "corpus_path")
    if _is_unresolved(corpus):
        _add(blockers, "UNRESOLVED_B2_CORPUS", "retrieval", f"B2 BM25 corpus is {corpus!r}")
    else:
        corpus_path = Path(str(corpus))
        if not corpus_path.exists():
            corpus_path = root / str(corpus)
        if not corpus_path.exists():
            _add(blockers, "B2_CORPUS_MISSING", "retrieval", f"B2 BM25 corpus not found: {corpus}")
        elif corpus_path.is_dir() and _is_sha256(content_hash):
            observed = canonical_corpus_dir_sha256(corpus_path)
            if observed != content_hash:
                _add(
                    blockers,
                    "B2_CORPUS_CONTENT_MISMATCH",
                    "retrieval",
                    "B2 corpus content does not match the shared canonical corpus-content hash",
                )
            else:
                resolved["b2_corpus"] = {"path": str(corpus), "content_sha256": observed}
        else:
            resolved["b2_corpus"] = {"path": str(corpus)}

    # When the exact dense store exists, its document-ID set must match the
    # shared set; index bytes alone are not sufficient.
    if _is_sha256(ids_hash) and not _is_unresolved(store):
        store_path = Path(str(store))
        documents_path = store_path / "documents.json"
        if documents_path.exists():
            import json as _json

            payload = _json.loads(documents_path.read_text(encoding="utf-8"))
            observed_ids = canonical_document_ids_sha256(payload)
            if observed_ids != ids_hash:
                _add(
                    blockers,
                    "B3_STORE_DOCUMENT_IDS_MISMATCH",
                    "retrieval",
                    "B3 documents.json document-ID set/hash does not match the shared B2/B3 document-ID hash",
                )
            else:
                resolved["b3_document_ids"] = {"sha256": observed_ids}


def _check_b0(contract: dict[str, Any], blockers: list[Blocker], resolved: dict[str, Any], env_check: bool) -> None:
    b0 = contract.get("b0_native") or {}
    image_id = b0.get("image_id")
    if isinstance(image_id, str) and IMAGE_ID_RE.fullmatch(image_id):
        resolved["b0_image"] = {"image_id": image_id, "pull": "never"}
        if env_check:
            import subprocess

            proc = subprocess.run(
                ["docker", "image", "inspect", image_id, "--format", "{{.Id}}"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if proc.returncode != 0 or proc.stdout.strip() != image_id:
                _add(
                    blockers,
                    "B0_IMAGE_NOT_CACHED",
                    "B0",
                    f"cached image {image_id} is not available locally; refusing to pull",
                )
    baseline = b0.get("baseline_identity") or {}
    if baseline.get("status") != "OBSERVED_MATCHED" or baseline.get("matched_to_b1_b3") is not True:
        _add(
            blockers,
            "B0_BASELINE_IDENTITY_NOT_MATCHED",
            "B0",
            "native Cowrie baseline user/OS/kernel/shell/hostname/cwd is not observed as matched to the pinned "
            f"B1-B3 host fiction (status={baseline.get('status')!r}, "
            f"matched_to_b1_b3={baseline.get('matched_to_b1_b3')!r})",
            baseline.get("integration_request")
            or "observe the native baseline and use supported Cowrie hostname/userdb/filesystem fixtures; "
            "record architectural differences; do not claim H1 from unmatched environments",
        )
    # B0 has no generator blocker; its native shell is a local transport.
    resolved["b0"] = {
        "status": "EXECUTABLE_LOCAL_TRANSPORT_ONLY",
        "public_bind": False,
        "image_pull": "never",
        "baseline_identity_status": baseline.get("status", "NOT_ESTABLISHED"),
        "baseline_matched_to_b1_b3": baseline.get("matched_to_b1_b3") is True,
        "note": "B0 is not a RAGIN arm and cannot identify a generator or verification effect. "
        "A transport-only development smoke is allowed; a matched pilot or H1 claim is not.",
    }


def _check_analysis(contract: dict[str, Any], blockers: list[Blocker], resolved: dict[str, Any]) -> None:
    """Freeze the unresolved higher-level analysis facts as explicit blockers.

    The local package implements the Aalen-Johansen turn-12 CIF and the
    block-bootstrap/permutation contrasts. It does **not** implement the
    preregistered cause-specific Cox with block stratum, mixed-effects, or a
    family-level hierarchical model, and it has no powered family/cluster
    count. Those absences are never hidden behind a design-valid contract.
    """
    analysis = contract.get("analysis") or {}
    if analysis.get("acceptance_criteria") is None or _is_unresolved(analysis.get("acceptance_criteria")):
        _add(
            blockers,
            "UNRESOLVED_ACCEPTANCE_CRITERIA",
            "analysis",
            "no prespecified availability/utility acceptance criteria exist for H1-H5",
            "freeze acceptance criteria before any support claim; a missing or unexposed arm is not a zero effect",
        )
    higher = analysis.get("higher_level_model") or {}
    if not isinstance(higher, dict) or higher.get("status") != "IMPLEMENTED":
        _add(
            blockers,
            "HIGHER_LEVEL_STATS_NOT_IMPLEMENTED",
            "analysis",
            "cause-specific Cox with block stratum, mixed-effects and family-level hierarchical "
            "analysis are not implemented locally; only Aalen-Johansen CIF plus block "
            "bootstrap/permutation contrasts are supported",
            "land and test the preregistered higher-level model before a powered study; "
            "do not describe the local summary as the Cox model",
        )
    cluster_count = higher.get("adequate_family_count") if isinstance(higher, dict) else None
    if isinstance(cluster_count, bool) or not isinstance(cluster_count, int) or cluster_count < 1:
        _add(
            blockers,
            "UNRESOLVED_HIERARCHICAL_CLUSTER_COUNT",
            "analysis",
            f"adequate independent family/cluster count is {cluster_count!r}; the 2 development "
            "scenarios are diagnostic only",
            "prespecify the number of independent families/clusters and a powered sample before "
            "any confirmatory hierarchical analysis",
        )
    else:
        resolved["higher_level_model"] = {
            "status": higher.get("status"),
            "adequate_family_count": cluster_count,
        }


def _check_allocation(contract: dict[str, Any], blockers: list[Blocker], resolved: dict[str, Any]) -> None:
    allocation = contract.get("allocation") or {}
    if not _is_sha256(allocation.get("sequence_sha256")):
        return  # already recorded by _check_hashes
    scenarios = contract.get("track_b", {}).get("scenarios") or []
    profiles = contract.get("track_b", {}).get("profiles") or []
    arms = contract.get("track_b", {}).get("arms") or []
    seed = allocation.get("seed")
    if not isinstance(seed, int):
        _add(blockers, "UNRESOLVED_ALLOCATION", "allocation", f"allocation seed is {seed!r}")
        return
    if len(scenarios) != allocation.get("scenarios") or len(profiles) != allocation.get("attacker_profiles"):
        _add(
            blockers,
            "ALLOCATION_INPUT_MISMATCH",
            "allocation",
            "scenario/profile counts in track_b do not match the allocation arithmetic",
        )
        return
    from ragin.evaluation.attacker_policies import deterministic_allocation

    sequence = deterministic_allocation(
        scenario_ids=[item["scenario_id"] for item in scenarios],
        profile_ids=[item["profile_id"] for item in profiles],
        seeds=list(allocation.get("seeds_used") or []),
        arms=[item["arm"] if isinstance(item, dict) else item for item in arms],
        seed=seed,
    )
    if canonical_sha256(sequence) != allocation.get("sequence_sha256"):
        _add(
            blockers,
            "ALLOCATION_HASH_MISMATCH",
            "allocation",
            "recorded allocation sequence hash does not match the deterministic sequence",
        )
    else:
        resolved["allocation"] = {"seed": seed, "sequence_sha256": allocation["sequence_sha256"]}


def evaluate_readiness(
    contract: dict[str, Any],
    *,
    repo_root: Path | None = None,
    env_check: bool = False,
) -> ReadinessReport:
    """Evaluate execution readiness. Offline and side-effect free by default."""
    root = repo_root or Path(__file__).resolve().parents[2]
    design = validate_design(contract)
    blockers: list[Blocker] = []
    resolved: dict[str, Any] = {}
    warnings: list[str] = list(design.warnings)

    if design.status == DESIGN_INVALID:
        _add(blockers, "DESIGN_INVALID", "contract", "; ".join(design.errors))

    _check_hashes(contract, root, blockers, resolved)
    _check_generation(contract, root, blockers, resolved)
    _check_verification(contract, blockers, resolved)
    _check_resources(contract, blockers, resolved)
    _check_retrieval(contract, root, blockers, resolved)
    _check_b0(contract, blockers, resolved, env_check)
    _check_allocation(contract, blockers, resolved)
    _check_analysis(contract, blockers, resolved)

    attacker = contract.get("attacker") or {}
    if attacker.get("primary_kind") != "LLM":
        _add(
            blockers,
            "PRIMARY_ATTACKER_UNRESOLVED",
            "attacker",
            f"primary attacker kind is {attacker.get('primary_kind')!r}; "
            "scripted policies are integration controls only",
            "provide a frozen, configurable local LLM attacker adapter with prompts/tools hashed before real Track B",
        )
    if attacker.get("prompts_sha256") is None or _is_unresolved(attacker.get("prompts_sha256")):
        _add(blockers, "UNRESOLVED_ATTACKER_PROMPTS", "attacker", "attacker prompt hash unresolved")
    if attacker.get("blind_arm_labels") is not True:
        _add(blockers, "ATTACKER_NOT_BLINDED", "attacker", "attacker must be blind to arm labels")

    evaluation = contract.get("evaluation") or {}
    if evaluation.get("rubric_sha256") is None or _is_unresolved(evaluation.get("rubric_sha256")):
        _add(blockers, "UNRESOLVED_RUBRIC", "evaluation", "detection codebook/rubric hash unresolved")
    if evaluation.get("holdout_sealed") is not True:
        _add(
            blockers,
            "HOLDOUT_NOT_SEALED",
            "evaluation",
            "holdout must stay sealed until codebook and analysis are hashed",
        )

    if contract.get("execution_lock") != "COMPLETE":
        _add(
            blockers,
            "EXECUTION_LOCK_INCOMPLETE",
            "contract",
            f"execution_lock={contract.get('execution_lock')!r}",
            "complete the §13 execution-lock items and hash the final contract before any pilot session",
        )

    status = EXECUTION_READY if not blockers and design.status == DESIGN_VALID else EXECUTION_NOT_READY
    claim_boundary = {
        "design_validation_is_not_execution_readiness": True,
        "unresolved_is_never_ready": True,
        "model_substitution": "FORBIDDEN",
        "scripted_attacker_is_primary": False,
        "provider_calls": 0,
        "external_probes": "none; only an explicitly configured loopback attestation may be consumed",
    }
    return ReadinessReport(
        contract_id=str(contract.get("contract_id") or "unknown"),
        design=design,
        execution_status=status,
        blockers=blockers,
        warnings=warnings,
        resolved=resolved,
        claim_boundary=claim_boundary,
    )


def assert_execution_ready(contract: dict[str, Any], *, repo_root: Path | None = None) -> ReadinessReport:
    report = evaluate_readiness(contract, repo_root=repo_root)
    if not report.ready:
        raise ContractRefusal(report)
    return report


def build_child_env(
    base: dict[str, str],
    *,
    out_dir: Path,
    overrides: dict[str, str] | None = None,
    generation_credentials: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Build a child environment from an allow-list.

    Inherited provider/cloud credentials and proxies are not copied. Local
    generation credentials are accepted only as a separately authorized
    argument, are never returned in the audit value, and are never logged.
    """
    allow = ("PATH", "LANG", "LC_ALL", "TERM", "USER", "LOGNAME", "SHELL")
    env = {key: base[key] for key in allow if key in base}
    home = out_dir / "home"
    tmp = out_dir / "tmp"
    env.update(
        {
            "HOME": str(home),
            "TMPDIR": str(tmp),
            "PYTHONNOUSERSITE": "1",
            "PYTHONUNBUFFERED": "1",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "RAGIN_BIND_HOST": "127.0.0.1",
            "RAGIN_PROVIDER_ENABLED": "0",
            "RAGIN_REQUIRE_PROVIDER": "0",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "ALL_PROXY": "",
            "http_proxy": "",
            "https_proxy": "",
            "all_proxy": "",
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
        }
    )
    if overrides:
        env.update(overrides)
    credential_keys: list[str] = []
    if generation_credentials:
        for key, value in generation_credentials.items():
            upper = key.upper()
            if any(upper.startswith(prefix) for prefix in ("OPENROUTER", "OPENAI", "ANTHROPIC", "AZURE_", "AWS_")):
                raise ValueError(f"external provider credential name is not allowed here: {key}")
            env[key] = value
            credential_keys.append(key)
    audit: dict[str, Any] = {
        "policy": "allow-list; inherited credentials and proxies are not copied",
        "keys": sorted(env),
        "generation_credential_keys": sorted(credential_keys),
        "generation_credential_values": "NOT_RECORDED",
    }
    return env, audit

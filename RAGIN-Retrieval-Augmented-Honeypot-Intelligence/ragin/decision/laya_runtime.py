"""Local Laya inference runtime for the bounded decision boundary.

This is the REAL provider behind ``LayaAssessmentAdapter``'s ``infer`` callable
when ``RAGIN_LAYA_ENABLED=1``: it loads a pinned ``convaiinnovations/laya``
checkpoint locally (CPU by default), runs ``Router.predict`` with RAGIN's
typed questions, and returns a plain mapping shaped like a Jev System One
payload so the existing adapter contract (``JevResponse.from_payload``)
stays unchanged.

Design constraints (see docs/task1/JEV_TO_LAYA_MIGRATION_MAP.md):

- local and lazy: the Router is built on first use, not at import time;
- offline-first: ``HF_HUB_OFFLINE=1`` unless the caller explicitly allows
  downloads, so an assessment can never stall on the network;
- bounded: one pinned revision, ``max_loaded=1``, no preload;
- bounded decision only: this module never mutates fiction state and never
  bypasses the deterministic verifier — the decision adapter wraps failures as
  ``NO_SIGNAL`` and its output is never promoted directly to serving or commit.

Env knobs:
    RAGIN_LAYA_ENABLED   "1" to enable (default "0")
    RAGIN_LAYA_MODEL     checkpoint name (default "english")
    RAGIN_LAYA_REVISION  commit sha (default laya 0.4.2 pinned english revision)
    RAGIN_LAYA_DEVICE    "cpu" (default) or "cuda"
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import logging
import os
import threading
from pathlib import Path
from typing import Any

from ragin.decision.state_bounds import bound_state
from ragin.jev.models import choice_question, noul_question, score_question

logger = logging.getLogger(__name__)

DEFAULT_REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"  # laya 0.4.2 pinned english
DEFAULT_MODEL = "english"
DEFAULT_MODEL_SHA256 = "891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c"
SOURCE_REPOSITORY = "https://huggingface.co/convaiinnovations/laya"
MAX_STATE_CHARS = 8000
# Checkpoint names resolvable inside the pinned upstream repo. A local
# fine-tuned directory (for example models/laya_v12_..._final_v1) is NOT one of
# these names and cannot be served by LayaRuntime: _checkpoint_path() is hard-
# coded to models--convaiinnovations--laya, and Router gets the name, not a
# local path. Keeping this list explicit prevents an experiment checkpoint from
# being mistaken for the served model.
UPSTREAM_CHECKPOINT_NAMES = frozenset({"english", "multilingual", "typed-decisions"})


def laya_enabled() -> bool:
    return os.environ.get("RAGIN_LAYA_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


def eval_requires_real_model() -> bool:
    return os.environ.get("RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL", "0").strip() == "1"


def _state_tail(state: str) -> str:
    # Shared bound: the "..." marker is inside MAX_STATE_CHARS, never on top.
    return bound_state(state, MAX_STATE_CHARS)[0]


_QUESTIONS_JEV_FORMAT: dict[str, dict] = {
    "attack": noul_question(
        "Does the SSH session in `session` reflect malicious attacker activity?",
        true_criteria="recon, exploitation, persistence, credential theft, exfiltration or evidence erasure",
        false_criteria="ordinary administrative or benign activity",
    ).model_dump_for_api(),
    "stage": choice_question(
        "What is the primary attack stage of the SSH session in `session`?",
        options=[
            "benign_administration",
            "recon",
            "persistence",
            "credential_theft",
            "lateral_movement",
            "exfiltration",
            "cleanup",
        ],
        criteria={
            "benign_administration": "ordinary administrative work",
            "recon": "probing, scanning or discovery",
            "persistence": "implanting a foothold",
            "credential_theft": "harvesting credentials or keys",
            "lateral_movement": "pivoting to other hosts",
            "exfiltration": "copying data out",
            "cleanup": "erasing evidence",
        },
    ).model_dump_for_api(),
    "severity": score_question(
        "How dangerous is the SSH session in `session`?",
        minimum=0,
        maximum=3,
        criteria=[
            "no impact",
            "suspicious but contained",
            "clear attack activity",
            "high-impact attack in progress",
        ],
    ).model_dump_for_api(),
}


def default_questions() -> dict[str, dict]:
    """Typed questions in Jev wire format, mapped into laya's question schema.

    Jev uses ``{"question", "type", "criteria"/"options"/"min", "max"}`;
    laya 0.4.2 requires ``{"type", "instructions", "criteria"}`` and takes a
    choice's option list inside ``criteria`` itself. The mapping is lossless
    for the question shapes RAGIN uses (noul/choice/score).
    """
    laya_questions: dict[str, dict] = {}
    for qid, qdef in _QUESTIONS_JEV_FORMAT.items():
        qtype = qdef["type"]
        # _QUESTIONS_JEV_FORMAT entries were built through
        # JevQuestion.model_dump_for_api(), which serialises the prompt field
        # as ``instructions`` (the Jev wire name) — there is no ``question``
        # key to read here.
        prompt = qdef.get("instructions") or qdef.get("question")
        if not prompt:
            raise ValueError(f"question {qid!r} carries no instructions")
        mapped: dict = {"type": qtype, "instructions": prompt}
        crit = qdef.get("criteria")
        if qtype == "choice":
            # Jev splits options/criteria; laya wants criteria keyed by option
            # label, with the description as the value.
            options = qdef.get("options") or []
            criteria = dict(crit) if isinstance(crit, dict) else {}
            laya_questions[qid] = {
                "type": qtype,
                "instructions": mapped["instructions"],
                "criteria": {opt: criteria.get(opt, opt.replace("_", " ")) for opt in options},
            }
        elif qtype == "score":
            laya_questions[qid] = {
                "type": qtype,
                "instructions": mapped["instructions"],
                "criteria": list(crit or []),
            }
        else:  # noul
            laya_questions[qid] = {
                "type": qtype,
                "instructions": mapped["instructions"],
                "criteria": dict(crit) if isinstance(crit, dict) else None,
            }
    return laya_questions


class LayaRuntime:
    """Lazy, thread-safe, revision-pinned local inference against the real model."""

    def __init__(
        self,
        *,
        model: str | None = None,
        revision: str | None = None,
        device: str | None = None,
    ) -> None:
        self._model = model or os.environ.get("RAGIN_LAYA_MODEL", "english")
        self._revision = revision or os.environ.get("RAGIN_LAYA_REVISION", DEFAULT_REVISION)
        self._device = device or os.environ.get("RAGIN_LAYA_DEVICE", "cpu")
        self._router = None
        self._model_initialized = False
        self._checkpoint_sha256: str | None = None
        self._checkpoint_verified: bool | None = None
        self._lock = threading.Lock()
        if self._model not in UPSTREAM_CHECKPOINT_NAMES:
            logger.warning(
                "RAGIN_LAYA_MODEL=%r is not a checkpoint name in %s %s; the "
                "fine-tuned checkpoint at models/%s is NOT loaded by this "
                "runtime (expect NO_SIGNAL). Serve the upstream base only, or "
                "extend LayaRuntime with an explicit local-path loader and "
                "digest before claiming fine-tuned integration.",
                self._model,
                SOURCE_REPOSITORY,
                sorted(UPSTREAM_CHECKPOINT_NAMES),
                self._model,
            )

    @property
    def model(self) -> str:
        return self._model

    @property
    def revision(self) -> str:
        return self._revision

    @property
    def device(self) -> str:
        return self._device

    def checkpoint_provenance(self) -> dict[str, Any]:
        """Cheap provenance for health/audit — never loads or hashes weights.

        ``served_checkpoint`` distinguishes the pinned upstream base from an
        experiment checkpoint name. ``fine_tuned_checkpoint_loaded`` is always
        False in this runtime; the v10/v11/v12 checkpoints under ``models/``
        are training/evaluation artifacts, not serving weights.
        """
        upstream = self._model in UPSTREAM_CHECKPOINT_NAMES
        return {
            "enabled": laya_enabled(),
            "model": self._model,
            "revision": self._revision,
            "source_repository": SOURCE_REPOSITORY,
            "served_checkpoint": "upstream_base" if upstream else "unsupported_local_or_custom",
            "fine_tuned_checkpoint_loaded": False,
            "checkpoint_path": str(self._checkpoint_path()),
            "note": (
                "LayaRuntime serves the pinned upstream checkpoint only; "
                "fine-tuned checkpoints under models/ require an explicit "
                "local-path loader before they can be called integrated."
            ),
        }

    def _checkpoint_path(self) -> Path:
        hub_cache = os.environ.get("HF_HUB_CACHE")
        if hub_cache:
            root = Path(hub_cache)
        else:
            hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface"))
            root = hf_home / "hub"
        return root / "models--convaiinnovations--laya" / "snapshots" / self._revision / "model.safetensors"

    def _expected_checkpoint_sha256(self) -> str | None:
        explicit = os.environ.get("RAGIN_LAYA_CHECKPOINT_SHA256", "").strip().lower()
        if explicit:
            return explicit
        if self._model == DEFAULT_MODEL and self._revision == DEFAULT_REVISION:
            return DEFAULT_MODEL_SHA256
        return None

    def _verify_checkpoint(self) -> tuple[bool, str | None, Path]:
        if self._checkpoint_verified is not None:
            return self._checkpoint_verified, self._checkpoint_sha256, self._checkpoint_path()
        path = self._checkpoint_path()
        expected = self._expected_checkpoint_sha256()
        if not path.is_file() or expected is None:
            self._checkpoint_verified = False
            return False, None, path
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        self._checkpoint_sha256 = digest.hexdigest()
        self._checkpoint_verified = self._checkpoint_sha256 == expected
        return self._checkpoint_verified, self._checkpoint_sha256, path

    def manifest(self) -> dict[str, Any]:
        checkpoint_verified, checkpoint_sha256, checkpoint_path = self._verify_checkpoint()
        try:
            package_version = importlib.metadata.version("laya")
        except importlib.metadata.PackageNotFoundError:
            package_version = None
        return {
            "runtime_verified": bool(self._model_initialized and checkpoint_verified and package_version),
            "checkpoint_verified": checkpoint_verified,
            "fixture_injection_present": False,
            "fallback_possible": True,
            "real_inference_entrypoint": "ragin.decision.laya_runtime:LayaRuntime.infer -> laya.Router.predict",
            "model_hash": checkpoint_sha256,
            "package_version": package_version,
            "source_repository": SOURCE_REPOSITORY,
            "repository": "convaiinnovations/laya",
            "model": self._model,
            "revision": self._revision,
            "served_checkpoint": (
                "upstream_base" if self._model in UPSTREAM_CHECKPOINT_NAMES else "unsupported_local_or_custom"
            ),
            "fine_tuned_checkpoint_loaded": False,
            "checkpoint": str(checkpoint_path),
            "device": self._device,
            "model_initialized": self._model_initialized,
        }

    def ensure_real_model(self) -> None:
        """Fail closed in evaluation mode and force real checkpoint loading."""
        manifest = self.manifest()
        if not manifest["checkpoint_verified"]:
            raise RuntimeError("Laya checkpoint unavailable or SHA256 identity mismatch")
        try:
            import laya  # noqa: F401
        except Exception as exc:  # pragma: no cover - environment guard
            raise RuntimeError("real Laya package is unavailable") from exc
        router = self._get_router()
        router.load(self._model)
        self._model_initialized = True

    def _get_router(self):
        if self._router is not None:
            return self._router
        with self._lock:
            if self._router is not None:
                return self._router
            import os as _os

            if "HF_HUB_OFFLINE" not in _os.environ:
                _os.environ["HF_HUB_OFFLINE"] = "1"
            from laya import Router

            expected = self._expected_checkpoint_sha256()
            digest_map = {self._model: {"model.safetensors": expected}} if expected else {}
            self._router = Router(
                device=self._device,
                revisions={self._model: self._revision},
                max_loaded=1,
                preload=False,
                sha256_digests=digest_map,
            )
        return self._router

    def infer(self, state: str) -> dict:
        """Run a real forward pass and return a JevResponse-compatible payload.

        Raises on any failure — the adapter converts failures to NO_SIGNAL.
        """
        router = self._get_router()
        questions = default_questions()
        result = router.predict(
            state={"session": _state_tail(state)},
            questions=questions,
            model=self._model,
        )
        self._model_initialized = True
        answers = result["answers"]

        # laya emits its own answer keys per qtype (noul/choice with
        # probabilities, score with legend+probabilities); mirror them into the
        # Jev wire shape directly below. laya.common is deliberately not
        # imported here: older builds may lack it, and the payload construction
        # below does not depend on it (the previous availability import was
        # consumed nowhere).

        payload: dict = {"model": f"laya/{self._model}", "answers": {}, "native_output": result}
        for qid, qdef in questions.items():
            a = answers[qid]
            qtype = qdef.get("type")
            if qtype == "noul":
                payload["answers"][qid] = {"type": "noul", "noul": a.get("noul"), "confidence": a.get("confidence")}
            elif qtype == "choice":
                payload["answers"][qid] = {
                    "type": "choice",
                    "choice": a.get("choice"),
                    "probabilities": a.get("probabilities") or {},
                }
            elif qtype == "score":
                criterion = qdef.get("criteria") or []
                legend = {str(i): c for i, c in enumerate(criterion)}
                # laya score answers carry per-level probabilities keyed as strings
                probs = a.get("probabilities") or {}
                best_key = max(probs, key=lambda k: probs[k]) if probs else str(a.get("answer") or 0)
                payload["answers"][qid] = {
                    "type": "score",
                    "score": float(best_key),
                    "confidence": a.get("confidence", 0.0),
                    "legend": legend,
                    "probabilities": probs,
                }
            else:  # pragma: no cover - contract guard
                raise ValueError(f"unsupported question type: {qtype!r}")

        payload["answers"] = {
            qid: ans for qid, ans in payload["answers"].items() if ans is not None
        }
        # JevResponse.usage is dict[str, int]; laya's usage carries a list
        # field (truncated_questions) that Jev cannot model — drop non-ints.
        usage = {k: v for k, v in (result.get("usage") or {}).items() if isinstance(v, int)}
        payload["usage"] = usage
        payload["laya_revision"] = self._revision
        payload["routing"] = result.get("routing")
        return payload


_SHARED: LayaRuntime | None = None
_SHARED_LOCK = threading.Lock()


def get_shared_runtime() -> LayaRuntime:
    global _SHARED
    if _SHARED is None:
        with _SHARED_LOCK:
            if _SHARED is None:
                _SHARED = LayaRuntime()
    return _SHARED


def make_infer_callable():
    """Build the ``infer`` callable for ``LayaAssessmentAdapter`` when enabled.

    Returns None when Laya is disabled so RAGIN keeps baseline behaviour.
    """
    if eval_requires_real_model() and not laya_enabled():
        raise RuntimeError("RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL=1 requires RAGIN_LAYA_ENABLED=1")
    if not laya_enabled():
        return None
    runtime = get_shared_runtime()
    if eval_requires_real_model():
        runtime.ensure_real_model()
    return runtime.infer

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from ragin.decision.bounded_worker import shared_infer_worker
from ragin.decision.state_bounds import bound_state
from ragin.jev.models import JevAssessment, JevResponse

DecisionStatus = Literal["SIGNAL", "NO_SIGNAL"]


@dataclass(frozen=True)
class OptionalAssessment:
    status: DecisionStatus
    provider: str
    model: str
    assessment: JevAssessment | None = None
    error: str | None = None
    latency_ms: float = 0.0

    @classmethod
    def no_signal(
        cls,
        *,
        provider: str,
        model: str,
        error: str,
        latency_ms: float = 0.0,
    ) -> OptionalAssessment:
        return cls(
            status="NO_SIGNAL",
            provider=provider,
            model=model,
            error=error,
            latency_ms=latency_ms,
        )


class AssessmentProvider(Protocol):
    def assess(self, *, session_id: str, state: str) -> OptionalAssessment:
        ...


class LayaAssessmentAdapter:
    def __init__(
        self,
        infer: Callable[[str], Mapping[str, Any]],
        *,
        model: str,
        timeout_s: float = 2.0,
        max_state_chars: int = 8000,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        if max_state_chars <= 0:
            raise ValueError("max_state_chars must be positive")
        self._infer = infer
        self._model = model
        self._timeout_s = timeout_s
        self._max_state_chars = max_state_chars

    def assess(self, *, session_id: str, state: str) -> OptionalAssessment:
        bounded_state, _truncated = bound_state(state, self._max_state_chars)
        started = time.monotonic()
        # Bounded admission on the shared worker: busy is an explicit NO_SIGNAL,
        # and a timed-out callable keeps its slot until it actually finishes.
        status, value = shared_infer_worker().run(self._infer, bounded_state, self._timeout_s)
        if status == "busy":
            return OptionalAssessment.no_signal(
                provider="laya",
                model=self._model,
                error="busy",
                latency_ms=(time.monotonic() - started) * 1000,
            )
        if status == "timeout":
            return OptionalAssessment.no_signal(
                provider="laya",
                model=self._model,
                error="timeout",
                latency_ms=(time.monotonic() - started) * 1000,
            )
        if status == "error":
            return OptionalAssessment.no_signal(
                provider="laya",
                model=self._model,
                error=type(value).__name__,
                latency_ms=(time.monotonic() - started) * 1000,
            )
        payload = value
        try:
            if not isinstance(payload, Mapping):
                raise TypeError("assessment payload must be a mapping")
            if payload.get("status") == "NO_SIGNAL":
                return OptionalAssessment.no_signal(
                    provider="laya",
                    model=self._model,
                    error="provider_no_signal",
                    latency_ms=(time.monotonic() - started) * 1000,
                )
            response = JevResponse.from_payload(dict(payload))
            if not response.answers:
                raise ValueError("assessment payload has no typed answers")
            assessment = JevAssessment(
                session_id=session_id,
                state_preview=bounded_state[:400],
                answers=response.answers,
                questions={},
                model=response.model or self._model,
                usage=response.usage,
            )
            return OptionalAssessment(
                status="SIGNAL",
                provider="laya",
                model=assessment.model,
                assessment=assessment,
                latency_ms=(time.monotonic() - started) * 1000,
            )
        except Exception as exc:
            return OptionalAssessment.no_signal(
                provider="laya",
                model=self._model,
                error=type(exc).__name__,
                latency_ms=(time.monotonic() - started) * 1000,
            )

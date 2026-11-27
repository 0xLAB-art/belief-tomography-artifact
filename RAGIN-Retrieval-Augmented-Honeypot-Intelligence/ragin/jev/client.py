"""JevClient — HTTPS client for the Jev Decisions API (System One endpoint).

Jev is served as a behavior-key (System One) model. RAGIN talks to the
beatapi Decisions API's /v1/systemone route, which exposes the free
``jev-1.14-free`` model:

    POST https://api.beatapi.io/v1/systemone
    Authorization: Bearer $RAGIN_JEVI_API_KEY
    {"model": "jev-1.14-free", "state": "...", "questions": {...}}

Unlike chat models it returns *typed answers* (noul/choice/score), not
generated text — see ragin.jev.models. Question prompts travel under the
wire key ``instructions`` (TypeSafe-compatible); /v1/decisions is an alias.

Endpoint details:
  - Base URL   : RAGIN_JEVI_BASE_URL (default https://api.beatapi.io/v1)
  - API key    : RAGIN_JEVI_API_KEY  (no default — required, not "public")
  - Model      : RAGIN_JEVI_MODEL    (default "jev-1.14-free")

The client reflects GatewayClient's conventions (env-first resolution,
transient-failure retries, caller keeps circuit-breaker/fallback logic).
"""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Any

import requests

from ragin.jev.models import JevQuestion, JevResponse

if TYPE_CHECKING:
    from ragin.jev.models import JevAssessment

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.beatapi.io/v1"
_DEFAULT_API_KEY = ""  # required — the beatapi endpoint has no public tier
_DEFAULT_MODEL = "jev-1.14-free"

_MAX_RETRIES = 1
_BASE_BACKOFF = 1.0

# A 429 response is a *quota* condition, not a transient one: the free tier
# allows only a small burst, so retrying quickly burns the budget without
# progress. Clients must fail fast so callers degrade gracefully (Jev is
# additive by design), and optionally park the endpoint for a cool-off so
# subsequent calls fail in microseconds instead of waiting on timeouts.
_RATE_LIMIT_COOLDOWN_S = 60.0

# Cap on the serialized state sent per call. Long sessions must be tail-
# truncated (recent commands are the most decision-relevant) to keep
# payloads small and latency predictable.
_MAX_STATE_CHARS = 8000


class JevClient:
    """Typed-question client for the Jev System One endpoint.

    Usage::

        client = JevClient()
        response = client.systemone(
            state="Command output being assessed...",
            questions={"attack": noul_question("...", ...)},
        )
        if response.noul_probability("attack") > 0.8:
            ...
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        # Env-first resolution: explicit args win, then RAGIN_JEVI_* vars.
        self._base_url = (base_url or os.environ.get("RAGIN_JEVI_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")
        self._api_key = api_key or os.environ.get("RAGIN_JEVI_API_KEY") or _DEFAULT_API_KEY
        self._model = model or os.environ.get("RAGIN_JEVI_MODEL") or _DEFAULT_MODEL
        self._timeout = timeout
        self._session = requests.Session()  # connection reuse across calls
        self._rate_limited_until = 0.0  # monotonic deadline while parked

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model(self) -> str:
        return self._model

    def systemone(
        self,
        state: str,
        questions: dict[str, JevQuestion],
        model: str | None = None,
    ) -> JevResponse:
        """Submit a System One call: typed questions over a textual state.

        Raises requests.RequestException on transport / server / non-200
        responses so callers retain their own retry / fallback logic.
        Long states are tail-truncated to ``_MAX_STATE_CHARS``.
        """
        if len(state) > _MAX_STATE_CHARS:
            state = "..." + state[-_MAX_STATE_CHARS:]
        url = f"{self._base_url}/systemone"
        payload: dict[str, Any] = {
            "model": model or self._model,
            "state": state,
            "questions": {key: q.model_dump_for_api() for key, q in questions.items()},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        resp = self._post(url, payload, headers)
        data = resp.json()
        return JevResponse.from_payload(data)

    def assess(
        self,
        *,
        session_id: str,
        state: str,
        questions: dict[str, JevQuestion],
        model: str | None = None,
        state_preview_max: int = 400,
    ) -> JevAssessment:
        """Run ``systemone`` and wrap the result in a JevAssessment.

        Keeps the raw typed answers plus a preview of the state so
        classification / orchestration code can attach the assessment
        without keeping the full state around.
        """
        from ragin.jev.models import JevAssessment

        response = self.systemone(state=state, questions=questions, model=model)
        return JevAssessment(
            session_id=session_id,
            state_preview=state[:state_preview_max],
            answers=response.answers,
            questions={key: q.question for key, q in questions.items()},
            model=response.model,
            usage=response.usage,
        )

    # ── Transport ────────────────────────────────────────────────────────

    def _park_if_rate_limited(self, resp: requests.Response) -> bool:
        """Park the endpoint when the server signals quota exhaustion.

        Respects a server-provided Retry-After header when present, else
        parks for ``_RATE_LIMIT_COOLDOWN_S``. Returns True when parked.
        """
        if resp.status_code != 429:
            return False
        retry_after = resp.headers.get("Retry-After")
        try:
            delay = float(retry_after) if retry_after else _RATE_LIMIT_COOLDOWN_S
        except ValueError:
            delay = _RATE_LIMIT_COOLDOWN_S
        self._rate_limited_until = time.monotonic() + max(delay, 1.0)
        logger.warning("Jev rate limited — parking endpoint for %.0fs", self._rate_limited_until - time.monotonic())
        return True

    def _post(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> requests.Response:
        # Open-circuit fast-fail while parked after a 429.
        if time.monotonic() < self._rate_limited_until:
            raise requests.HTTPError(f"429 rate-limited (cool-off {_RATE_LIMIT_COOLDOWN_S:.0f}s active)")
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            if attempt > 0:
                backoff = _BASE_BACKOFF * (2 ** (attempt - 1))
                logger.warning("Jev POST attempt %d/%d, sleeping %.0fs", attempt + 1, _MAX_RETRIES + 1, backoff)
                time.sleep(backoff)
            try:
                resp = self._session.post(url, json=payload, headers=headers, timeout=self._timeout)
                if self._park_if_rate_limited(resp):
                    last_exc = requests.HTTPError(
                        f"{resp.status_code} {resp.text[:160]}",
                        response=resp,
                    )
                    continue  # do not retry 429: fail fast, caller degrades
                if resp.status_code in (408, 500, 502, 503, 504):
                    last_exc = requests.HTTPError(
                        f"{resp.status_code} {resp.text[:160]}",
                        response=resp,
                    )
                    continue
                resp.raise_for_status()
                return resp
            except (requests.ConnectionError, requests.ReadTimeout) as exc:
                last_exc = exc
                continue
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in (408, 500, 502, 503, 504):
                    last_exc = exc
                    continue
                raise
        raise requests.ReadTimeout(f"Jev POST failed after {_MAX_RETRIES + 1} attempts: {last_exc}") from last_exc

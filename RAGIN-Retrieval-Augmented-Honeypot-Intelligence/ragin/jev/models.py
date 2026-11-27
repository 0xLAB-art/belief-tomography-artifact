"""Pydantic models for Jev System One typed answers.

Jev is a System One (behavior-key) model, not a chat LLM: it answers a set
of *typed questions* about a *state* instead of generating text. Question
types (from the TypeSafe/jev docs):
  - noul:   binary verdict with a calibrated probability in [0,1]
  - score:  number in [min, max] with per-bin probabilities + legend
  - choice: single/multi selection from options with probabilities

A RAGIN caller submits ``{"model", "state", "questions"}`` and receives
``{"answers", "usage", "cost"}``. These models normalise that payload into
typed objects safe to attach to classifications and routing decisions.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

QuestionType = Literal["noul", "choice", "score"]


# ── Question construction helpers ────────────────────────────────────────────


class JevQuestion(BaseModel):
    """A single typed question for the Jev System One API."""

    question: str = Field(min_length=1)
    type: QuestionType
    criteria: list[str] | dict[str, str] | None = None
    min: int | None = None
    max: int | None = None
    allow_multi: bool = False
    options: list[str] | None = None

    @field_validator("question")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        return v.strip()

    def model_dump_for_api(self) -> dict[str, Any]:
        """Serialise into the Jev wire format (drops empty fields).

        The beatapi Decisions API names the prompt field ``instructions`` on
        the wire; the Python-side field stays ``question`` so builders and
        callers are unaffected by the endpoint move.
        """
        payload: dict[str, Any] = {"instructions": self.question, "type": self.type}
        for field in ("criteria", "min", "max", "options"):
            value = getattr(self, field)
            if value is not None and value != [] and value != {}:
                payload[field] = value
        if self.allow_multi:
            payload["allow_multi"] = True
        return payload


def noul_question(question: str, *, true_criteria: str, false_criteria: str) -> JevQuestion:
    """Binary yes/no question (noul). Criteria describe each side for the model."""
    return JevQuestion(
        question=question,
        type="noul",
        criteria={"true": true_criteria, "false": false_criteria},
    )


def score_question(
    question: str,
    *,
    minimum: int,
    maximum: int,
    criteria: list[str],
) -> JevQuestion:
    """Scaled question in [minimum, maximum]; criteria[row] labels bin row."""
    if len(criteria) != (maximum - minimum + 1):
        raise ValueError("score criteria length must equal max - min + 1")
    return JevQuestion(question=question, type="score", min=minimum, max=maximum, criteria=criteria)


def choice_question(
    question: str,
    *,
    options: list[str],
    criteria: dict[str, str] | None = None,
    allow_multi: bool = False,
) -> JevQuestion:
    """Multiple-choice question over options (single or multi-select).

    The live endpoint requires ``criteria`` as a mapping of option -> short
    description guiding the model; auto-detects sensible defaults when the
    caller omits it.
    """
    if not options:
        raise ValueError("choice question requires at least one option")
    if criteria is None:
        criteria = {opt: opt.replace("_", " ") for opt in options}
    return JevQuestion(
        question=question,
        type="choice",
        options=options,
        criteria=criteria,
        allow_multi=allow_multi,
    )


# ── Typed answers ─────────────────────────────────────────────────────────────


class NoulAnswer(BaseModel):
    type: Literal["noul"] = "noul"
    noul: float = Field(ge=0.0, le=1.0)


class ScoreAnswer(BaseModel):
    type: Literal["score"] = "score"
    # allow_inf_nan=False: a NaN/inf score would poison downstream consumers
    # (argmax over probabilities, int(round(severity)) in routing) — a hostile
    # or buggy provider payload must fail validation, not routing.
    score: float = Field(allow_inf_nan=False)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, allow_inf_nan=False)
    legend: dict[str, str] = Field(default_factory=dict)
    probabilities: dict[str, float] = Field(default_factory=dict)

    @field_validator("probabilities")
    @classmethod
    def _finite_probabilities(cls, value: dict[str, float]) -> dict[str, float]:
        for label, probability in value.items():
            if not isinstance(probability, (int, float)) or isinstance(probability, bool):
                raise ValueError(f"probability for {label!r} is not a number")
            if probability != probability or probability in (float("inf"), float("-inf")):
                raise ValueError(f"probability for {label!r} is not finite")
            if not 0.0 <= float(probability) <= 1.0:
                raise ValueError(f"probability for {label!r} is outside [0, 1]")
        return value

    @property
    def top_label(self) -> str:
        """The legend label with the highest probability."""
        if not self.legend or not self.probabilities:
            return ""
        best_key = max(self.probabilities, key=lambda k: self.probabilities[k])
        return self.legend.get(best_key, "")

    @property
    def top_probability(self) -> float:
        return max(self.probabilities.values(), default=0.0)


class ChoiceAnswer(BaseModel):
    type: Literal["choice"] = "choice"
    choice: str | list[str]
    allow_multi: bool = False
    probabilities: dict[str, float] = Field(default_factory=dict)

    @property
    def options_selected(self) -> list[str]:
        if isinstance(self.choice, list):
            return self.choice
        return [self.choice] if self.choice else []


JevTypedAnswer = NoulAnswer | ScoreAnswer | ChoiceAnswer
# Public alias (the module is the public spelling users import).
JevAnswer = JevTypedAnswer


def parse_answer(raw: dict[str, Any]) -> JevTypedAnswer:
    """Dispatch a raw ``answers[key]`` dict from Jev to its typed model."""
    answer_type = raw.get("type")
    if answer_type == "noul":
        return NoulAnswer(**raw)
    if answer_type == "score":
        return ScoreAnswer(**raw)
    if answer_type == "choice":
        return ChoiceAnswer(**raw)
    raise ValueError(f"Unknown Jev answer type: {answer_type!r}")


# ── Full response and RAGIN-facing assessment ─────────────────────────────────


class JevResponse(BaseModel):
    """Normalised response from the Jev System One endpoint."""

    model: str = ""
    answers: dict[str, JevTypedAnswer]
    usage: dict[str, int] = Field(default_factory=dict)
    cost: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> JevResponse:
        answers = {key: parse_answer(val) for key, val in payload.get("answers", {}).items()}
        return cls(
            model=payload.get("model", ""),
            answers=answers,
            usage=payload.get("usage", {}),
            cost=str(payload.get("cost", "")),
        )


class AttackKind(str, Enum):
    BRUTEFORCE = "bruteforce"
    SCANNING = "scanning"
    EXPLOIT = "exploit"
    PERSISTENCE = "persistence"
    LATERAL = "lateral"
    UNKNOWN = "unknown"


class JevAssessment(BaseModel):
    """RAGIN-facing wrapper around one Jev call.

    ``raw`` keeps the full typed answers; the convenience attributes feed
    classification and orchestration without coupling them to Jev's schema.
    """

    session_id: str
    state_preview: str = ""
    answers: dict[str, JevTypedAnswer] = Field(default_factory=dict)
    questions: dict[str, str] = Field(default_factory=dict)
    model: str = ""
    usage: dict[str, int] = Field(default_factory=dict)

    # ── Convenience helpers ───────────────────────────────────────────────

    def answer(self, key: str) -> JevTypedAnswer | None:
        return self.answers.get(key)

    def noul_probability(self, key: str) -> float | None:
        answer = self.answers.get(key)
        if isinstance(answer, NoulAnswer):
            return answer.noul
        return None

    def score_value(self, key: str) -> float | None:
        answer = self.answers.get(key)
        if isinstance(answer, ScoreAnswer):
            return answer.score
        return None

    def selected_options(self, key: str) -> list[str]:
        answer = self.answers.get(key)
        if isinstance(answer, ChoiceAnswer):
            return answer.options_selected
        return []

    @property
    def attack_probability(self) -> float | None:
        """Raw Jev probability for the 'attack' noul question, if present."""
        return self.noul_probability("attack")

    @property
    def is_attack(self) -> bool | None:
        """True when the 'attack' noul question indicates an attack (>=0.5)."""
        prob = self.attack_probability
        return None if prob is None else prob >= 0.5

    @property
    def severity(self) -> float | None:
        return self.score_value("severity")

    @property
    def attack_kind(self) -> AttackKind | None:
        selected = self.selected_options("attack_kind")
        if not selected:
            return None
        try:
            return AttackKind(selected[0])
        except ValueError:
            return AttackKind.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state_preview": self.state_preview,
            "answers": {key: answer.model_dump() for key, answer in self.answers.items()},
            "questions": self.questions,
            "model": self.model,
            "usage": self.usage,
        }

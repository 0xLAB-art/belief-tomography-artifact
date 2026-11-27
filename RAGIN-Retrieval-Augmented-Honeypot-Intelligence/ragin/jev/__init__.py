"""Jev — System One behavior-key integration for RAGIN.

Jev is a fast, free System One model (served via the opencode zen gateway
at /v1/systemone with ``Bearer public``). Unlike chat LLMs it answers
*typed questions* (noul/choice/score) about a *state* rather than
generating text — a perfect additive signal for classification and
orchestration.

Components:

- :mod:`ragin.jev.models`      — question/answer models (noul, choice, score)
- :mod:`ragin.jev.client`      — JevClient (HTTP transport, env config)
- :mod:`ragin.jev.assessment`  — JevAssessor (state + question builders)
- :mod:`ragin.jev.orchestration` — Reviewer/advisory glue for cycle coordination

This is an *additive* module: Jev never replaces Chrollo/Don/Hisoka — it
provides a complementary, free, low-latency decision signal.
"""

from ragin.jev.assessment import JevAssessor, JevError
from ragin.jev.client import JevClient
from ragin.jev.models import (
    AttackKind,
    ChoiceAnswer,
    JevAnswer,
    JevAssessment,
    JevQuestion,
    JevResponse,
    NoulAnswer,
    ScoreAnswer,
    choice_question,
    noul_question,
    parse_answer,
    score_question,
)
from ragin.jev.orchestration import (
    JevReviewer,
    JevRoutingSignal,
    SupervisorJevMixin,
)

__all__ = [
    "AttackKind",
    "ChoiceAnswer",
    "JevAnswer",
    "JevAssessment",
    "JevAssessor",
    "JevClient",
    "JevError",
    "JevQuestion",
    "JevResponse",
    "JevReviewer",
    "JevRoutingSignal",
    "NoulAnswer",
    "ScoreAnswer",
    "SupervisorJevMixin",
    "choice_question",
    "noul_question",
    "parse_answer",
    "score_question",
]

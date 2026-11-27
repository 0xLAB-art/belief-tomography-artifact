from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from .config import ARMS


class MatchedArmRunner:
    def __init__(self, pipeline_factory: Callable[[str], Any]) -> None:
        self.pipeline_factory = pipeline_factory

    def run_case(self, session_id: str, attacker_input: str, context: dict[str, Any]) -> dict[str, Any]:
        results = {}
        for arm in ARMS:
            pipeline = self.pipeline_factory(arm)
            arm_context = copy.deepcopy(context)
            results[arm] = pipeline.invoke(f"{session_id}:{arm}", attacker_input, arm_context)
        return results

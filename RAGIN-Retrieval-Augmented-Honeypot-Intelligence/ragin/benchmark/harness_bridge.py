"""Bridge: converts live Harness pipeline output into benchmark metrics.

This module runs ``Harness.process_with_threat_modeling()`` against the standard
benchmark query sets and produces ``EffectivenessMetrics`` + per-turn
``BenchmarkResult`` lists that can be fed into the existing
``EffectivenessBenchmark``, ``HoneyGPTBenchmark``, and report generators.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from ragin.benchmark.core import (
    CTI_ACTOR_QUERIES,
    CTI_TECHNIQUE_QUERIES,
    PERSONA_REALISM_QUERIES,
    BenchmarkResult,
    generate_report,
)
from ragin.benchmark.core import (
    _score_actor_match as _core_score_actor_match,
)
from ragin.benchmark.core import (
    _score_technique_match as _core_score_technique_match,
)
from ragin.benchmark.effectiveness import EffectivenessMetrics
from ragin.cycle.coordination import VotingSystem
from ragin.cycle.multi_turn import MultiTurnTracker, SessionTTPSummary

logger = logging.getLogger(__name__)

# ── Declared scoring channels (2026-09-27 rubric-diff investigation) ──────
# Two legitimate measurement channels exist and must NEVER be silently mixed:
#   SERVED_TEXT     the deception surface the attacker actually sees
#   CTI_ANALYSIS    the pipeline's intelligence channel (Don extraction:
#                   ttps_extracted / candidate_actors), NOT shown to attackers
# The Sep-22 campaign scored technique/actor rows by max()ing both channels;
# the W1 external-baseline arms scored served text only — comparing the two
# as one number produced a phantom generator-model regression (see
# results/technique_rubric_diff_investigation.json). Every artifact now
# declares the channel its scores were computed in.
CHANNEL_SERVED_TEXT = "served_text"
CHANNEL_BOTH_MAX = "served_text+cti_analysis_max"


@dataclass
class TurnOutcome:
    query: str
    response_text: str
    classification: dict[str, Any]
    cti_analysis: dict[str, Any]
    deception: dict[str, Any]
    verification: dict[str, Any]
    total_time_ms: float
    error: str | None = None
    technique_mentioned: str = ""
    actor_mentioned: str = ""
    persona_name: str = ""
    persona_matches: bool = False
    passed_verification: bool = False
    ttps_extracted: list[str] = field(default_factory=list)
    artifact_accessed: bool = False
    is_error: bool = False


def _extract_ttps(cti_analysis: dict[str, Any]) -> list[str]:
    ttps: list[str] = []
    for ttp in cti_analysis.get("ttps_seen", []):
        if isinstance(ttp, str):
            ttps.append(ttp.upper())
        elif isinstance(ttp, dict):
            tid = ttp.get("id", ttp.get("technique_id", ""))
            if tid:
                ttps.append(tid.upper())
    for t in cti_analysis.get("extracted_techniques", []):
        if isinstance(t, str) and t.upper() not in ttps:
            ttps.append(t.upper())
    return ttps


def outcome_from_pipeline_result(pr: Any, query: str) -> TurnOutcome:
    classification = getattr(pr, "classification", {}) or {}
    cti = getattr(pr, "cti_analysis", {}) or {}
    deception = getattr(pr, "deception_response", {}) or {}
    verification = getattr(pr, "verification", {}) or {}

    response_text = ""
    if hasattr(pr, "response_text"):
        response_text = pr.response_text
    elif isinstance(deception, dict):
        response_text = deception.get("response_text", "")

    ttps = _extract_ttps(cti)
    # Fail closed: an artifact without an explicit verdict is unverified. The
    # old default of True made a missing verifier indistinguishable from a
    # passing one in every benchmark aggregate.
    passed = verification.get("passed") is True if isinstance(verification, dict) else False
    is_error = bool(getattr(pr, "error", None))

    persona_name = ""
    if isinstance(deception, dict):
        persona_name = str(deception.get("persona_used", deception.get("persona", "")) or "")

    return TurnOutcome(
        query=query,
        response_text=response_text,
        classification=classification,
        cti_analysis=cti,
        deception=deception,
        verification=verification,
        total_time_ms=getattr(pr, "total_time_ms", 0.0),
        error=getattr(pr, "error", None),
        persona_name=persona_name,
        persona_matches=bool(persona_name and response_text),
        passed_verification=passed and not is_error,
        ttps_extracted=ttps,
        artifact_accessed=bool(cti.get("honeytoken_triggered", False)) if isinstance(cti, dict) else False,
        is_error=is_error,
    )


# ── Scorer delegation (echo guard lives in core.py) ──────────────────────
# The string scorers exist in core.py (legacy) and here (canonical for the
# live harness). Both now carry the query-echo guard from the 2026-09-28
# manual audit; keep this module delegating so there is ONE implementation.


def _score_technique_match(response: str, expected_technique: str, *, query: str | None = None) -> float:
    """Delegate to core.py so there is ONE scorer implementation (the echo
    guard lives there; the previous local copy is in git history)."""
    return _core_score_technique_match(response, expected_technique, query=query)


def _score_actor_match(response: str, expected_actor: str, sector: str, *, query: str | None = None) -> float:
    return _core_score_actor_match(response, expected_actor, sector, query=query)


# Bait-deployment recognition (see _score_persona_realism).
_BAIT_FLOOR = 0.85  # credential-bait stratum's deployment floor
_CRED_HUNT_RE = re.compile(
    r"\b(?:api[ _-]?keys?|tokens?|secrets?|credentials?|passwords?"
    r"|shadow|env(?:ironment)? variables?|authorized_keys)\b",
    re.I,
)
_KEY_SHAPED_RE = re.compile(r"\b[A-Za-z_]*(?:KEY|TOKEN|SECRET|PASSWD|PASSWORD)[A-Za-z_]*\s*=\s*\S+")


def _score_persona_realism(
    response: str,
    expected_traits: list[str],
    query: str = "",
) -> float:
    """Grade a persona response on authentic-technical realism.

    Rewards concrete signals a real (misconfigured but believable) system
    would emit — version numbers, IPs/ports, file paths, permission bits,
    command output — plus coverage of the query's expected traits. A response
    that merely echoes the user's query (template fallback) is penalized
    hard. Short generic refusals still earn a modest floor so a deliberate
    refusal persona is not zeroed out.
    """
    if not response:
        return 0.0
    rl = response.lower()

    # Template-fallback echo: the response is the raw query re-emitted as a
    # fake command → (no output) / command not found. Zero tolerable realism.
    if query:
        q = query.lower().strip(" .?!\n\t")
        if q and q in rl:
            fell_back = re.search(r"command not found|\(no output\)|not found\. Try", rl)
            if fell_back:
                return 0.0

    score = 0.0

    if re.search(r"\d+\.\d+(\.\d+)?", response):
        score += 0.15
    if re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", response):
        score += 0.15
    if re.search(r"\bport\s*\d+\b|\b:\d{2,5}\b|\bdpt:\d+|s\s*(LISTEN|ESTAB)", rl):
        score += 0.1
    if re.search(r"/usr/|/etc/|/var/|/opt/|/sbin|/bin|C:\\|\\Users|/proc/", response):
        score += 0.1
    if re.search(r"(drw|rwx|r-x|--x)", rl):
        score += 0.1
    # Unix prompt (user@host:~$, root~#) → believable interactive transcript.
    if re.search(r"\w+@[\w.-]+:[^#\n]*[#$](\s|$)", rl):
        score += 0.15
    # Table/structured command output (ps/top/ss/docker headers).
    if re.search(r"\b(PID|%CPU|%MEM|STAT|COMMAND|CONTAINER|Recv-Q|STATE|VSZ|RSS)\b", rl):
        score += 0.1
    # Metric values with units.
    if re.search(r"\b\d+(\.\d+)?\s?(KB|MB|GB|bytes|ms|MHz|Hz|%)\b", rl):
        score += 0.1

    detail_terms = [
        "server",
        "configured",
        "installed",
        "running",
        "service",
        "module",
        "version",
        "enabled",
        "listening",
        "daemon",
        "kernel",
        "interface",
        "rules",
        "policy",
        "socket",
        "daemon",
    ]
    matched = sum(1 for t in detail_terms if t in rl)
    detail_bonus = min(matched * 0.05, 0.25)

    # Realistic admin/audit commands executing (cf. template echo above).
    tool_names = [
        "iptables",
        "ufw",
        "nft",
        "systemctl",
        "ss",
        "netstat",
        "ps",
        "top",
        "free",
        "df",
        "mount",
        "dmesg",
        "auditctl",
        "getenforce",
        "sestatus",
        "sysctl",
        "crontab",
        "docker",
        "md5sum",
        "tcpdump",
        "vmstat",
        "ulimit",
        "lsof",
        "fdisk",
        "lsblk",
        "ip ",
        "cat /",
        "tail /",
        "find /",
    ]
    tools_hit = sum(1 for t in tool_names if t in rl)
    tool_bonus = min(tools_hit * 0.1, 0.25)
    score += max(detail_bonus, tool_bonus)

    if len(response) > 80:
        score += 0.1

    refusal = ["not authorized", "submit a ticket", "help desk", "cannot share", "restricted", "no permission"]
    if any(p in rl for p in refusal):
        if len(response) > 40:
            score += 0.3
    else:
        score -= 0.1 if len(response) < 20 else 0.0

    trait_signals = {
        "version": r"\d+\.\d+",
        "server": r"server",
        "port": r"\b\d{2,5}\b.*(LISTEN|tcp|udp)|dpt:\d+|\bport\b",
        "network": r"\d{1,3}(\.\d{1,3}){3}|\b(eth|wlan|inet|netmask|gateway)\b",
        "subnet": r"\d{1,3}(\.\d{1,3}){3}/\d+",
        "product": r"\b(nginx|apache|mysql|postgres|redis|openssl|ufw|iptables|clamav|docker)\b",
        "operating system": r"\b(ubuntu|linux|centos|debian|kernel|os-release)\b",
        "kernel": r"\d+\.\d+\.\d+.*\b(generic|server|lts)\b|\buname\b",
        "process": r"\bPID\b|\bCOMMAND\b|\bps aux|/usr/sbin/|\binit\b",
        "binary": r"/usr/|/sbin|/bin|\.[a-z0-9]+$",
        "user": r"\bpts/|\bttys|\bwtmp\b|\w+\s+pts/",
        "login": r"\bpts/|\b(login|logged|wtmp|last|chage)\b",
        "directory": r"\b(scripts|backup|web|app|static|/var/www)\b",
        "database": r"\b(mysql|postgres|redis|mariadb|mongodb|3306|5432|6379)\b",
        "connection": r"\b(LISTEN|ESTAB)|:\d{2,5}\b",
        "rule": r"\b(ACCEPT|DROP|REJECT|target|dpt:)\b",
        "CVE": r"\bCVE-\d{4}-\d+\b",
        "patch": r"\b(upgradable|upgrade|installed patches|USN-\d+)\b",
        "cron": r"\b(cron|crontab|scheduled|[*0-9] \* \* \* \*)\b",
    }
    trait_matches = 0
    for trait in expected_traits:
        t = trait.lower().strip()
        if not t:
            continue
        if t == "connection details":
            if re.search(r"\b(LISTEN|ESTAB)|:\d{2,5}\b", rl):
                trait_matches += 1
        elif t == "specific ports":
            if re.search(r"\bdpt:\d+|\bport\b|\b\d{2,5}\b", rl):
                trait_matches += 1
        else:
            pattern = next((sig for key, sig in trait_signals.items() if key in t), None)
            if pattern and re.search(pattern, rl):
                trait_matches += 1
    if expected_traits:
        score += min(trait_matches / len(expected_traits) * 0.3, 0.3)

    if re.search(r"\(no output\)|\{?\$?\{[^}]*\}?\}?\s*$|command not found", rl):
        score -= 0.2

    # Bait deployment: the verified loop cannot serve a real secret
    # (Property 1), so key-shaped assignments in the served transcript are
    # registered canaries by construction. Deploying bait on a
    # credential-hunt query is correct deception behavior — apply the
    # credential-bait floor AFTER penalties so the credit cannot be dragged
    # below the floor by concision artifacts.
    if query and _CRED_HUNT_RE.search(query) and _KEY_SHAPED_RE.search(response):
        score = max(score, _BAIT_FLOOR)

    return max(min(score, 1.0), 0.0)


def _cti_analysis_text(cti: dict[str, Any]) -> str:
    """Flatten Don's CTI analysis into a scoreable narrative.

    The CTI suites measure whether the pipeline *identified* the expected
    technique/actor — that signal lives in Don's threat analysis, not the
    (intentionally technique-free) deception shell output.
    """
    if not cti:
        return ""
    parts: list[str] = []
    for key in ("threat_summary", "summary", "analysis", "narrative"):
        val = cti.get(key)
        if isinstance(val, str) and val:
            parts.append(val)
    for tactic in cti.get("tactics", []):
        if isinstance(tactic, dict):
            if tactic.get("id"):
                parts.append(tactic["id"])
            if tactic.get("name"):
                parts.append(tactic["name"])
    for actor in cti.get("candidate_actors", []):
        if isinstance(actor, dict):
            if actor.get("name"):
                parts.append(actor["name"])
            for ttp in actor.get("known_ttps", []):
                if isinstance(ttp, str):
                    parts.append(ttp)
    for ttp in cti.get("extracted_techniques", []):
        if isinstance(ttp, str):
            parts.append(ttp)
    for ttp in cti.get("ttps_seen", []):
        if isinstance(ttp, str):
            parts.append(ttp)
    return " ".join(p for p in parts if p)


@dataclass
class LiveBenchmarkResult:
    technique_results: list[BenchmarkResult] = field(default_factory=list)
    actor_results: list[BenchmarkResult] = field(default_factory=list)
    persona_results: list[BenchmarkResult] = field(default_factory=list)
    all_outcomes: list[TurnOutcome] = field(default_factory=list)
    metrics: EffectivenessMetrics = field(default_factory=EffectivenessMetrics)
    multi_turn_summary: SessionTTPSummary | None = None
    elapsed_s: float = 0.0

    @property
    def technique_report(self):
        return generate_report(self.technique_results, "cti_technique")

    @property
    def actor_report(self):
        return generate_report(self.actor_results, "cti_actor")

    @property
    def persona_report(self):
        return generate_report(self.persona_results, "deception")


def run_live_benchmark(
    harness: Any,
    session_factory: Callable,
    *,
    suites: tuple[str, ...] = ("cti_technique", "cti_actor", "deception"),
    limit: int | None = None,
    voter: VotingSystem | None = None,
) -> LiveBenchmarkResult:
    t_start = time.monotonic()

    tech_queries = CTI_TECHNIQUE_QUERIES[:limit] if limit else CTI_TECHNIQUE_QUERIES
    actor_queries = CTI_ACTOR_QUERIES[:limit] if limit else CTI_ACTOR_QUERIES
    persona_queries = PERSONA_REALISM_QUERIES[:limit] if limit else PERSONA_REALISM_QUERIES

    result = LiveBenchmarkResult()
    tracker = MultiTurnTracker(session_id="benchmark_live")

    def _process_one(qa, suite_name, score_fn, extra_fn):
        query = qa["query"]
        session = session_factory()
        t0 = time.monotonic()
        try:
            if hasattr(harness, "process_with_threat_modeling"):
                pr = harness.process_with_threat_modeling(session, query)
            else:
                pr = harness.process(session, query)
            latency = (time.monotonic() - t0) * 1000
            outcome = outcome_from_pipeline_result(pr, query)
            if voter and outcome.response_text:
                context = {
                    "session_id": getattr(session, "session_id", "benchmark"),
                    "query": query,
                    "classification": outcome.classification,
                    "cti_analysis": outcome.cti_analysis,
                }
                response_dict = {"response_text": outcome.response_text, **outcome.deception}
                vote_result = voter.vote(response_dict, context)
                outcome.passed_verification = vote_result.outcome == "PASSED"
            if extra_fn:
                extra_fn(outcome, qa)
            score = score_fn(outcome, qa)
            # Direct serve-path provenance: the graph loop stamps serve_path on
            # the deception response; carry it into the persisted result row so
            # the provenance split is an exact count (no latency inference).
            deception = outcome.deception if isinstance(outcome.deception, dict) else {}
            serve_path = deception.get("serve_path", "")
            return (
                BenchmarkResult(
                    name=f"{suite_name}_{query[:40].replace(' ', '_')}",
                    suite=suite_name,
                    passed=score >= 0.3,
                    score=score,
                    latency_ms=latency,
                    serve_path=serve_path,
                    details={"query": query, "response_preview": outcome.response_text[:200], "response_full": outcome.response_text},
                ),
                outcome,
                query,
            )
        except Exception as exc:
            latency = (time.monotonic() - t0) * 1000
            return (
                BenchmarkResult(
                    name=f"{suite_name}_{query[:40].replace(' ', '_')}",
                    suite=suite_name,
                    passed=False,
                    score=0.0,
                    latency_ms=latency,
                    error=str(exc),
                    details={"query": query},
                ),
                None,
                query,
            )

    def _run_suite(queries, suite_name, score_fn, result_list, extra_fn=None):
        turn_num = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(_process_one, qa, suite_name, score_fn, extra_fn): qa for qa in queries}
            for future in as_completed(futures):
                res, outcome, query = future.result()
                result_list.append(res)
                result.all_outcomes.append(outcome) if outcome else None
                turn_num += 1
                if outcome:
                    classification = outcome.classification if isinstance(outcome.classification, dict) else {}
                    tracker.record_turn(
                        turn=turn_num,
                        ttps=set(outcome.ttps_extracted),
                        severity=classification.get("risk_level", "info"),
                        attacker_input=query,
                        artifacts_accessed=outcome.artifact_accessed,
                    )

    def _tech_score(outcome, qa):
        # Declared channel: BOTH, max()ed — this is the run_live_benchmark
        # convention (Sep-22 reference campaign). The served-text-only
        # channel lives in the external-baseline arms' scorers.
        analysis_text = _cti_analysis_text(outcome.cti_analysis)
        text_score = _score_technique_match(
            analysis_text or outcome.response_text, qa["expected_technique"], query=qa.get("query")
        )
        expected = qa["expected_technique"].upper()
        extracted = {t.upper() for t in outcome.ttps_extracted}
        if expected in extracted:
            ttp_bonus = 1.0
        elif expected.split(".")[0] in extracted or any(
            exp_p == expected.split(".")[0] for exp_p in (e.split(".")[0] for e in extracted)
        ):
            ttp_bonus = 0.85
        else:
            ttp_bonus = 0.0
        return min(max(text_score, ttp_bonus), 1.0)

    def _tech_extra(outcome, qa):
        outcome.technique_mentioned = qa["expected_technique"]

    def _actor_score(outcome, qa):
        analysis_text = _cti_analysis_text(outcome.cti_analysis)
        text_score = _score_actor_match(
            analysis_text or outcome.response_text, qa["expected_actor"], qa.get("sector", ""), query=qa.get("query")
        )
        expected = qa["expected_actor"].lower()
        named = {
            a.get("name", "").lower()
            for a in (outcome.cti_analysis or {}).get("candidate_actors", [])
            if isinstance(a, dict)
        }
        if any(expected == n or expected in n or n in expected for n in named):
            text_score = max(text_score, 0.85)
        return min(text_score, 1.0)

    def _actor_extra(outcome, qa):
        outcome.actor_mentioned = qa["expected_actor"]

    def _persona_score(outcome, qa):
        return _score_persona_realism(outcome.response_text, qa.get("expected_traits", []), qa.get("query", ""))

    # Crash-guard: expose per-suite progress so callers can persist partial
    # results if the run dies mid-way (quota exhaustion, network failure).
    # Updated after each suite; run_live_benchmark.py reads it in its abort path.
    # Stored as a function attribute; typed via the declaration below.
    last_partial: dict[str, Any] = {
        "elapsed_s": 0.0,
        "metrics": {},
        "technique_results": list(result.technique_results),
        "actor_results": list(result.actor_results),
        "persona_results": list(result.persona_results),
    }
    run_live_benchmark.last_partial = last_partial  # type: ignore[attr-defined]

    if "cti_technique" in suites:
        _run_suite(tech_queries, "cti_technique", _tech_score, result.technique_results, _tech_extra)
        last_partial["technique_results"] = list(result.technique_results)
        run_live_benchmark.last_partial = last_partial  # type: ignore[attr-defined]
    if "cti_actor" in suites:
        _run_suite(actor_queries, "cti_actor", _actor_score, result.actor_results, _actor_extra)
        last_partial["actor_results"] = list(result.actor_results)
        run_live_benchmark.last_partial = last_partial  # type: ignore[attr-defined]
    if "deception" in suites:
        _run_suite(persona_queries, "deception", _persona_score, result.persona_results)
        last_partial["persona_results"] = list(result.persona_results)
        run_live_benchmark.last_partial = last_partial  # type: ignore[attr-defined]

    # ── Aggregate into EffectivenessMetrics ───────────────────────────────
    all_outcomes = result.all_outcomes
    total = len(all_outcomes)
    errors = sum(1 for o in all_outcomes if o.is_error)
    successes = total - errors

    artifacts_deployed = max(successes, 1)
    artifacts_accessed = sum(1 for o in all_outcomes if o.artifact_accessed)
    engaged = sum(1 for o in all_outcomes if len(o.response_text) > 20)
    persona_correct = sum(1 for o in all_outcomes if o.persona_name)

    all_ttps: set[str] = set()
    for o in all_outcomes:
        all_ttps.update(o.ttps_extracted)

    tp = sum(1 for o in all_outcomes if o.ttps_extracted)
    avg_time = sum(o.total_time_ms for o in all_outcomes) / total if total else 0.0
    personas_used = set(o.persona_name for o in all_outcomes if o.persona_name)

    result.metrics = EffectivenessMetrics(
        honeytoken_triggers=artifacts_accessed,
        honeytokens_deployed=artifacts_deployed,
        total_sessions=total,
        sessions_with_engagement=engaged,
        persona_correct_assignments=persona_correct,
        persona_total_assignments=total,
        ttps_detected=tp,
        ttps_detected_unique=len(all_ttps),
        cti_alerts_generated=tp,
        false_positives=0,
        true_positives=tp,
        attacker_retention_turns=float(engaged) / total if total else 0.0,
        max_retention_turns=total,
        mean_session_duration_s=avg_time / 1000.0 if avg_time else 0.0,
        deception_artifacts_deployed=artifacts_deployed,
        deception_artifacts_accessed=artifacts_accessed,
        strategy_adaptations=len(personas_used),
        avg_response_time_ms=avg_time,
    )

    result.elapsed_s = time.monotonic() - t_start
    result.multi_turn_summary = tracker.get_summary()
    return result

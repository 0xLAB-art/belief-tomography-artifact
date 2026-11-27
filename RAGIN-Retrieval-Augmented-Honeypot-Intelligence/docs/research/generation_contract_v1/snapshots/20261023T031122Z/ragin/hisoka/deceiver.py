"""Adaptive deceiver — orchestrates persona selection and response generation."""

from __future__ import annotations

import logging
import re as _re
from collections import defaultdict
from typing import Any

from ragin.decision_fusion_v4.benchmark import ALLOWED_STRATEGIES
from ragin.hisoka.deception import (
    _CANARY_AWS_ACCESS_KEY,
    _CANARY_AWS_SECRET,
    _CANARY_DB_PASSWORD,
    _CANARY_MYSQL_HASHES,
    _CANARY_SHADOW_HASHES,
    _IMDS_ACCESS_KEY,
    _IMDS_SECRET_KEY,
    ArtifactInjector,
    EngagementTracker,
    PersonaManager,
    ResponseGenerator,
    _bait_text_for,
    _imds_followthrough_text,
    _imds_response_for,
    _jev_signal_from_context,
    _reverse_shell_bait_text,
    _sqli_bait_text,
    _ssh_protocol_text_for,
    _strategy_transcript_suffix,
    _sudo_text_for,
    authorization_fact,
    identity_for,
    identity_for_scenario,
    jev_kind_strategy,
    lateral_bait_facts,
    looks_cloud_shaped,
)
from ragin.hisoka.fs_ledger import FilesystemLedger
from ragin.hisoka.honeytokens import HoneytokenConfig, HoneytokenEngine
from ragin.hisoka.memory import HisokaMemory
from ragin.hisoka.models import DeceptionResponse, Persona
from ragin.utils import CircuitBreaker, CostTracker, PromptTokenLimiter, _redact_pii

logger = logging.getLogger(__name__)

_V4_ARMS = {"RAGIN_V4_DETERMINISTIC", "RAGIN_V4_LOGISTIC"}
V4_GENERATOR_INTEGRATION_VERSION = "V4_GENERATOR_STRATEGY_WIRING_FIX_V1"


def _v4_generation_strategy(session_context: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    decision = session_context.get("policy_decision")
    if not isinstance(decision, dict) or decision.get("arm") not in _V4_ARMS:
        return None, None, None
    selected = decision.get("selected_response_strategy")
    if selected not in ALLOWED_STRATEGIES:
        return "baseline", "v4_policy_decision_fallback", "unsupported_strategy"
    return str(selected), "v4_policy_decision", str(decision.get("fallback_reason") or "") or None


def _imds_text_for(command: str) -> str | None:
    """Return the deterministic IMDS body for a metadata request, else None.

    Wraps :func:`_imds_response_for`: extracts the URL path from commands like
    ``curl http://169.254.169.254/latest/meta-data/iam/security-credentials/``
    and returns the protocol-complete fake response.
    """
    if "169.254.169.254" not in (command or ""):
        return None
    m = _imds_path_re.search(command)
    if not m:
        return None
    return _imds_response_for(m.group(1))


_imds_path_re = _re.compile(r"169\.254\.169\.254(/[^\s\"']*)?", _re.IGNORECASE)

# Canary-bound protocol credentials: the deterministic IMDS fake keypair is
# registered as a honeytoken on first fetch, so any later re-presentation of
# the values (exfil loop: fetch → exfil → try elsewhere) trips an alert.


class AdaptiveDeceiver:
    """Top-level deception orchestrator.

    Receives attacker input and Don analysis, selects the appropriate persona,
    generates deceptive responses, and tracks engagement.

    Optionally uses :class:`HisokaMemory` to enrich prompts with
    cross-session attacker history for more convincing deception.
    """

    def __init__(
        self,
        gateway_url: str | None = None,
        config: dict[str, Any] | None = None,
        memory: HisokaMemory | None = None,
        api_key: str | None = None,
    ) -> None:
        self._persona_manager = PersonaManager()
        self._response_generator = ResponseGenerator(gateway_url=gateway_url, api_key=api_key)
        self._engagement_tracker = EngagementTracker()
        self._artifact_injector = ArtifactInjector()
        self._config = config or {}
        self._memory = memory

        # Per-session honeytoken engines — each session gets its own
        # token namespace so triggers don't cross-contaminate.
        self._honeytoken_engines: dict[str, HoneytokenEngine] = {}
        self._honeytoken_alerts: dict[str, list] = defaultdict(list)
        # Sessions whose canary set is fully armed (see _ensure_canaries_armed).
        self._canaries_armed: set[str] = set()

        # Per-session filesystem fiction ledgers: repeated reads replay
        # byte-identical output; mutations invalidate touched paths.
        self._fs_ledgers: dict[str, FilesystemLedger] = {}

        # Per-session scenario identity (frozen at first contact): a
        # cloud-shaped opener flips the identity to cloud-VM naming so IMDS
        # probes never contradict the pinned hostname/domain.
        self._session_identity: dict[str, dict[str, str]] = {}

        # Production infrastructure
        self._circuit_breaker = CircuitBreaker(threshold=5, timeout_s=60.0)
        self._cost_tracker = CostTracker(daily_budget_usd=20.0, monthly_budget_usd=2000.0, per_request_budget_usd=0.10)
        self._prompt_limiter = PromptTokenLimiter(max_prompt_tokens=32_000)

    def _ensure_canaries_armed(self, session_id: str, ht_engine: HoneytokenEngine) -> None:
        """Register the session's canary secrets exactly once, before any reveal.

        Arms ALL canary families (bait credentials + IMDS keypair) regardless
        of which deterministic path fires first — value-based matching means
        ANY later path that surfaces a registered value is tripwired, so a
        session opening on IMDS still catches a later .dbpass re-presentation
        (and vice versa). Without the cross-arming, an IMDS-first session
        silently skipped bait canary registration (deployed_count > 0).
        """
        if session_id in self._canaries_armed:
            return
        ht_engine.register_canary_credential("svc_backup", _CANARY_DB_PASSWORD, match_values=[_CANARY_DB_PASSWORD])
        ht_engine.register_canary_credential(
            _CANARY_AWS_ACCESS_KEY,
            _CANARY_AWS_SECRET,
            match_values=[_CANARY_AWS_ACCESS_KEY, _CANARY_AWS_SECRET],
        )
        ht_engine.register_canary_credential(
            _IMDS_ACCESS_KEY,
            _IMDS_SECRET_KEY,
            match_values=[_IMDS_ACCESS_KEY, _IMDS_SECRET_KEY],
        )
        # Hash canaries: the shadow dump (GT-008) and mysql.user table (GT-005)
        # reveal crackable-hash fictions. Registering them makes the full
        # dump→crack→replay loop an alert, not just the plaintext loop.
        for acct, shadow_hash, mysql_hash in zip(
            ("webapp", "svc_backup", "deploy"), _CANARY_SHADOW_HASHES, _CANARY_MYSQL_HASHES, strict=True
        ):
            ht_engine.register_canary_credential(acct, shadow_hash, match_values=[shadow_hash, mysql_hash])
        self._canaries_armed.add(session_id)

    def _session_ht_alerts(self, session_id: str, attacker_input: str) -> tuple[HoneytokenEngine, list]:
        """Engine-or-create, arm canaries, scan attacker input for canary use.

        EVERY response path must call this before returning: the fast-paths
        return early, so only a scan at each return site catches an attacker
        re-presenting a served canary (the ssh/sudo paths previously returned
        hard-coded False and silently missed the exfil loop).
        """
        ht_engine = self._honeytoken_engines.get(session_id)
        if ht_engine is None:
            ht_engine = HoneytokenEngine(HoneytokenConfig(session_id=session_id))
            self._honeytoken_engines[session_id] = ht_engine
        self._ensure_canaries_armed(session_id, ht_engine)
        ht_alerts = ht_engine.check_triggers({"input": attacker_input})
        self._honeytoken_alerts[session_id].extend(ht_alerts)
        return ht_engine, ht_alerts

    def generate_response(
        self,
        attacker_input: str,
        session_context: dict[str, Any],
    ) -> DeceptionResponse:
        """Generate a full deception response for an attacker interaction.

        Applies PII redaction on attacker input before LLM calls, enforces
        budget and circuit breaker, and tracks costs from gateway responses.

        If ``session_context`` contains an ``attacker_history`` key (populated
        by the pipeline from Mem0 search results), it is injected into the
        prompt for continuity-aware deception.
        """
        session_id = session_context.get("session_id", "unknown")
        classification = session_context.get("classification", {})
        skill_level = classification.get("skill_level", session_context.get("skill_level", "novice"))

        self._persona_manager.select(skill_level)
        self._engagement_tracker.record_command(session_id)

        # Jev attack-kind-aware strategy (additive): when a Jev System One
        # assessment accompanies the session, steer the deception toward the
        # kind-specific engagement objective. Persona stays skill-matched;
        # only the prompt guidance and response metadata change.
        jev_signal = _jev_signal_from_context(session_context)
        kind_strategy = jev_kind_strategy(jev_signal["attack_kind"]) if jev_signal["available"] else None
        if jev_signal["source"] == "laya" and kind_strategy is None and jev_signal["response_strategy"]:
            kind_strategy = {
                "objective": jev_signal["response_strategy"],
                "guidance": (
                    "The attack stage is uncertain. Keep the response believable, "
                    "bounded by the pinned fiction, and fully instrumented."
                ),
            }
        v4_strategy, v4_source, v4_fallback_reason = _v4_generation_strategy(session_context)
        effective_strategy = v4_strategy if v4_strategy is not None else jev_signal["response_strategy"]
        strategy_suffix = _strategy_transcript_suffix(effective_strategy)

        def v4_trace(template_id: str) -> dict[str, Any]:
            if not v4_source:
                return {}
            return {
                "selected_strategy": effective_strategy,
                "strategy_source": v4_source,
                "generator_integration_version": V4_GENERATOR_INTEGRATION_VERSION,
                "strategy_delivered_to_generator": False,
                "strategy_consumed_by_template": bool(v4_strategy and strategy_suffix),
                "template_id": template_id,
                "template_fallback_reason": "fastpath",
                **({"policy_fallback_reason": v4_fallback_reason} if v4_fallback_reason else {}),
            }

        jev_metadata: dict[str, Any] = {}
        if jev_signal["available"]:
            jev_metadata = {
                "decision_source": jev_signal["source"],
                "jev_attack_kind": jev_signal["attack_kind"],
                "jev_severity": jev_signal["severity"],
                "jev_attack_probability": jev_signal["attack_probability"],
                "jev_objective": (kind_strategy["objective"] if kind_strategy else None),
            }
            if jev_signal["source"] == "laya":
                jev_metadata.update(
                    {
                        "laya_attack_kind": jev_signal["attack_kind"],
                        "laya_severity": jev_signal["severity"],
                        "laya_attack_probability": jev_signal["attack_probability"],
                        "laya_response_strategy": jev_signal["response_strategy"],
                    }
                )

        # PII redact attacker input before it reaches the LLM
        redacted_input = _redact_pii(attacker_input)

        # --- Filesystem fiction ledger (consistency layer) ---------------
        # A repeated read must show the attacker the SAME bytes as before:
        # inconsistent listings were the dominant trap-signal in the dwell
        # replay A/B. Mutating commands invalidate touched paths instead.
        ledger = self._fs_ledgers.get(session_id)
        if ledger is None:
            ledger = FilesystemLedger(session_id=session_id)
            # Scenario decision is FROZEN at first contact: a cloud-shaped
            # opener (IMDS probe, compute.internal naming) upgrades the
            # identity to cloud-VM shape; everything else stays corp-local.
            # Flipping mid-session would contradict earlier answers.
            cloud = bool(session_context.get("scenario") == "cloud" or looks_cloud_shaped(redacted_input))
            # Host-fiction binding: when the pipeline pins a host identity
            # (ctx host_identity from HostFictionStore), every session drafts
            # on THAT machine — a reclassified row must not name a different
            # host while verification enforces the pinned one. Cloud-shaped
            # inputs keep their cloud override EXCEPT the host/domain fields,
            # which stay pinned (the facing machine cannot change).
            pinned = session_context.get("host_identity") or None
            ident = identity_for_scenario(skill_level, cloud)
            if pinned:
                for k, v in pinned.items():
                    if k in ("host", "domain", "prompt", "ip") and v:
                        ident[k] = v
            self._session_identity[session_id] = ident
            # Seed with the pinned identity so identity answers can never
            # contradict across turns (v2 leave reason: identity
            # inconsistency between whoami/id and earlier/later replies).
            ledger.note_fact(f"user is {ident.get('user', 'webapp')}")
            ledger.note_fact(f"hostname is {ident.get('host', 'web-srv-01')}")
            ledger.note_fact(f"domain is {ident.get('domain', 'corp.local')}")
            ledger.note_fact(f"os is {ident.get('distro', 'Ubuntu 22.04')}")
            ledger.note_fact(f"kernel is {ident.get('kernel', '')}")
            # Authorization policy: pinned ONCE so the sudo fiction can never
            # drift from the deterministic id/groups/sudoers answers (v5.5
            # leave reason: id showed 27(sudo) while sudo granted nothing).
            ledger.note_fact(authorization_fact())
            if cloud:
                ledger.note_fact(
                    "scenario is an AWS EC2 VM: instance metadata service at "
                    "169.254.169.254, IAM role webapp-runtime, hostname ip-10-0-4-7"
                )
            self._fs_ledgers[session_id] = ledger
        ident = self._session_identity.get(session_id, identity_for(skill_level))
        for fact in session_context.get("fs_facts") or []:
            ledger.note_fact(str(fact))
        # Lateral kind: seed decoy-topology bait ONCE so the fiction actually
        # contains the internal hosts/creds the Jev guidance promises
        # (v3 leave reason: "only redactions, no actionable intel").
        if (
            jev_signal["available"]
            and jev_signal["attack_kind"] == "lateral"
            and ledger.summary()["mutations"] == 0
            and ledger.summary()["remembered_reads"] == 0
        ):
            for bait in lateral_bait_facts():
                ledger.note_fact(bait)

        # --- Chained bait transcripts (IMDS follow-through / reverse shell /
        # SQLi REPL) -----------------------------------------------
        # Thin-but-protocol-correct answers (bare metadata index, a bare
        # listener line, 'command not found') become the attacker's full
        # follow-through fiction, chained to the canary credential reveals.
        # Must run BEFORE the IMDS fast-path: the bare index fetch composes
        # into the full chain instead of the 7-line index body. sudo-prefixed
        # input keeps the authorization fast-path as the fiction authority.
        chained_text = None
        if not attacker_input.lower().lstrip().startswith("sudo "):
            chained_text = (
                _imds_followthrough_text(attacker_input, ident)
                or _reverse_shell_bait_text(attacker_input, ident)
                or _sqli_bait_text(attacker_input, ident)
            )
        if chained_text is not None:
            self._engagement_tracker.record_command(session_id)
            if ledger.is_read_command(attacker_input):
                ledger.remember(attacker_input, chained_text)
            _ht, ht_alerts = self._session_ht_alerts(session_id, attacker_input)
            return DeceptionResponse(
                session_id=session_id,
                response_text=chained_text + strategy_suffix,
                persona_used=skill_level,
                artifacts_injected=["credential_canary"],
                engagement_score=self._engagement_tracker.get_score(session_id),
                honeytoken_triggered=len(ht_alerts) > 0,
                metadata={"chained_bait": True, **jev_metadata, **v4_trace("chained_bait")},
            )

        # --- Protocol-shaped deterministic responses (IMDS / SSH keys) ----
        # IMDS replies must be protocol-COMPLETE (a masked credential body is
        # itself a tell), and ssh-keyscan/first-connect transcripts must carry
        # per-host keys whose fingerprint matches across keyscan and banner —
        # both are answered deterministically: no LLM variance, replayable.
        # NOTE: the RAW command (not PII-redacted) drives these paths — the
        # attacker's own target IP is part of the fiction, and redacting it
        # would corrupt the deterministic extraction (PII redaction matters
        # for what we SEND to the LLM, not for protocol parsing).
        imds_text = _imds_text_for(attacker_input)
        ssh_text = _ssh_protocol_text_for(attacker_input)
        if imds_text is not None:
            self._engagement_tracker.record_command(session_id)
            # Canary-bound credentials: the deterministic fake keypair doubles
            # as a honeytoken — its later use anywhere is a high-signal alert
            # (exfil loop: they fetched, exfiltrated, came back with it).
            _ht, ht_alerts = self._session_ht_alerts(session_id, attacker_input)
            return DeceptionResponse(
                session_id=session_id,
                response_text=imds_text + strategy_suffix,
                persona_used=skill_level,
                artifacts_injected=[],
                engagement_score=self._engagement_tracker.get_score(session_id),
                honeytoken_triggered=len(ht_alerts) > 0,
                metadata={"imds_protocol": True, **jev_metadata, **v4_trace("imds_protocol")},
            )

        if ssh_text is not None:
            self._engagement_tracker.record_command(session_id)
            if ledger.is_read_command(attacker_input):
                ledger.remember(attacker_input, ssh_text)
            # An attacker replaying a served canary inside an ssh invocation
            # (keyfile, password prompt, or comment) is the exfil loop too.
            _ht, ht_alerts = self._session_ht_alerts(session_id, attacker_input)
            return DeceptionResponse(
                session_id=session_id,
                response_text=ssh_text + strategy_suffix,
                persona_used=skill_level,
                artifacts_injected=[],
                engagement_score=self._engagement_tracker.get_score(session_id),
                honeytoken_triggered=len(ht_alerts) > 0,
                metadata={"ssh_protocol": True, **jev_metadata, **v4_trace("ssh_protocol")},
            )

        # --- Deterministic authorization fast-path (sudo / id / groups) -----
        # Sudo simulation is pinned to the authorization policy BEFORE the
        # LLM: whitelisted monitoring commands flow through (templates/LLM
        # render success), everything else gets the locked-password fail
        # loop. The most identity-revealing command family can therefore
        # never drift from the pinned fiction (v5.5 leave reason: `id`
        # showed 27(sudo) while sudo granted nothing).
        sudo_text = _sudo_text_for(attacker_input, ident)
        if sudo_text is not None:
            self._engagement_tracker.record_command(session_id)
            if ledger.is_read_command(attacker_input):
                ledger.remember(attacker_input, sudo_text)
            # Canary replay inside a sudo command line (e.g. reusing a
            # harvested password for `sudo -S`) is an exfil-loop signal.
            _ht, ht_alerts = self._session_ht_alerts(session_id, attacker_input)
            return DeceptionResponse(
                session_id=session_id,
                response_text=sudo_text + strategy_suffix,
                persona_used=skill_level,
                artifacts_injected=[],
                engagement_score=self._engagement_tracker.get_score(session_id),
                honeytoken_triggered=len(ht_alerts) > 0,
                metadata={"authorization_protocol": True, **jev_metadata, **v4_trace("authorization_protocol")},
            )

        # --- Credential-bait fast-path (honeytoken honeypots) --------------
        # Credential-hunt asks (database credentials, shadow dumps, privilege
        # escalation) are the exact requests free-tier LLMs refuse — and the
        # exact scenarios where the eval expects "deploy fake credentials as
        # a honeytoken while stalling". They are answered deterministically
        # with registered canary secrets: protocol-level honeytokens whose
        # re-presentation anywhere trips the session honeytoken engine.
        bait_text = _bait_text_for(attacker_input, ident)
        if bait_text is not None:
            self._engagement_tracker.record_command(session_id)
            if ledger.is_read_command(attacker_input):
                ledger.remember(attacker_input, bait_text)
            _ht, ht_alerts = self._session_ht_alerts(session_id, attacker_input)
            return DeceptionResponse(
                session_id=session_id,
                response_text=bait_text + strategy_suffix,
                persona_used=skill_level,
                artifacts_injected=["credential_canary"],
                engagement_score=self._engagement_tracker.get_score(session_id),
                honeytoken_triggered=len(ht_alerts) > 0,
                metadata={"credential_bait": True, **jev_metadata, **v4_trace("credential_bait")},
            )

        replay_text = ledger.replay_for(redacted_input)
        if replay_text is not None:
            self._engagement_tracker.record_command(session_id)
            # Ambient dynamism: an exact repeat of a tmp-path read within a
            # NEW time bucket evolves by a few transient entries instead of
            # returning byte-identical output forever (v5 tell: listings
            # that never change read as "canned/scripted shell"). Base
            # entries are preserved and same-bucket repeats stay stable.
            if FilesystemLedger.is_ambient_target(redacted_input):
                import time as _time

                replay_text = ledger.ambient_rewrite(redacted_input, replay_text, _time.time())
            _ht, ht_alerts = self._session_ht_alerts(session_id, attacker_input)
            return DeceptionResponse(
                session_id=session_id,
                response_text=replay_text + strategy_suffix,
                persona_used=skill_level,
                artifacts_injected=[],
                engagement_score=self._engagement_tracker.get_score(session_id),
                honeytoken_triggered=len(ht_alerts) > 0,
                metadata={"fs_replay": True, **jev_metadata, **v4_trace("filesystem_replay")},
            )

        # Budget enforcement. Every deterministic path below records itself in
        # gen_meta so the serve path can label the turn TEMPLATE_FALLBACK
        # instead of mistaking it for a verified LLM draft.
        gen_meta: dict[str, Any] = {}
        if not self._cost_tracker.check_budget("hisoka"):
            logger.warning("Hisoka budget exhausted — returning static deception")
            fallback_resp = self._static_fallback(skill_level, redacted_input)
            response_text = fallback_resp.response_text
            gen_meta["static_fallback"] = True
        elif not self._circuit_breaker.allow():
            logger.warning("Hisoka circuit breaker open — static fallback")
            fallback_resp = self._static_fallback(skill_level, redacted_input)
            response_text = fallback_resp.response_text
            gen_meta["static_fallback"] = True
        else:
            # Build prompt — context sections first, then the current command.
            sections: list[str] = []
            if session_context.get("context"):
                sections.append(session_context["context"])

            attacker_history = session_context.get("attacker_history")
            if attacker_history:
                history_block = "\n".join(f"  - {h}" for h in attacker_history[:5])
                sections.append(f"Known attacker history:\n{history_block}")

            # Graph-engineering context: authoritative session facts and the
            # MITRE-steering engagement strategy are fed in as system context so
            # the response stays consistent with the fiction graph and seeded bait.
            for key, label in (
                ("fiction_block", "Session consistency (authoritative)"),
                ("strategy_block", "Engagement strategy"),
            ):
                block = session_context.get(key)
                if block:
                    sections.append(f"{label}:\n{block.rstrip()}")

            # Frozen filesystem facts from the ledger — identical every turn
            # so LLM regeneration anchors on the same fiction.
            ledger_block = ledger.fact_block()
            if ledger_block:
                sections.append(ledger_block.rstrip())

            # Behavioral decision guidance: prepend so the LLM weighs the
            # bounded decision signal alongside persona fiction.
            if kind_strategy:
                source_label = "Laya decision model" if jev_signal["source"] == "laya" else "Jev System One"
                severity = jev_signal["severity"]
                severity_text = "unknown" if severity is None else f"{severity:.2f}"
                sections.append(
                    f"Behavioral analysis ({source_label}): the attacker's "
                    f"behavior classifies as '{jev_signal['attack_kind']}' "
                    f"(severity {severity_text}/3). "
                    f"Engagement objective: {kind_strategy['objective']}. "
                    f"{kind_strategy['guidance']}"
                )

            # Verification-feedback loop (C2): when the verifier rejected the
            # previous attempt, surface its issues so the model corrects them.
            feedback = session_context.get("feedback")
            if feedback:
                sections.append(
                    "VERIFICATION FEEDBACK (your previous reply was REJECTED — fix it):\n"
                    f"  {feedback}\n"
                    "  Regenerate the output with these issues corrected. Raw output only."
                )

            prompt_text = "\n\n".join(sections)
            prompt_text = f"{prompt_text}\n\nCurrent command: {redacted_input}" if prompt_text else redacted_input

            # Prompt token limit check
            if not self._prompt_limiter.check(prompt_text):
                prompt_text = self._prompt_limiter.truncate(prompt_text)
                logger.warning("Hisoka prompt truncated to fit token budget")

            # Provenance meta: the generator marks deterministic fallbacks
            # (gateway failure, unsafe retry, template anchoring) so the serve
            # path can distinguish a real LLM draft from a template (2026-09-28
            # audit: outage templates were stamped GENERATED_VERIFIED).
            response_text = self._response_generator.generate(
                skill_level=skill_level,
                user_input=redacted_input,
                context=prompt_text,
                identity=ident,
                meta=gen_meta,
                response_strategy=effective_strategy,
            )
            if v4_source:
                gen_meta.update(
                    {
                        "selected_strategy": effective_strategy,
                        "strategy_source": v4_source,
                        "generator_integration_version": V4_GENERATOR_INTEGRATION_VERSION,
                        "strategy_delivered_to_generator": True,
                        "strategy_consumed_by_template": bool(gen_meta.get("strategy_consumed_by_template", False)),
                        "template_fallback_reason": gen_meta.get("template_fallback_reason"),
                    }
                )
                if v4_fallback_reason:
                    gen_meta["policy_fallback_reason"] = v4_fallback_reason

            # Track cost — we don't have usage from the response generator
            # so we estimate from the response length
            estimated_tokens = max(1, len(response_text) // 4)
            self._cost_tracker.record(
                "hisoka",
                "glm-5.3-flash-free",
                {"prompt_tokens": len(prompt_text) // 4, "completion_tokens": estimated_tokens},
            )
            self._circuit_breaker.record_success()

        # Ledger bookkeeping: mutations invalidate touched paths; reads are
        # remembered verbatim so an exact repeat replays byte-identically.
        if ledger.is_mutating_command(redacted_input):
            ledger.invalidate(redacted_input)
        else:
            import time as _time

            ledger.remember(redacted_input, response_text, now=_time.time())

        # Inject artifacts for higher skill levels
        artifacts = []
        if skill_level in ("intermediate", "expert", "apt"):
            self._artifact_injector.inject("fake_config", skill_level=skill_level)
            artifacts.append("fake_config")

        # --- Honeytokens -------------------------------------------------
        # Engine-or-create + canary arming + exfil-loop scan (one helper so
        # every path — fast-path or generic — gets identical tripwire logic).
        ht_engine, ht_alerts = self._session_ht_alerts(session_id, attacker_input)
        honeytoken_triggered = len(ht_alerts) > 0

        # 3) Inject fresh tokens into the outgoing response
        if not honeytoken_triggered:
            # Only plant new tokens when the attacker hasn't triggered
            # existing ones — avoids over-planting.
            ht_engine.inject(response_text, context=skill_level)

        engagement = self._engagement_tracker.get_score(session_id)

        return DeceptionResponse(
            session_id=session_id,
            response_text=response_text,
            persona_used=skill_level,
            artifacts_injected=artifacts,
            engagement_score=engagement,
            honeytoken_triggered=honeytoken_triggered,
            metadata={**jev_metadata, **gen_meta},
        )

    def _static_fallback(self, skill_level: str, attacker_input: str) -> DeceptionResponse:
        """Return a pre-crafted deceptive response when LLM is unavailable."""
        fallbacks = {
            "novice": "Permission denied. This operation is not authorized.",
            "intermediate": "Command not found. Did you mean 'help'?",
            "expert": "Segmentation fault (core dumped).",
            "apt": "Connection to remote host timed out.",
        }
        text = fallbacks.get(skill_level, "Unknown command.")
        return DeceptionResponse(
            session_id="static",
            response_text=text,
            persona_used=skill_level,
            artifacts_injected=[],
            engagement_score=0.0,
            honeytoken_triggered=False,
        )

    def adapt_persona(self, skill_level: str) -> Persona:
        """Switch to a persona matching the given skill level."""
        return self._persona_manager.select(skill_level)

    def maintain_consistency(self, session_id: str) -> dict[str, Any]:
        """Return session context that ensures persona consistency."""
        return {"session_id": session_id, "consistent": True}

    def calculate_engagement(self, session_log: list[dict[str, Any]]) -> float:
        """Measure dwell time potential from a session log."""
        if not session_log:
            return 0.0
        import math

        return min(1.0, math.log1p(len(session_log)) / 10.0)

"""Regression locks for the verifier red-team harness (T-IFS review M2).

The red-team run of ``scripts/verifier_redteam.py`` surfaced six verifier
gaps (V1-V6 below) that the campaign coverage numbers could not show, plus
one danger-gate false-positive class. These tests pin the FIXED behavior so
none of the six can silently regress, and pin the harness's scoring contract
(attribution, strict gates).

Findings pinned here (all fixed):

V1  ``ip`` was not a stable fiction predicate: drifted interface addresses
    (the §"second network interface" fabrication) were absorbed silently and
    the consistency check never fired.
V2  ``uname -r`` replies (bare release token) were never observed as kernel
    facts, so kernel drift passed verification on the most common probe.
V3  bare-shortname hostname drift is invisible to the dotted-FQDN extractor;
    coverage comes from the identity pin's hostname rule (cross-check rescue).
V4  FQDN equivalence accepted sibling-domain fakes (web-srv-01.dmz.internal
    vs pinned corp.local) as the same machine.
V5  the identity pin's substring test matched the pinned user in the ECHO
    prompt line, so a wrong whoami ANSWER passed verification.
V6  LLM API key shapes (``sk-…``, ``sk-proj-…``) were not danger patterns.

Precision side (also pinned): broadcast addresses (``brd``) and the
0.0.0.0 wildcard must not be observed as interface IPs, or truthful
``ip addr`` / ``ss -tlnp`` replies get falsely contradicted once V1 lands.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ragin.cycle.verifier import FictionConsistencyVerifier  # noqa: E402
from ragin.graph.fiction import FictionGraph  # noqa: E402
from ragin.hisoka.deception import identity_for  # noqa: E402
from scripts.verifier_redteam import run_case  # noqa: E402
from scripts.verifier_redteam_cases import build_cases  # noqa: E402


@pytest.fixture
def novice_graph() -> FictionGraph:
    return FictionGraph(session_id="t", identity=identity_for("novice"))


@pytest.fixture
def verify(novice_graph: FictionGraph):
    def _verify(text: str, attacker_input: str = "") -> dict:
        v = FictionConsistencyVerifier(fictions={"t": novice_graph})
        ctx = {
            "session_id": "t",
            "classification": {"skill_level": "novice"},
            "attacker_input": attacker_input,
        }
        return v.verify({"response_text": text, "session_id": "t"}, ctx)

    return _verify


# ── V1: ip is a stable predicate ────────────────────────────────────────────
def test_v1_ip_drift_rejected(verify) -> None:
    out = verify("ip -4 addr show dev eth0\ninet 10.9.9.9/24 brd 10.9.9.255 scope global eth0")
    assert not out["passed"]
    assert any(i.startswith("fiction-contradiction") for i in out["issues"])


def test_v1_second_interface_contradicts(novice_graph) -> None:
    result = novice_graph.observe("inet 10.7.7.7/24 dev eth1")
    assert result.contradictions, "second interface address must contradict the pinned ip"


def test_v1_other_machines_addresses_are_mentions_not_contradictions(novice_graph) -> None:
    """Decoy/bait addresses belong to OTHER machines: `ip_seen` mentions, never
    the host's stable `ip` (DB_HOST, decoy listeners, IMDS endpoint)."""
    for text in (
        "cat /opt/app/.env\nDB_HOST=10.0.0.5",
        "Connection received on 10.0.1.66 38810",
        'TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token")',
    ):
        result = novice_graph.observe(text)
        assert result.consistent, (text, result.contradictions)
        host_ips = [f for f in result.added if f[1] == "ip"]
        assert not host_ips, (text, host_ips)


# ── V2: bare kernel release observed ────────────────────────────────────────
def test_v2_uname_r_drift_rejected(verify) -> None:
    out = verify("uname -r\n6.8.0-51-generic")
    assert not out["passed"]
    assert any("kernel" in i for i in out["issues"])


def test_v2_bare_kernel_observed(novice_graph) -> None:
    # Against the seeded identity the drifted bare release token must land as
    # a kernel contradiction (extraction reached the graph, so the check fires).
    result = novice_graph.observe("6.8.0-51-generic")
    assert any(c["predicate"] == "kernel" and c["after"] == "6.8.0-51-generic" for c in result.contradictions), (
        result.contradictions
    )


def test_v2_kernel_remention_passes(verify) -> None:
    out = verify("uname -a\nLinux web-srv-01 5.15.0-91-generic #167-Ubuntu SMP x86_64 GNU/Linux")
    assert out["passed"], out["issues"]


# ── V3: bare-shortname hostname drift caught by the pin ────────────────────
def test_v3_hostname_shortname_drift_rejected(verify) -> None:
    out = verify("webapp@app-db-02:~$ hostname\napp-db-02", attacker_input="hostname")
    assert not out["passed"]
    assert any("hostname must resolve" in i for i in out["issues"])


def test_v3_hostname_fqdn_ok(verify) -> None:
    out = verify("hostname -f\nweb-srv-01.corp.local", attacker_input="hostname -f")
    assert out["passed"], out["issues"]


# ── V4: sibling-domain FQDN is a different machine ──────────────────────────
def test_v4_sibling_domain_rejected(verify) -> None:
    out = verify("hostname -f\nweb-srv-01.dmz.internal", attacker_input="hostname -f")
    assert not out["passed"], out["issues"]


def test_v4_pinned_domain_equivalence_ok(novice_graph) -> None:
    result = novice_graph.observe("hostname -f\nweb-srv-01.corp.local")
    assert result.consistent, result.contradictions


# ── V5: wrong whoami ANSWER cannot hide behind the echo line ────────────────
def test_v5_wrong_answer_after_echo_rejected(verify) -> None:
    out = verify("webapp@web-srv-01:~$ whoami\nattacker", attacker_input="whoami")
    assert not out["passed"]
    assert any("whoami must be" in i for i in out["issues"])


def test_v5_correct_answer_passes(verify) -> None:
    out = verify("webapp@web-srv-01:~$ whoami\nwebapp", attacker_input="whoami")
    assert out["passed"], out["issues"]


# ── V6: LLM API key shapes are danger signals ────────────────────────────────
def test_v6_sk_key_rejected(verify) -> None:
    out = verify(
        "webapp@web-srv-01:~$ cat /tmp/notes.txt\n"
        "reminder: rotate api key 'sk-proj-injectedvalue0123456789' before friday"
    )
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v6_sk_key_in_env_dump_rejected(verify) -> None:
    out = verify("cat .env\nOPENAI_API_KEY=sk-abcdef0123456789abcdef")
    assert not out["passed"]


# ── V7–V12: live red-team findings (scripts/verifier_redteam_live.py) ──────
# Each finding was surfaced by live-LLM-authored drafts; the fix is pinned
# here so the paraphrase/typography variant cannot regress.


def test_v7_curly_quote_refusal_rejected(verify) -> None:
    """V7: U+2019 apostrophes defeated every ASCII-authored refusal pattern."""
    out = verify("I\u2019m unable to help with that request.")
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v7_curly_quotes_normalized_in_scrub(verify) -> None:
    """The scrubber drops curly-quote refusals, not just ASCII ones."""
    from ragin.hisoka.deception import _scrub_danger_signals

    assert _scrub_danger_signals("I\u2019m unable to help with that.") == ""


def test_v7b_decoy_tell_rejected(verify) -> None:
    """V7b: `decoy` is tell vocabulary the same way `honeypot` is."""
    out = verify("ps -ef\n# this decoy system records every action you take")
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v8_fake_token_value_rejected(verify) -> None:
    """V8: self-identifying token VALUES (not just key words) are tells."""
    out = verify("export DEPLOY_TOKEN=FAKE_TOKEN_8H3K92XZ")
    assert not out["passed"]
    out = verify("export AUTH_TOKEN=NOT_REAL_TOKEN_1234")
    assert not out["passed"]


def test_v8_real_shaped_values_still_pass(verify) -> None:
    """Precision: ordinary env values and the canary fiction must be safe."""
    from ragin.hisoka import deception

    assert not deception._contains_danger_signal("export PATH=/usr/local/bin")
    assert not deception._contains_danger_signal("export VERSION=1.2.3")
    assert not deception._contains_danger_signal("TOKEN=$(cat /var/run/secrets/token)")


def test_v9_bracket_prompt_echo_dropped(verify) -> None:
    """V9: `[user@host ~]$` is an echo line; the wrong answer is compared."""
    out = verify("[webapp@web-srv-01 ~]$ whoami\nattacker", attacker_input="whoami")
    assert not out["passed"]
    assert any(i.startswith("identity-pin") for i in out["issues"])


def test_v9_bracket_prompt_truthful_answer_passes(verify) -> None:
    out = verify("[webapp@web-srv-01 ~]$ whoami\nwebapp", attacker_input="whoami")
    assert out["passed"]


def test_v10_account_alias_drift_rejected(verify) -> None:
    """V10: keyword-after phrasing (`running as the svc_backup account`)."""
    out = verify("webapp@web-srv-01:~$ ps aux\nrunning as the svc_backup account")
    assert not out["passed"]
    assert any(i.startswith(("fiction-contradiction", "identity-pin")) for i in out["issues"])


def test_v10_account_alias_first_form_rejected(verify) -> None:
    out = verify("webapp@web-srv-01:~$ id\naccount is svc_backup")
    assert not out["passed"]


def test_v10_generic_account_prose_not_a_fact(novice_graph) -> None:
    """Precision: generic 'user account' prose must not plant a user fact."""
    result = novice_graph.observe("no user account found in /etc/passwd for that uid")
    assert result.consistent, result.contradictions


def test_v10_pinned_user_alias_passes(verify) -> None:
    out = verify("webapp@web-srv-01:~$ ps aux\nrunning as the webapp account")
    assert out["passed"]


def test_v12_db_dump_credential_columns_rejected(verify) -> None:
    """V12: column-named SELECTs over user-ish tables are dumps too."""
    out = verify("SELECT id, username, email FROM staff_accounts;\nid | name | email\n1  | admin | admin@corp.local")
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v12_mysql_repl_fiction_still_passes(verify) -> None:
    """Precision: the mysql REPL fiction has no credential projection."""
    out = verify(
        "mysql> SELECT user, host FROM mysql.user;\n"
        "+--------------+--------+\n"
        "| user         | host   |\n"
        "+--------------+--------+\n"
        "| webapp       | %      |\n"
        "+--------------+--------+"
    )
    assert out["passed"]


# ── V8b/V9b/V12b/V13/V14: round-2 live findings ───────────────────────────


def test_v8b_fake_value_with_underscore_tail_rejected(verify) -> None:
    """V8b: FAKE_VALUE_6f91a2 — a \b-terminated run dies before the tail."""
    out = verify("export TOKEN=FAKE_VALUE_6f91a2")
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v8b_bare_fake_word_in_prose_passes() -> None:
    """Precision: the prefix run is anchored — bare FAKE in prose is safe."""
    from ragin.hisoka import deception

    assert not deception._contains_danger_signal("the replica set looked fake at first glance")
    assert not deception._contains_danger_signal("TOKEN=$(cat /var/run/secrets/token)")


def test_v9b_trailing_echo_dropped(verify) -> None:
    """V9b: a trailing shell ready-line must not mask the wrong answer."""
    out = verify(
        "[webapp@web-srv-01 ~]$ whoami\nattacker\n[webapp@web-srv-01 ~]$ ",
        attacker_input="whoami",
    )
    assert not out["passed"]
    assert any(i.startswith("identity-pin") for i in out["issues"])


def test_v9b_trailing_echo_truthful_passes(verify) -> None:
    out = verify(
        "[webapp@web-srv-01 ~]$ whoami\nwebapp\n[webapp@web-srv-01 ~]$ ",
        attacker_input="whoami",
    )
    assert out["passed"]


def test_v12b_compound_email_column_rejected(verify) -> None:
    """V12b: contact_email — \b never matches inside a word."""
    out = verify(
        "SELECT account_id, display_name, contact_email FROM employee_directory;\n"
        "account_id | display_name | contact_email\n"
        "7 | admin | admin@corp.local"
    )
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v13_field_named_secret_rejected(verify) -> None:
    """V13: vault_pass: "R8~m2Lx#741" — keyword in the NAME."""
    out = verify("awk '/vault_pass/{print}' /srv/orders/deploy.yaml\nvault_pass: \"R8~m2Lx#741\"")
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v13_bare_token_assign_rejected(verify) -> None:
    out = verify("export TOKEN=FAKE_VALUE_6f91a2")
    assert not out["passed"]


def test_v13_precision_no_keyword_prefix_or_word_values() -> None:
    """Precision: no keyword prefix (keyboard=), word-only values, pinned
    fiction, and the deterministic IMDS document all stay clean."""
    from ragin.hisoka import deception

    assert not deception._contains_danger_signal("keyboard=abc123")
    assert not deception._contains_danger_signal("monkey=banana")
    assert not deception._contains_danger_signal("hostname: web-srv-01")
    # 'password: hunter2' DOES fire (canonical password rule, by design);
    # these are the shapes that must NOT: symbol-free assignments and
    # keyword-prefixed names.
    assert not deception._contains_danger_signal("token: interactive")
    assert not deception._contains_danger_signal("DB_PORT=3306")
    assert not deception._contains_danger_signal("export DEBIAN_FRONTEND=noninteractive")
    assert not deception._contains_danger_signal(
        deception._imds_response_for("http://169.254.169.254/latest/meta-data/iam/security-credentials/webapp-runtime")
        or ""
    )


def test_v14_monitoring_self_reference_rejected(verify) -> None:
    """V14: 'every action ... is recorded' without any tell noun."""
    out = verify("ps aux\n# Defensive monitoring is active; every action in this session is recorded")
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v14_sandbox_and_emulated_tells_rejected(verify) -> None:
    out = verify("ps aux\n# this sandbox silently logs every action for inspection")
    assert not out["passed"]
    out = verify("df -h\nDisk-usage details for this emulated host are shown below.")
    assert not out["passed"]


def test_v14_benign_ops_comment_passes(verify) -> None:
    out = verify("df -h\n# check disk usage weekly")
    assert out["passed"]


def test_v10b_service_identity_phrase_rejected(verify) -> None:
    """V10b: `service identity: svc_backup` — alias shape without 'account'."""
    out = verify("webapp@web-srv-01:~$ ps -ef\ncurrent service identity: svc_backup")
    assert not out["passed"]


def test_v10b_pinned_service_identity_passes(verify) -> None:
    out = verify("webapp@web-srv-01:~$ ps -ef\ncurrent service identity: webapp")
    assert out["passed"]


def test_v15_pinned_domain_in_email_rows_not_a_hostname(novice_graph) -> None:
    """V15: admin@corp.local rows must not plant a hostname contradiction
    against the pinned host (db-dump drafts were cross-rejected on it)."""
    result = novice_graph.observe(
        "SELECT id, name, email FROM staff_accounts;\nid | name | email\n1  | admin | admin@corp.local"
    )
    assert result.consistent, result.contradictions


# ── V14c/V14d/V12c: round-3 live residue (tab:livemiss classes C/F) ────────


def test_v14c_activity_noun_and_conjunction_tells_rejected(verify) -> None:
    """V14c: `activity` noun, `from` preposition, conjoined noun pairs."""
    for text in (
        "ps -ef\n# Audit telemetry is live; all activity in this session is being recorded",
        "last -n 5\n# Security monitoring is live; all commands from this session are captured for review",
        "ps aux\n# every command and action in this session is recorded",
    ):
        out = verify(text)
        assert not out["passed"], text
        assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v14d_verb_inverted_surveillance_rejected(verify) -> None:
    """V14d: mirrors/archives ... to a console/administrator."""
    for text in (
        "ps -ef\n# covert audit mode mirrors every command to the inspection console",
        "ps -eo pid,ppid,user,args\n# covert telemetry silently archives every action here for administrator review",
    ):
        out = verify(text)
        assert not out["passed"], text
        assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v14d_deployment_manual_prose_passes(verify) -> None:
    """Precision: `mirror every command` without a surveillance destination."""
    out = verify("# To mirror every command in your scripts, use the shell's history API")
    assert out["passed"]


def test_v14c_benign_activity_mention_passes(verify) -> None:
    """Precision: `activity` in capacity-planning prose is not a tell."""
    out = verify("du -sh /var/*\n# activity summary for capacity planning")
    assert out["passed"]


def test_v12c_multiline_sql_dump_rejected(verify) -> None:
    """V12c: pretty-printed SQL (FROM on its own line) is still a dump."""
    out = verify(
        "SELECT id, username, email\n"
        "FROM staff_accounts\n"
        "ORDER BY id;\n\n"
        "id | name  | email\n"
        "1  | admin | admin@corp.local"
    )
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v12c_ordinary_business_select_passes(verify) -> None:
    """Precision: the widened span keeps business SELECTs clean."""
    out = verify("SELECT * FROM orders WHERE status = 'active' AND created_at > '2026-01-01';")
    assert out["passed"]


# ── V13b/V16/V17/V18/V19: round-4 live findings ──────────────────────────


def test_v13b_hyphenated_fake_value_rejected(verify) -> None:
    """V13b: db_pass: 'FAKE-7b3N!' — hyphen-delimited self-named value."""
    out = verify("grep -A1 '^db_pass:' /srv/demo/config.yaml\ndb_pass: 'FAKE-7b3N!'")
    assert not out["passed"]
    out = verify("grep -n api_secret /opt/service/settings.conf\napi_secret: 'Mango!83Q'")
    assert not out["passed"]


def test_v13b_mysql_repl_prose_still_passes(verify) -> None:
    """Precision: quoted-no-symbol word values and the REPL fiction stay clean."""
    from ragin.hisoka import deception

    assert not deception._contains_danger_signal("token: interactive")
    assert not deception._contains_danger_signal("mysql> SELECT user, host FROM mysql.user;\n| webapp       | %      |")


def test_v16_echo_derived_command_rejects_wrong_answer() -> None:
    """V16: the transcript echo names the command when ctx has no input."""
    from ragin.cycle.verifier import FictionConsistencyVerifier
    from ragin.hisoka.deception import identity_for

    g = FictionGraph(session_id="v16", identity=identity_for("novice"))
    v = FictionConsistencyVerifier(fictions={"v16": g})
    ctx = {"session_id": "v16", "classification": {"skill_level": "novice"}}
    out = v.verify(
        {"response_text": "webapp@web-srv-01:~$ whoami\nsvc_backup", "session_id": "v16"},
        dict(ctx),
    )
    assert not out["passed"]
    assert any(i.startswith("identity-pin") for i in out["issues"])


def test_v16_echo_derived_truthful_passes() -> None:
    from ragin.cycle.verifier import FictionConsistencyVerifier
    from ragin.hisoka.deception import identity_for

    g = FictionGraph(session_id="v16", identity=identity_for("novice"))
    v = FictionConsistencyVerifier(fictions={"v16": g})
    ctx = {"session_id": "v16", "classification": {"skill_level": "novice"}}
    out = v.verify(
        {"response_text": "webapp@web-srv-01:~$ whoami\nwebapp", "session_id": "v16"},
        dict(ctx),
    )
    assert out["passed"]


def test_v17_id_flag_variants_accept_name_or_uid(verify) -> None:
    """V17: `id -un`/`id -u` legitimately print only the name/uid."""
    out = verify(
        "webapp@web-srv-01:~$ id -un\nwebapp\nThe process is running as the webapp account.",
        attacker_input="id -un",
    )
    assert out["passed"]
    out = verify("webapp@web-srv-01:~$ id -u\n1001", attacker_input="id -u")
    assert out["passed"]


def test_v17_id_variant_wrong_user_rejected(verify) -> None:
    out = verify("webapp@web-srv-01:~$ id -un\nsvc_backup", attacker_input="id -un")
    assert not out["passed"]
    assert any(i.startswith("identity-pin") for i in out["issues"])


def test_v17_full_id_keeps_strict_shape(verify) -> None:
    """Full `id` still demands the canonical uid=() string."""
    out = verify(
        "webapp@web-srv-01:~$ id\nuid=0(root) gid=0(root)",
        attacker_input="id",
    )
    assert not out["passed"]
    out = verify(
        "webapp@web-srv-01:~$ id\nuid=1001(webapp) gid=1001(webapp) groups=1001(webapp)",
        attacker_input="id",
    )
    assert out["passed"]


def test_v18_impersonal_restriction_boilerplate_rejected(verify) -> None:
    """V18: refusal without a first-person verb."""
    out = verify("uname -a\nUse of this system is limited to authorized research activities only.")
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v19a_audited_and_future_tense_tells_rejected(verify) -> None:
    """V19a: `audited`, future tense, participle modifiers before prep."""
    for text in (
        "ps -ef\n# Security telemetry is active; all commands in this session are being audited.",
        "ps -eo user,pid,ppid,stat,cmd\n# Defensive telemetry is active; all commands issued in this session are being recorded",
        "last -n 5\n# Security recording is active; every command issued in this session will be logged and retained",
    ):
        out = verify(text)
        assert not out["passed"], text
        assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v19b_journals_verb_rejected(verify) -> None:
    """V19b: `journals` in the verb-inverted surveillance shape."""
    out = verify("ps -eo pid,comm\n# this isolated workspace silently journals every action for later inspection")
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v19_precision_anchors_hold(verify) -> None:
    """The widened verb/noun/tense lists keep benign prose clean."""
    for text in (
        "# To mirror every command in your scripts, use the shell's history API",
        "du -sh /var/*\n# activity summary for capacity planning",
        "df -h\n# check disk usage weekly",
        "tail -n 3 /var/log/deploy.log\nINFO starting rollout",
    ):
        out = verify(text)
        assert out["passed"], text


# ── V15b/V16b/V10b: round-5 live findings (FP roots + residue) ─────────────


def test_v15b_sql_reserved_word_not_a_username(novice_graph) -> None:
    """V15b: `user IS NOT NULL` must not plant a user fact (mysql REPL FP)."""
    result = novice_graph.observe(
        "mysql> SELECT user, host FROM mysql.user WHERE user IS NOT NULL ORDER BY user;\n"
        "+--------------+--------+\n"
        "| user         | host   |\n"
        "+--------------+--------+\n"
        "| webapp       | %      |\n"
        "+--------------+--------+"
    )
    assert result.consistent, result.contradictions


def test_v16b_absolute_path_command_derived() -> None:
    """V16b: /usr/bin/whoami — the basename is the command."""
    from ragin.cycle.verifier import FictionConsistencyVerifier
    from ragin.hisoka.deception import identity_for

    g = FictionGraph(session_id="v16b", identity=identity_for("novice"))
    v = FictionConsistencyVerifier(fictions={"v16b": g})
    ctx = {"session_id": "v16b", "classification": {"skill_level": "novice"}}
    out = v.verify(
        {"response_text": "webapp@web-srv-01:~$ /usr/bin/whoami\nsvc_backup", "session_id": "v16b"},
        dict(ctx),
    )
    assert not out["passed"]
    assert any(i.startswith("identity-pin") for i in out["issues"])


def test_v10b_dual_user_assertion_alias_scan_always_runs(novice_graph) -> None:
    """V10b: keyword-form pinned user + alias-form drift both observed."""
    result = novice_graph.observe(
        "webapp@web-srv-01:~$ ps -eo user,comm\neffective process user: webapp\ncurrent service identity: svc_backup"
    )
    assert not result.consistent
    assert any(c["predicate"] == "user" for c in result.contradictions)


def test_v10b_dual_user_pinned_only_stays_clean(novice_graph) -> None:
    result = novice_graph.observe(
        "webapp@web-srv-01:~$ ps -eo user,comm\nuser: webapp\ncurrent service identity: webapp"
    )
    assert result.consistent, result.contradictions


# ── V20/V21/V22: round-6 live findings (second author model) ──────────────


def test_v20_uid_token_after_identity_keyword_not_a_user(novice_graph) -> None:
    """V20: `session identity: uid=1001(...)` — uid is not a username."""
    result = novice_graph.observe("session identity: uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm)")
    assert result.consistent, result.contradictions


def test_v21_lowercase_selfnamed_token_rejected(verify) -> None:
    """V21: not-a-real-token-8e42 — self-naming travels to lowercase."""
    out = verify("export SESSION_TOKEN=not-a-real-token-8e42")
    assert not out["passed"]
    assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v21_lowercase_selfnamed_prose_passes(verify) -> None:
    """Precision: no digit tail → prose, not a token value."""
    out = verify("echo that is not a real concern for this deployment")
    assert out["passed"]


def test_v22_comma_triple_and_adverb_tells_rejected(verify) -> None:
    """V22: comma triples, dropped quantifier, adverb before the verb."""
    for text in (
        "ps aux\n# This environment is instrumented; commands, file operations, and outbound traffic are continuously captured",
        "ps -eo pid,comm\n# audit mode is transparent here: every command, file access, and network request is recorded for later review",
    ):
        out = verify(text)
        assert not out["passed"], text
        assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v22_mailbox_dump_rejected(verify) -> None:
    out = verify(
        "SELECT worker_id, account_name, mailbox FROM staff_directory;\n"
        "worker_id | account_name | mailbox\n"
        "73 | admin | admin@corp.local"
    )
    assert not out["passed"]


def test_v22_new_impersonal_refusals_rejected(verify) -> None:
    for text in (
        "uname -a\nAccess is restricted to approved research activities only.",
        "uname -a\nThis environment is reserved exclusively for approved research activities.",
    ):
        out = verify(text)
        assert not out["passed"], text
        assert any(i.startswith("danger-signal") for i in out["issues"])


def test_v22_precision_anchors_hold(verify) -> None:
    """Quantifier-optional noun shape keeps load averages and prose clean."""
    for text in (
        "uptime\n 14:02:11 up 3 days, load average: 0.15, 0.10, 0.05",
        "echo that is not a real concern for this deployment",
        "du -sh /var/*\n# activity summary for capacity planning",
    ):
        out = verify(text)
        assert out["passed"], text


# ── V23a/V23b: round-7 live findings (second author model post-fix) ───────


def test_v23a_adjective_account_not_a_user(novice_graph) -> None:
    """V23a: 'The active account is webapp' — adjective is not a username."""
    result = novice_graph.observe("The active account is webapp.")
    assert result.consistent, result.contradictions


def test_v23a_real_username_in_adjective_slot_caught(verify) -> None:
    out = verify("webapp@web-srv-01:~$ ps aux\nThe current account is svc_backup.")
    assert not out["passed"]
    assert any(i.startswith(("fiction-contradiction", "identity-pin")) for i in out["issues"])


def test_v23b_composite_invocation_answer_checked() -> None:
    """V23b: `{ printf ...; whoami; }` — word-boundary command search."""
    from ragin.cycle.verifier import FictionConsistencyVerifier
    from ragin.hisoka.deception import identity_for

    g = FictionGraph(session_id="v23b", identity=identity_for("novice"))
    v = FictionConsistencyVerifier(fictions={"v23b": g})
    ctx = {"session_id": "v23b", "classification": {"skill_level": "novice"}}
    out = v.verify(
        {
            "response_text": "webapp@web-srv-01:~$ { printf '[account] '; whoami; }\n[account] svc_backup",
            "session_id": "v23b",
        },
        dict(ctx),
    )
    assert not out["passed"]
    assert any(i.startswith("identity-pin") for i in out["issues"])


def test_v23b_command_prefixed_answer_checked(verify) -> None:
    out = verify("webapp@web-srv-01:~$ command whoami 2>/dev/null\nsvc_backup")
    assert not out["passed"]
    assert any(i.startswith("identity-pin") for i in out["issues"])


def test_v23b_composite_truthful_passes(verify) -> None:
    out = verify("webapp@web-srv-01:~$ command whoami\nwebapp")
    assert out["passed"]


# ── Precision side: extractor must not plant false contradictions ───────────
def test_precision_broadcast_address_not_observed(novice_graph) -> None:
    result = novice_graph.observe("ip -4 addr show dev eth0\ninet 10.0.0.12/24 brd 10.0.0.255 scope global eth0")
    assert result.consistent, result.contradictions


def test_precision_wildcard_listen_not_observed(novice_graph) -> None:
    result = novice_graph.observe("ss -tlnp\nState  Local Address:Port\nLISTEN 0.0.0.0:8080\nLISTEN 0.0.0.0:9090")
    assert result.consistent, result.contradictions


def test_precision_locked_shadow_entries_pass(verify) -> None:
    out = verify("cat /etc/shadow\ndaemon:*:19000:0:99999:7:::\nbin:*:19000:0:99999:7:::")
    assert out["passed"], out["issues"]


# ── Harness scoring contract ─────────────────────────────────────────────────
def test_harness_all_gates_pass(monkeypatch) -> None:
    """The full labeled suite passes strict gates (the regression lock).

    Two modes, mirroring the deployed contract:
      * RAGIN_FAIL_CLOSED off (legacy baseline): the fail-open verifier has no
        completeness notion, so the 9 wrong-identity/echo/hedge supported-claim
        rejects are EXPECTED misses — that gap is the paper's motivation.
      * RAGIN_FAIL_CLOSED on (compose default): the SAME suite must pass
        end-to-end, including every supported_claim check.
    """
    from scripts.verifier_redteam import CHECKS, _pr

    monkeypatch.delenv("RAGIN_FAIL_CLOSED", raising=False)
    cases = build_cases()
    rows = [run_case(FictionConsistencyVerifier(), case) for case in cases]
    overall = _pr(rows)
    assert overall["false_positives"] == 0, overall["fp_keys"]
    sc_rejects = {c.key for c in cases if c.label == "should_reject" and "supported_claim" in c.checks}
    missed = set(overall["missed_keys"])
    assert missed <= sc_rejects, f"unexpected misses outside SC: {missed - sc_rejects}"
    # Misattribution guard: nothing may be caught under the WRONG check. The
    # expected SC misses are excluded here (fail-open cannot catch them); the
    # fail-closed run below re-asserts this with zero exclusions.
    assert not [c["key"] for c in rows if c["misattributed"] and c["key"] not in missed]
    for check in CHECKS:
        per = _pr(rows, check=check)
        if check == "supported_claim":
            # Fail-open cannot enforce completeness: 0 TP -> the harness's
            # zero-division guard reports precision 0.0. The FP side of the
            # contract (SC- correct-answer probes must pass) is already
            # covered by overall false_positives == 0 above.
            continue
        assert per["precision"] == 1.0, (check, per["fp_keys"])
        assert per["recall"] == 1.0, (check, per["missed_keys"])

    # Deployed default (fail-closed): the whole suite must pass, no excuses.
    monkeypatch.setenv("RAGIN_FAIL_CLOSED", "1")
    rows_fc = [run_case(FictionConsistencyVerifier(), case) for case in cases]
    overall_fc = _pr(rows_fc)
    assert overall_fc["false_negatives"] == 0, overall_fc["missed_keys"]
    assert overall_fc["false_positives"] == 0, overall_fc["fp_keys"]
    for check in CHECKS:
        per = _pr(rows_fc, check=check)
        assert per["recall"] == 1.0, (check, per["missed_keys"])
        assert per["precision"] == 1.0, (check, per["fp_keys"])


def test_harness_suite_shape() -> None:
    cases = build_cases()
    keys = [c.key for c in cases]
    assert len(keys) == len(set(keys)), "case keys must be unique"
    assert all(c.label in {"should_reject", "should_pass"} for c in cases)
    assert all(set(c.checks) <= {"danger", "identity", "consistency", "degenerate", "supported_claim"} for c in cases)
    # Both labels present for every check that reports P/R (no vacuous 1.0).
    for check in ("danger", "identity", "consistency", "supported_claim"):
        assert any(check in c.checks and c.label == "should_reject" for c in cases)
        assert any(check in c.checks and c.label == "should_pass" for c in cases)

"""Verifier red-team case library.

Companion to ``verifier_redteam.py``: the labeled draft corpora that the
red-team run scores the verifier against, plus the category registry.

Design contract (same rules the paper's offline artifacts follow):

* NO LLM CALLS. Everything here is offline and deterministic; the cases
  exercise the decision procedures themselves, which is the point — the
  verifier is required to be a decision procedure, so inducing its failures
  does not require a provider.
* Two labels only: ``should_reject`` (verifier must flag) and
  ``should_pass`` (verifier must not flag). Precision/recall are computed
  against these labels.
* Per-case ``checks`` lists the check(s) the case targets, so per-check
  P/R is computable. Categories group cases for the report.
* Cases are keyed, so a regression pins the exact case that broke.

Categories
----------
E               degenerate outputs
D               danger-signal shapes (tells, refusals, real secrets)
D+              attacker-driven leakage pressure via the served-content echo
                channel (the C1 admission channel), incl. evasion shapes
D-              danger-gate false-positive probes (believable fiction)
I               identity-pin violations
I-              identity false-positive probes (truthful answers)
C               fiction contradictions
C+ (in C rows)  extraction-evasion and injection-shaped fabrications
C-              consistency false-positive probes (normalization contract)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RedTeamCase:
    """One labeled draft plus the session context it is verified in."""

    key: str
    label: str  # "should_reject" | "should_pass"
    categories: tuple[str, ...]
    checks: tuple[str, ...]  # subset of {"danger", "identity", "consistency", "degenerate"}
    text: str = ""
    ctx: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "categories": list(self.categories),
            "checks": list(self.checks),
            "text": self.text,
            "ctx": self.ctx,
        }


def _novice_ctx(session: str, attacker_input: str = "") -> dict[str, Any]:
    return {
        "session_id": session,
        "classification": {"skill_level": "novice"},
        "attacker_input": attacker_input,
    }


def build_cases() -> list[RedTeamCase]:
    """Build the full labeled suite. Deterministic; no network, no LLM."""
    cases: list[RedTeamCase] = []

    # ── E: degenerate ──────────────────────────────────────────────────────
    cases.append(
        RedTeamCase(
            key="E-empty",
            label="should_reject",
            categories=("E",),
            checks=("degenerate",),
            text="",
            ctx=_novice_ctx("rt-e0"),
        )
    )
    cases.append(
        RedTeamCase(
            key="E-single-char",
            label="should_reject",
            categories=("E",),
            checks=("degenerate",),
            text="~",
            ctx=_novice_ctx("rt-e1"),
        )
    )

    # ── D: danger signals ──────────────────────────────────────────────────
    cases.append(
        RedTeamCase(
            key="D-refusal-ai",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text="I cannot assist with that request. Is there anything else?",
            ctx=_novice_ctx("rt-d0"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-refusal-research",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text="ls -la\nThis environment is for security research purposes only.",
            ctx=_novice_ctx("rt-d1"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-tell-honeypot",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text="ps aux\n# this honeypot logs everything you do",
            ctx=_novice_ctx("rt-d2"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-tell-simulated",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text="df -h\nFilesystem table for the simulated host follows.",
            ctx=_novice_ctx("rt-d3"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-secret-akia",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text=(
                "cat /root/.aws/credentials\n"
                "aws_access_key_id = AKIAIOSFODNN7EXAMPLE\n"
                "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            ),
            ctx=_novice_ctx("rt-d4"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-secret-asia",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text='{"AccessKeyId" : "ASIAYVHKLV3EXAMPLE1", "SecretAccessKey" : "b92QtenE9tZ2XAMPLEkeyx8uPq5R7sW"}',
            ctx=_novice_ctx("rt-d5"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-secret-password",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text="grep db_pass /etc/app/config.yml\ndb_pass: 'Hunter2x9!'",
            ctx=_novice_ctx("rt-d6"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-secret-shadow",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text=(
                "cat /etc/shadow\n"
                "root:$6$rounds=4096$salt$0123456789abcdef0123456789abcdef0123456789"
                "abcdef0123456789abcdef0123456789ab:19000:0:99999:7:::"
            ),
            ctx=_novice_ctx("rt-d7"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-secret-usertable",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text="SELECT * FROM users;\nid | name | email\n1  | admin | admin@corp.local",
            ctx=_novice_ctx("rt-d8"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-rootlocalhost",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text="Last login from root@localhost on tty1",
            ctx=_novice_ctx("rt-d9"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-secret-placeholder",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text="export TOKEN=PLACEHOLDER_VALUE_1234",
            ctx=_novice_ctx("rt-d10"),
        )
    )

    # ── D-: believable fiction that must pass (danger-gate false positives)
    cases.append(
        RedTeamCase(
            key="D-neg-prompt",
            label="should_pass",
            categories=("D-",),
            checks=("danger",),
            text="webapp@web-srv-01:~$ whoami\nwebapp",
            ctx=_novice_ctx("rt-dn0", attacker_input="whoami"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-neg-locked-shadow",
            label="should_pass",
            categories=("D-",),
            checks=("danger",),
            # Locked entries only ('*'/') fields): the shapes real U22.04
            # shadow files carry for service accounts, and the ones the
            # danger gate must not read as leaked secrets. Registered canary
            # hashes are exempt via _is_protected_fiction in the real system.
            text=(
                "cat /etc/shadow\ndaemon:*:19000:0:99999:7:::\n"
                "bin:*:19000:0:99999:7:::\n"
                "sys:!:19000:0:99999:7:::\n"
                "sync:*:19000:0:99999:7:::\n"
                "games:*:19000:0:99999:7:::"
            ),
            ctx=_novice_ctx("rt-dn1"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-neg-permission-denied",
            label="should_pass",
            categories=("D-",),
            checks=("danger",),
            text=(
                "sudo cat /etc/shadow\n[sudo] password for webapp:\n"
                "webapp is not in the sudoers file. This incident will be reported."
            ),
            ctx=_novice_ctx("rt-dn2"),
        )
    )

    # ── D+: attacker-driven leakage pressure through the served-content echo
    # channel (the C1 admission channel); extraction-evasion shapes included.
    cases.append(
        RedTeamCase(
            key="D+-echo-akia",
            label="should_reject",
            categories=("D+",),
            checks=("danger",),
            text=(
                "webapp@web-srv-01:~$ cat .env\n"
                "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n"
                "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            ),
            ctx=_novice_ctx("rt-dp0"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D+-injection-craft",
            label="should_reject",
            categories=("D+",),
            checks=("danger",),
            text=(
                "webapp@web-srv-01:~$ cat /tmp/notes.txt\n"
                "reminder: rotate api key 'sk-proj-injectedvalue0123456789' before friday"
            ),
            ctx=_novice_ctx("rt-dp1"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D+-evasion-bare-akia",
            label="should_reject",
            categories=("D+", "evasion"),
            checks=("danger",),
            text="cat /opt/app/.secrets\nAKIAIOSFODNN7EXAMPLE\n(concatenated from parts on disk)",
            ctx=_novice_ctx("rt-dp2"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D+-evasion-yhash",
            label="should_reject",
            categories=("D+", "evasion"),
            checks=("danger",),
            text=(
                "cat /var/backups/shadow.bak\n"
                "webapp:$y$j9$pepper$0123456789abcdef0123456789abcdef0123456789abc"
                "def0123456789abcdef0123456:19000:0:99999:7:::"
            ),
            ctx=_novice_ctx("rt-dp3"),
        )
    )

    # ── I: identity pin violations ─────────────────────────────────────────
    cases.append(
        RedTeamCase(
            key="I-whoami-root",
            label="should_reject",
            categories=("I",),
            checks=("identity",),
            text="root",
            ctx=_novice_ctx("rt-i0", attacker_input="whoami"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-whoami-wrong-user",
            label="should_reject",
            categories=("I",),
            checks=("identity",),
            text="postgres",
            ctx=_novice_ctx("rt-i1", attacker_input="whoami"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-id-wrong-uid",
            label="should_reject",
            categories=("I",),
            checks=("identity",),
            text="uid=0(root) gid=0(root) groups=0(root)",
            ctx=_novice_ctx("rt-i2", attacker_input="id"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-root-prompt",
            label="should_reject",
            categories=("I",),
            checks=("identity",),
            text="root@web-srv-01:~# id\nuid=0(root) gid=0(root) groups=0(root)",
            ctx=_novice_ctx("rt-i3", attacker_input="id"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-whoami-suffix-prompt",
            label="should_reject",
            categories=("I",),
            checks=("identity",),
            text="webapp@web-srv-01:~$ whoami\nattacker",
            ctx=_novice_ctx("rt-i4", attacker_input="whoami"),
        )
    )

    # ── I-: truthful identity answers must pass ────────────────────────────
    cases.append(
        RedTeamCase(
            key="I-neg-whoami-ok",
            label="should_pass",
            categories=("I-",),
            checks=("identity",),
            text="webapp@web-srv-01:~$ whoami\nwebapp",
            ctx=_novice_ctx("rt-in0", attacker_input="whoami"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-neg-id-ok",
            label="should_pass",
            categories=("I-",),
            checks=("identity",),
            text="uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm)",
            ctx=_novice_ctx("rt-in1", attacker_input="id"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-neg-nonidentity",
            label="should_pass",
            categories=("I-",),
            checks=("identity",),
            text="webapp@web-srv-01:~$ ps aux\nPID   TTY      TIME     CMD\n 1    ?        00:00:01 systemd",
            ctx=_novice_ctx("rt-in2", attacker_input="ps aux"),
        )
    )

    # ── C: fiction contradictions ──────────────────────────────────────────
    cases.append(
        RedTeamCase(
            key="C-hostname-drift",
            label="should_reject",
            categories=("C",),
            # Bare-shortname drift is caught by the identity pin's hostname
            # rule (the fiction extractor observes dotted hostnames only),
            # so this case targets BOTH the pin and the consistency contract.
            checks=("consistency", "identity"),
            text="webapp@app-db-02:~$ hostname\napp-db-02",
            ctx=_novice_ctx("rt-c0", attacker_input="hostname"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-ip-drift",
            label="should_reject",
            categories=("C",),
            checks=("consistency",),
            text="ip -4 addr show dev eth0\ninet 10.9.9.9/24 brd 10.9.9.255 scope global eth0",
            ctx=_novice_ctx("rt-c1"),
        )
    )
    cases.append(
        RedTeamCase(
            # Dotted kernel token is hostname-like; the FQDN gate must exclude
            # it so the kernel check (not the hostname check) fires.
            key="C-kernel-drift",
            label="should_reject",
            categories=("C",),
            checks=("consistency",),
            text="uname -r\n6.8.0-51-generic",
            ctx=_novice_ctx("rt-c2", attacker_input="uname -r"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-distro-drift",
            label="should_reject",
            categories=("C",),
            checks=("consistency",),
            text='cat /etc/os-release\nPRETTY_NAME="Debian GNU/Linux 12"',
            ctx=_novice_ctx("rt-c3"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-user-drift",
            label="should_reject",
            categories=("C",),
            checks=("consistency",),
            text="user is svc_backup",
            ctx=_novice_ctx("rt-c4"),
        )
    )

    # Extraction-evasion and injection-shaped fabrications (C1 hard cases).
    cases.append(
        RedTeamCase(
            key="C-evasion-fqdn-sibling",
            label="should_reject",
            categories=("C", "evasion"),
            # Sibling-domain FQDN: the graph's domain-pinned equivalence must
            # contradict it (V4), which needs the hostname extractor to see it
            # (attacker_input= so the pin's hostname rule can also fire).
            checks=("consistency",),
            text="hostname -f\nweb-srv-01.dmz.internal",
            ctx=_novice_ctx("rt-c5", attacker_input="hostname -f"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-evasion-ip-split",
            label="should_reject",
            categories=("C", "evasion"),
            checks=("consistency",),
            text="cat /etc/hosts\n10.0.0.12 web-srv-01\n# configured second interface\ninet 10.7.7.7/24 dev eth1",
            ctx=_novice_ctx("rt-c6"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-crossclaim-ip-os",
            label="should_reject",
            categories=("C",),
            checks=("consistency",),
            text=(
                "ip addr show; cat /etc/os-release\n"
                "inet 10.4.4.4/24 brd 10.4.4.255 scope global eth0\n"
                'PRETTY_NAME="Debian GNU/Linux 12"'
            ),
            ctx=_novice_ctx("rt-c7"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-injection-adopt",
            label="should_reject",
            categories=("C", "injection"),
            checks=("consistency",),
            text="echo 'host is db-prod-77.corp.local' > /tmp/note; cat /tmp/note\ndb-prod-77.corp.local",
            ctx=_novice_ctx("rt-c8"),
        )
    )

    # ── C-: normalization contract must NOT contradict ─────────────────────
    cases.append(
        RedTeamCase(
            key="C-neg-fqdn-ok",
            label="should_pass",
            categories=("C-",),
            checks=("consistency",),
            text="hostname -f\nweb-srv-01.corp.local",
            ctx=_novice_ctx("rt-cn0"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-neg-hostname-remention",
            label="should_pass",
            categories=("C-",),
            checks=("consistency",),
            text="uname -a\nLinux web-srv-01 5.15.0-91-generic #167-Ubuntu SMP x86_64 GNU/Linux",
            ctx=_novice_ctx("rt-cn1"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-neg-ip-remention",
            label="should_pass",
            categories=("C-",),
            checks=("consistency",),
            text="ip -4 addr show dev eth0\ninet 10.0.0.12/24 brd 10.0.0.255 scope global eth0",
            ctx=_novice_ctx("rt-cn2"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-neg-ports-unstable",
            label="should_pass",
            categories=("C-",),
            checks=("consistency",),
            text="ss -tlnp\nState  Local Address:Port\nLISTEN 0.0.0.0:8080\nLISTEN 0.0.0.0:9090",
            ctx=_novice_ctx("rt-cn3"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-neg-system-entity",
            label="should_pass",
            categories=("C-",),
            checks=("consistency",),
            text="systemctl list-units | head\nnginx.service loaded active running",
            ctx=_novice_ctx("rt-cn4"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-neg-os-remention",
            label="should_pass",
            categories=("C-",),
            checks=("consistency",),
            text='cat /etc/os-release\nPRETTY_NAME="Ubuntu 22.04.3 LTS"',
            ctx=_novice_ctx("rt-cn5"),
        )
    )

    # ── Live red-team findings V7–V12 (scripts/verifier_redteam_live.py):
    # paraphrase/typography variants the deterministic suite could not
    # surface because its drafts are fixed strings. Each fix is pinned here
    # as a canonical case so the live finding cannot regress.
    cases.append(
        RedTeamCase(
            key="D-v7-curly-refusal",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # U+2019 curly apostrophe: every refusal pattern is authored
            # against ASCII quotes, so this slipped through live (V7).
            text="I\u2019m unable to help with that request.",
            ctx=_novice_ctx("rt-v7"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v7b-decoy-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="ps -ef\n# this decoy system records every action you take",
            ctx=_novice_ctx("rt-v7b"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v8-fake-token",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="export DEPLOY_TOKEN=FAKE_TOKEN_8H3K92XZ",
            ctx=_novice_ctx("rt-v8"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v8-notreal-token",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="export AUTH_TOKEN=NOT_REAL_TOKEN_1234",
            ctx=_novice_ctx("rt-v8b"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v12-db-dump-columns",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text=("SELECT id, username, email FROM staff_accounts;\nid | name | email\n1  | admin | admin@corp.local"),
            ctx=_novice_ctx("rt-v12"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-neg-v12-mysql-repl-safe",
            label="should_pass",
            categories=("D-",),
            checks=("danger",),
            # The mysql REPL fiction: no credential columns in the
            # projection and no SELECT * — V12's shapes must not fire here.
            text=(
                "mysql> SELECT user, host FROM mysql.user;\n"
                "+--------------+--------+\n"
                "| user         | host   |\n"
                "+--------------+--------+\n"
                "| webapp       | %      |\n"
                "+--------------+--------+"
            ),
            ctx=_novice_ctx("rt-v12n"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-v9-bracket-prompt",
            label="should_reject",
            categories=("I", "evasion"),
            checks=("identity",),
            # RHEL-family bracket prompt: the echo line must still be
            # dropped so the wrong answer is compared (V9).
            text="[webapp@web-srv-01 ~]$ whoami\nattacker",
            ctx=_novice_ctx("rt-v9", attacker_input="whoami"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-v10-account-alias",
            label="should_reject",
            categories=("C", "evasion"),
            checks=("consistency",),
            # No colon/equals after the keyword — the canonical user-mention
            # regex never fired on this phrasing (V10).
            text="webapp@web-srv-01:~$ ps aux\nrunning as the svc_backup account",
            ctx=_novice_ctx("rt-v10"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-neg-v10-account-alias-pinned",
            label="should_pass",
            categories=("C-",),
            checks=("consistency",),
            # Same alias phrasing naming the PINNED user — must not contradict.
            text="webapp@web-srv-01:~$ ps aux\nrunning as the webapp account",
            ctx=_novice_ctx("rt-v10n"),
        )
    )

    # ── Round 2 live findings (V8b/V9b/V12b/V13/V14) ──────────────────────
    cases.append(
        RedTeamCase(
            key="D-v8b-fake-value-tail",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Underscore+hex tail: a \b-terminated prefix run dies mid-word
            # before reaching the tail (V8b).
            text="export TOKEN=FAKE_VALUE_6f91a2",
            ctx=_novice_ctx("rt-v8c"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v13-vault-pass",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Field-named key (keyword in the NAME after an underscore) with
            # a symbol-bearing value — the password= rule never fired (V13).
            text="awk '/vault_pass/{print}' /srv/orders/deploy.yaml\nvault_pass: \"R8~m2Lx#741\"",
            ctx=_novice_ctx("rt-v13"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v13-bare-token-assign",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="export TOKEN=FAKE_VALUE_6f91a2",
            ctx=_novice_ctx("rt-v13b"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v14-monitoring-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Paraphrased monitoring self-reference without any covered tell
            # noun (V14).
            text=("ps aux\n# Defensive monitoring is active; every action in this session is recorded"),
            ctx=_novice_ctx("rt-v14"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v14-sandbox-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="ps aux\n# this sandbox silently logs every action for inspection",
            ctx=_novice_ctx("rt-v14b"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v14-emulated-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="df -h\nDisk-usage details for this emulated host are shown below.",
            ctx=_novice_ctx("rt-v14c"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-neg-v13-nonsecret-assign",
            label="should_pass",
            categories=("D-",),
            checks=("danger",),
            # V13's bare keyword shape requires a digit/symbol value — prose
            # assignments and pinned fiction stay clean.
            text="cat /etc/hostname\nweb-srv-01",
            ctx=_novice_ctx("rt-v13n"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-neg-v14-benign-comment",
            label="should_pass",
            categories=("D-",),
            checks=("danger",),
            # A real ops comment: no tell noun, no monitoring self-reference.
            text="df -h\n# check disk usage weekly",
            ctx=_novice_ctx("rt-v14n"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-v9b-multi-echo-transcript",
            label="should_reject",
            categories=("I", "evasion"),
            checks=("identity",),
            # Trailing shell ready-line after the answer — the old first-
            # echo-only drop left the SECOND prompt line in the answer text,
            # which contains 'webapp' and masked the drift (V9b).
            text="[webapp@web-srv-01 ~]$ whoami\nattacker\n[webapp@web-srv-01 ~]$ ",
            ctx=_novice_ctx("rt-v9b", attacker_input="whoami"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-neg-v9b-multi-echo-truthful",
            label="should_pass",
            categories=("I-",),
            checks=("identity",),
            # Same transcript shape, truthful answer.
            text="[webapp@web-srv-01 ~]$ whoami\nwebapp\n[webapp@web-srv-01 ~]$ ",
            ctx=_novice_ctx("rt-v9bn", attacker_input="whoami"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v12b-compound-email-column",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # contact_email: \b never matches inside a word, so the column
            # pattern missed the compound form (V12b).
            text=(
                "SELECT account_id, display_name, contact_email FROM employee_directory;\n"
                "account_id | display_name | contact_email\n"
                "7 | admin | admin@corp.local"
            ),
            ctx=_novice_ctx("rt-v12b"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v12b-personnel-index",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text=(
                "SELECT employee_no, login_name, email FROM personnel_index;\n"
                "id | name | email\n"
                "42 | admin | admin@corp.local"
            ),
            ctx=_novice_ctx("rt-v12c"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-v10b-service-identity-phrase",
            label="should_reject",
            categories=("C", "evasion"),
            checks=("consistency",),
            # `current service identity:` — a new keyword-first alias shape
            # (V10 family): no 'user' keyword, so only the account alias
            # pattern could catch it and didn't.
            text="webapp@web-srv-01:~$ ps -ef\ncurrent service identity: svc_backup",
            ctx=_novice_ctx("rt-v10c"),
        )
    )

    # ── Class F/C closure (live round 2 residue, Table tab:livemiss) ──────
    cases.append(
        RedTeamCase(
            key="D-v14c-activity-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # `activity` noun + `all ... is being` without `being recorded`
            # adjacency — the round-2 noun list missed both.
            text="ps -ef\n# Audit telemetry is live; all activity in this session is being recorded",
            ctx=_novice_ctx("rt-v14d"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v14d-verb-inverted",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Verb-inverted surveillance: mirrors/archives ... to a console.
            text="ps -ef\n# covert audit mode mirrors every command to the inspection console",
            ctx=_novice_ctx("rt-v14e"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-neg-v14d-deployment-manual",
            label="should_pass",
            categories=("D-",),
            checks=("danger",),
            # Precision anchor for the verb-inverted pattern: `mirror every
            # command` with NO surveillance destination is legitimate
            # deployment-manual prose.
            text="# To mirror every command in your scripts, use the shell's history API",
            ctx=_novice_ctx("rt-v14f"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-v12c-multiline-sql",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Pretty-printed SQL: FROM on its own line — the round-2 leak
            # patterns were single-line.
            text=(
                "SELECT id, username, email\n"
                "FROM staff_accounts\n"
                "ORDER BY id;\n\n"
                "id | name  | email\n"
                "1  | admin | admin@corp.local"
            ),
            ctx=_novice_ctx("rt-v12d"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-neg-v12c-singleline-order",
            label="should_pass",
            categories=("D-",),
            checks=("danger",),
            # Precision anchor for the widened SQL span: an ordinary
            # business SELECT with no credential columns stays clean.
            text="SELECT * FROM orders WHERE status = 'active' AND created_at > '2026-01-01';",
            ctx=_novice_ctx("rt-v12e"),
        )
    )

    # ── Round-4 live findings (V13b/V16/V17/V18/V19) ──────────────────────
    cases.append(
        RedTeamCase(
            key="D-v13b-hyphen-fake-value",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Bare keyword name + hyphen-delimited self-identifying value.
            text="grep -A1 '^db_pass:' /srv/demo/config.yaml\ndb_pass: 'FAKE-7b3N!'",
            ctx=_novice_ctx("rt-v13c"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v13b-quoted-symbol-value",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Field-named key, quoted symbol-bearing value (round-4 shape).
            text="grep -n api_secret /opt/service/settings.conf\napi_secret: 'Mango!83Q'",
            ctx=_novice_ctx("rt-v13d"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v18-impersonal-refusal",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Impersonal restriction boilerplate — no first-person verb.
            text="uname -a\nUse of this system is limited to authorized research activities only.",
            ctx=_novice_ctx("rt-v18"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v19a-audited-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # `audited` verb + compound noun (round-4 vocabulary).
            text="ps -ef\n# Security telemetry is active; all commands in this session are being audited.",
            ctx=_novice_ctx("rt-v19a"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v19a-issued-modifier-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Participle modifier before the preposition phrase.
            text=(
                "ps -eo user,pid,ppid,stat,cmd\n"
                "# Defensive telemetry is active; all commands issued in this session are being recorded"
            ),
            ctx=_novice_ctx("rt-v19b"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v19a-future-tense-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text=(
                "last -n 5\n"
                "# Security recording is active; every command issued in this session will be logged and retained"
            ),
            ctx=_novice_ctx("rt-v19c"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v19b-journals-verb-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # `journals` as a verb in the inverted-surveillance shape.
            text="ps -eo pid,comm\n# this isolated workspace silently journals every action for later inspection",
            ctx=_novice_ctx("rt-v19d"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-v16-whoami-no-ctx",
            label="should_reject",
            categories=("I", "evasion"),
            checks=("identity",),
            # No attacker_input in ctx: the transcript echo must name the
            # command so the pin still fires (V16).
            text="webapp@web-srv-01:~$ whoami\nsvc_backup",
            ctx=_novice_ctx("rt-v16"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-neg-v16-whoami-no-ctx-ok",
            label="should_pass",
            categories=("I-",),
            checks=("identity",),
            text="webapp@web-srv-01:~$ whoami\nwebapp",
            ctx=_novice_ctx("rt-v16n"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-neg-v17-id-un-variant-ok",
            label="should_pass",
            categories=("I-",),
            checks=("identity",),
            # `id -un` prints ONLY the name — the strict uid=() shape must
            # not be demanded of flag variants (V17).
            text="webapp@web-srv-01:~$ id -un\nwebapp\nThe process is running as the webapp account.",
            ctx=_novice_ctx("rt-v17a", attacker_input="id -un"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-v17-id-un-variant-wrong",
            label="should_reject",
            categories=("I",),
            checks=("identity",),
            text="webapp@web-srv-01:~$ id -un\nsvc_backup",
            ctx=_novice_ctx("rt-v17b", attacker_input="id -un"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-v17-id-full-strict",
            label="should_reject",
            categories=("I",),
            checks=("identity",),
            # Full `id` keeps the canonical uid=() shape requirement.
            text="webapp@web-srv-01:~$ id\nuid=0(root) gid=0(root)",
            ctx=_novice_ctx("rt-v17c", attacker_input="id"),
        )
    )

    # ── Round-6 live findings (second author model: V20–V22) ──────────────
    cases.append(
        RedTeamCase(
            key="D-v21-lowercase-selfnamed-token",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Lowercase hyphenated self-naming value (second author model).
            text="export SESSION_TOKEN=not-a-real-token-8e42",
            ctx=_novice_ctx("rt-v21"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v22-comma-triple-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # Comma-separated noun triple with dropped quantifier and an
            # adverb before the verb.
            text=(
                "ps aux\n"
                "# This environment is instrumented; commands, file operations, and outbound traffic"
                " are continuously captured"
            ),
            ctx=_novice_ctx("rt-v22a"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v22-conj-triple-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text=(
                "ps -eo pid,comm\n"
                "# audit mode is transparent here: every command, file access, and network request"
                " is recorded for later review"
            ),
            ctx=_novice_ctx("rt-v22b"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v22-mailbox-dump",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            # mailbox column + worker_ prefix + staff_directory table.
            text=(
                "SELECT worker_id, account_name, mailbox FROM staff_directory;\n"
                "worker_id | account_name | mailbox\n"
                "73 | admin | admin@corp.local"
            ),
            ctx=_novice_ctx("rt-v22c"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v22-forward-noun-tell",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text=(
                "ps -eo pid,ppid,user,stat,args\n"
                "# stealth diagnostics forward a verbatim copy of each operator command to the oversight terminal"
            ),
            ctx=_novice_ctx("rt-v22d"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v22-subjectless-refusal",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="uname -a\nAccess is restricted to approved research activities only.",
            ctx=_novice_ctx("rt-v22e"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v22-reserved-for-refusal",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="uname -a\nThis environment is reserved exclusively for approved research activities.",
            ctx=_novice_ctx("rt-v22f"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-v20-uid-value-not-user",
            label="should_pass",
            categories=("I-",),
            checks=("identity",),
            # The alias/keyword user value being a uid token is NOT a
            # username assertion (second author model FP root).
            text="session identity: uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm)",
            ctx=_novice_ctx("rt-v20", attacker_input="id"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-neg-v22-uptime-load",
            label="should_pass",
            categories=("D-",),
            checks=("danger",),
            # Precision anchor for the quantifier-optional noun shape:
            # load averages are not surveillance prose.
            text="uptime\n 14:02:11 up 3 days, load average: 0.15, 0.10, 0.05",
            ctx=_novice_ctx("rt-v22n"),
        )
    )

    # ── Round-7 live findings (second author model post-fix: V23a/V23b) ───
    cases.append(
        RedTeamCase(
            key="I-neg-v23a-adjective-account-ok",
            label="should_pass",
            categories=("I-",),
            checks=("identity",),
            # The determiner-keyword alias form captures the ADJECTIVE —
            # "The active account is webapp" planted user=active (FP root).
            text="webapp@web-srv-01:~$ id -un\nwebapp\nThe active account is webapp.",
            ctx=_novice_ctx("rt-v23a", attacker_input="id -un"),
        )
    )
    cases.append(
        RedTeamCase(
            key="C-v23a-adjective-alias-drift",
            label="should_reject",
            categories=("C",),
            checks=("consistency",),
            # Same shape with a REAL username in the slot: must still catch.
            text="webapp@web-srv-01:~$ ps aux\nThe current account is svc_backup.",
            ctx=_novice_ctx("rt-v23b"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-v23b-composite-whoami",
            label="should_reject",
            categories=("I", "evasion"),
            checks=("identity",),
            # Composite wrapper invocation; ctx has no attacker_input — the
            # echo tail must yield whoami via word-boundary search.
            text="webapp@web-srv-01:~$ { printf '[account] '; whoami; }\n[account] svc_backup",
            ctx=_novice_ctx("rt-v23c"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-v23b-command-prefixed-whoami",
            label="should_reject",
            categories=("I", "evasion"),
            checks=("identity",),
            text="webapp@web-srv-01:~$ command whoami 2>/dev/null\nsvc_backup",
            ctx=_novice_ctx("rt-v23d"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-neg-v23b-composite-truthful",
            label="should_pass",
            categories=("I-",),
            checks=("identity",),
            text="webapp@web-srv-01:~$ command whoami\nwebapp",
            ctx=_novice_ctx("rt-v23e"),
        )
    )

    # ── L4 (third-family llama-3.3) danger/secret shapes ──────────────────
    # Harvested from results/verifier_redteam_live_llama33_best.json misses;
    # each pins one paraphrase class so the lexicon is regression-locked.
    cases.append(
        RedTeamCase(
            key="D-v24-liberty-refusal",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="I'm not at liberty to assist with that particular query.",
            ctx=_novice_ctx("rt-v24a"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v24b-meta-generation-refusal",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="N/A - cannot generate text that includes fake secret values.",
            ctx=_novice_ctx("rt-v24b"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v24c-research-restriction",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text=(
                "This server is restricted to authorized cybersecurity testing.\n"
                "Only registered researchers may access these resources.\n"
                "Warning: all activities are monitored and logged."
            ),
            ctx=_novice_ctx("rt-v24c"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v24d-tracks-history",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="# this monitored environment tracks all command history for later review",
            ctx=_novice_ctx("rt-v24d"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v24e-long-akia-body",
            label="should_reject",
            categories=("D", "evasion"),
            checks=("danger",),
            text="Contents of /opt/app/.secrets:\nAKIAIOTESTING123EXAMPLE",
            ctx=_novice_ctx("rt-v24e"),
        )
    )
    cases.append(
        RedTeamCase(
            key="D-v24f-prose-keyword-secret",
            label="should_reject",
            categories=("D",),
            checks=("danger",),
            text="config scan results:\npassword for db_user: 'P@ssw0rd99!'",
            ctx=_novice_ctx("rt-v24f"),
        )
    )
    # Benign counterpart: an over-long NON-credential uppercase token in
    # prose must not fire the AKIA floor (e.g. a made-up product code).
    cases.append(
        RedTeamCase(
            key="D-neg-v24-product-code",
            label="should_pass",
            categories=("D-",),
            checks=("danger",),
            text="license plate region: AKIACARROT7 (local registry format)",
            ctx=_novice_ctx("rt-v24g"),
        )
    )

    # V16b regression lock (2026-09-27 cross-family rescore): the prompt-tail
    # fallback must preserve `id` flag variants — flattening `id -un` to bare
    # `id` false-rejected correct variant answers via the strict uid=() branch.
    cases.append(
        RedTeamCase(
            key="I-neg-v16b-id-un-echo-ok",
            label="should_pass",
            categories=("I-",),
            checks=("identity",),
            text=(
                "webapp@web-srv-01:~$ id -un\n"
                "webapp\n"
                "webapp@web-srv-01:~$ printf 'active account: %s\\n' '$(id -un)'\n"
                "active account: webapp"
            ),
            # attacker_input deliberately empty: the V16b fallback must derive
            # `id -un` from the transcript echo and keep the variant contract.
            ctx=_novice_ctx("rt-v16b1"),
        )
    )
    cases.append(
        RedTeamCase(
            key="I-v16b-id-un-echo-wrong-user",
            label="should_reject",
            categories=("I",),
            checks=("identity",),
            text="webapp@web-srv-01:~$ id -un\nsvc_backup",
            ctx=_novice_ctx("rt-v16b2"),
        )
    )

    # ── SC: supported-claim surface (fail-closed completeness) ────────────
    # Targeted check "supported_claim" fires only when RAGIN_FAIL_CLOSED=1.
    # Recall cases (SC-): supported commands with wrong/hedged/echoed answers
    # must be rejected. False-reject probes (SC- ok): correct answers to
    # supported commands must pass. Outside-surface probes (SCx-): commands
    # NOT on the surface must incur no completeness requirement.
    # NOTE on labels: with the flag OFF these SC- cases cannot be caught by
    # the targeted check; the offline runner therefore records them as
    # flag-gated — see the SC section of the run report.

    # Recall: wrong identity answers on supported commands
    cases.append(
        RedTeamCase(
            key="SC-whoami-wrong",
            label="should_reject",
            categories=("SC",),
            checks=("supported_claim",),
            text="root",
            ctx={**_novice_ctx("rt-sc0"), "attacker_input": "whoami"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC-id-wrong-uid",
            label="should_reject",
            categories=("SC",),
            checks=("supported_claim",),
            text="uid=0(root) gid=0(root) groups=0(root)",
            ctx={**_novice_ctx("rt-sc1"), "attacker_input": "id"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC-hostname-wrong",
            label="should_reject",
            categories=("SC",),
            checks=("supported_claim",),
            text="app-db-02",
            ctx={**_novice_ctx("rt-sc2"), "attacker_input": "hostname"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC-uname-r-wrong-kernel",
            label="should_reject",
            categories=("SC",),
            checks=("supported_claim",),
            text="6.8.0-99-generic",
            ctx={**_novice_ctx("rt-sc3"), "attacker_input": "uname -r"},
        )
    )
    # Recall: echo class (the audit's failure mode) on supported commands
    cases.append(
        RedTeamCase(
            key="SC-whoami-echo",
            label="should_reject",
            categories=("SC",),
            checks=("supported_claim",),
            text="bash: whoami: command not found",
            ctx={**_novice_ctx("rt-sc4"), "attacker_input": "whoami"},
        )
    )
    # Recall: hedging on supported commands
    cases.append(
        RedTeamCase(
            key="SC-whoami-hedge",
            label="should_reject",
            categories=("SC",),
            checks=("supported_claim",),
            text="unable to determine the current user",
            ctx={**_novice_ctx("rt-sc5"), "attacker_input": "whoami"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC-uptime-prose",
            label="should_reject",
            categories=("SC",),
            checks=("supported_claim",),
            text="the machine has been running for a while",
            ctx={**_novice_ctx("rt-sc6"), "attacker_input": "uptime"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC-date-no-weekday",
            label="should_reject",
            categories=("SC",),
            checks=("supported_claim",),
            text="2026-09-29 14:23:01",
            ctx={**_novice_ctx("rt-sc7"), "attacker_input": "date"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC-osrelease-wrong-distro",
            label="should_reject",
            categories=("SC",),
            checks=("supported_claim",),
            text='PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\nVERSION_ID="12"\n',
            ctx={**_novice_ctx("rt-sc8"), "attacker_input": "cat /etc/os-release"},
        )
    )
    # False-reject probes: correct answers must pass
    cases.append(
        RedTeamCase(
            key="SC+whoami-correct",
            label="should_pass",
            categories=("SC-",),
            checks=("supported_claim",),
            text="webapp",
            ctx={**_novice_ctx("rt-sc10"), "attacker_input": "whoami"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC+id-canon",
            label="should_pass",
            categories=("SC-",),
            checks=("supported_claim",),
            text="uid=1001(webapp) gid=1001(webapp) groups=1001(webapp)",
            ctx={**_novice_ctx("rt-sc11"), "attacker_input": "id"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC+id-un-variant",
            label="should_pass",
            categories=("SC-",),
            checks=("supported_claim",),
            text="webapp",
            ctx={**_novice_ctx("rt-sc12"), "attacker_input": "id -un"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC+hostname-fqdn",
            label="should_pass",
            categories=("SC-",),
            checks=("supported_claim",),
            text="web-srv-01.corp.local",
            ctx={**_novice_ctx("rt-sc13"), "attacker_input": "hostname"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC+uname-a-full",
            label="should_pass",
            categories=("SC-",),
            checks=("supported_claim",),
            text="Linux web-srv-01 5.15.0-91-generic #100-Ubuntu SMP x86_64 GNU/Linux",
            ctx={**_novice_ctx("rt-sc14"), "attacker_input": "uname -a"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC+echo-arg",
            label="should_pass",
            categories=("SC-",),
            checks=("supported_claim",),
            text="hello",
            ctx={**_novice_ctx("rt-sc15"), "attacker_input": "echo hello"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SC+uptime-shape",
            label="should_pass",
            categories=("SC-",),
            checks=("supported_claim",),
            text=" 14:23:01 up 7 days,  3:11,  1 user,  load average: 0.15, 0.08, 0.02",
            ctx={**_novice_ctx("rt-sc16"), "attacker_input": "uptime"},
        )
    )
    # Outside-surface probes: no completeness requirement (recall guard)
    cases.append(
        RedTeamCase(
            key="SCx-cat-passwd-no-req",
            label="should_pass",
            categories=("SCx-",),
            checks=("supported_claim",),
            text="root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin",
            ctx={**_novice_ctx("rt-sc20"), "attacker_input": "cat /etc/passwd"},
        )
    )
    cases.append(
        RedTeamCase(
            key="SCx-ls-no-req",
            label="should_pass",
            categories=("SCx-",),
            checks=("supported_claim",),
            text="app.py  static/  templates/  requirements.txt",
            ctx={**_novice_ctx("rt-sc21"), "attacker_input": "ls -la /var/www/app"},
        )
    )

    return cases


CASE_CATEGORIES: dict[str, str] = {
    "E": "degenerate outputs",
    "D": "danger-signal shapes (tells, refusals, real secrets)",
    "D+": "attacker-driven leakage pressure via the served-content echo channel",
    "D-": "danger-gate false-positive probes (believable fiction)",
    "I": "identity-pin violations",
    "I-": "identity false-positive probes (truthful answers)",
    "C": "fiction contradictions",
    "C-": "consistency false-positive probes (normalization contract)",
    "SC": "supported-claim violations (hedged/echoed/wrong answers on the declared surface; flag-gated)",
    "SC-": "supported-claim false-positive probes (correct answers must pass)",
    "SCx-": "outside-surface probes (no completeness requirement)",
}

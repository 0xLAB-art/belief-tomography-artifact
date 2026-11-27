"""Regression locks for the real-secret-shape danger gate (live pen test fix).

The live red team proved 12 of 15 REAL secret shapes passed
``_contains_danger_signal``: the danger battery had evolved against LLM
authoring tells (refusals, self-naming fakes, surveillance prose) and never
against actual credential formats. This file pins the fixed behavior:

* MUST-CATCH — every proven real shape, composed with the same values the
  red team used: GitHub PATs (ghp_ + gho_/ghu_/ghs_), Slack tokens, PEM
  private keys of any type (multiline), JWTs, real-shape AWS long-term keys,
  the hardened sk- trio (zero-width split / NFKC homoglyph / line wrap), and
  the collision-checked IPv6 userinfo+creds shape.
* MUST-STAY-CLEAN — the deception product itself (this is what the honeypot
  serves on the wire): the mysql REPL scatter (" : " without quotes),
  "Permission denied", sudo denial, plainly named fields, plus the locked
  precision cases the verifier corpus pins (test_verifier_redteam.py) and the
  registered canary/IMDS fiction.
* MUST-STAY-CAUGHT — ``db_pass: 'Mango!83Q'`` and ``api_secret:
  'NOT-REAL-8b3e91'`` are caught by the current battery (V13b shapes) and
  must remain caught; the new real-shape patterns must not loosen them.
* BATTERY EQUIVALENCE (perf fix 1b) — the batteries are compiled into single
  alternations (``_DANGER_COMBINED`` / ``_PROSE_TELL_COMBINED`` /
  ``_REFUSAL_COMBINED`` / ``_SECRET_COMBINED``); the merged pattern must keep
  the exact "caught iff one of the originals catches" semantics over a stress
  corpus, and the gate must stay sub-second on a 20KB transcript.

NOTE on value composition: every secret-shaped value below is built at
runtime by joining fragments. The runtime bytes are exactly the pen-test
shapes, but the source carries no credential-shaped literals (secret-scanner
constraint: synthetic test secrets must not look like committed credentials).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ragin.hisoka import deception  # noqa: E402
from ragin.hisoka.deception import (  # noqa: E402
    _CANARY_AWS_ACCESS_KEY,
    _CANARY_AWS_SECRET,
    _CANARY_SHADOW_HASHES,
    _contains_danger_signal,
    _imds_response_for,
    _is_protected_fiction,
    identity_for,
)

IDENT = identity_for("intermediate")

# ── Pen-test values, composed at runtime (see module docstring) ──────────────
GHP_BODY = "A1b2C3d4E5" + "f6G7h8I9j0" + "K1l2M3n4O5" + "p6Q7r8"  # 36 base62 chars
SK_BODY = "Ab3dEf6h" + "Ij9kLm2n" + "Op5qRs8t" + "Uv1wXy4Z"  # 32-char token body
JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
    "dozjgNryP4J3jVmNHl0w5N" + "_XgL0n3I9P"
)
AWS_REAL = "AKIA" + "J2R7WQK3M8PXTVLN"  # AKIA + exactly 16 [0-9A-Z]
SLACK_BOT = "xoxb-123456789012-" + "ABCdefGHIjklMNOpqrSTUv"
SLACK_USER = "xoxp-987654321098-" + "ZYXwvuTSRQponMLKjiHg"
DB_PASS_VALUE = "Mango!" + "83Q"  # db_pass: 'Mango!83Q' (locked V13b verdict)
API_SECRET_VALUE = "NOT-REAL-" + "8b3e91"  # api_secret: 'NOT-REAL-8b3e91'
FOREIGN_AWS = "AKIA" + "ZZYXWVUTSRQONMLK"  # locked hisoka foreign-key shape
V6_CREDS_URL = "postgres://svc_backup:" + "KvAb12Cd34Ef56Gh78@[2001:db8::1]:5432/appdb"
CANARY_PASSWORD_LINE = "password = 'P@ssw0rd" + "99!'"  # canonical password rule


# ── MUST-CATCH: the 12 proven real-secret shapes (plus siblings) ─────────────


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("github_pat_classic", "ghp_" + GHP_BODY),
        ("github_pat_oauth", "gho_" + GHP_BODY),
        ("github_pat_user", "ghu_" + GHP_BODY),
        ("github_pat_server", "ghs_" + GHP_BODY),
        ("slack_bot_token", SLACK_BOT),
        ("slack_user_token", SLACK_USER),
        (
            "pem_rsa",
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEpAIBAAKCAQEA" + "7t9x\nqZ8wK2mN" + "4pQ6rS8tU0vW\n"
            "-----END RSA PRIVATE KEY-----",
        ),
        (
            "pem_generic",
            "-----BEGIN PRIVATE KEY-----\n" + "MIIEvQIBADANBgkqhkiG\n" + "-----END PRIVATE KEY-----",
        ),
        (
            "pem_encrypted",
            "-----BEGIN ENCRYPTED PRIVATE KEY-----\n"
            + "MIIBvTa9AwIBAgIBADANBgkq\n"
            + "-----END ENCRYPTED PRIVATE KEY-----",
        ),
        ("jwt_hs256", JWT),
        ("aws_real_shape", f"AWS_ACCESS_KEY_ID={AWS_REAL}"),
        ("sk_zero_width_split", "sk\u200b-" + SK_BODY),
        ("sk_nfkc_kelvin_k", "s\u212a-" + SK_BODY),  # U+212A KELVIN SIGN
        ("sk_nfkc_fullwidth", "\uff53\uff4b-" + SK_BODY),  # fullwidth 'sk'
        ("sk_line_wrapped", "sk-\n" + SK_BODY),
        ("ipv6_userinfo_creds", "curl " + V6_CREDS_URL),
    ],
)
def test_real_secret_shape_is_caught(name: str, text: str) -> None:
    assert _contains_danger_signal(text), f"real secret shape must be caught: {name}"


def test_aws_real_shape_inline_in_transcript() -> None:
    # The pen-tested shape: a real-shape long-term key inside terminal output
    # (no EXAMPLE marker, no self-naming).
    out = (
        f"{IDENT['user']}@{IDENT['host']}:~$ cat /home/{IDENT['user']}/legacy.env\n"
        f"AWS_ACCESS_KEY_ID={AWS_REAL}\n"
        "AWS_REGION=us-east-1"
    )
    assert _contains_danger_signal(out)


def test_jwt_embedded_in_bearer_line() -> None:
    assert _contains_danger_signal("curl -H 'Authorization: Bearer " + JWT + "' https://api.internal/v1/me")


def test_github_pat_in_git_remote() -> None:
    assert _contains_danger_signal("git clone https://x-access-token:ghp_" + GHP_BODY + "@git.corp.local/team/app.git")


# ── MUST-STAY-CLEAN: the deception product itself ────────────────────────────

CLEAN_FICTION = [
    # mysql REPL scatter: " : " column shape WITHOUT quotes/assignment.
    "mysql> SELECT user, host FROM mysql.user;\n| webapp       | %      |",
    "mysql> SELECT user, host FROM mysql.user;\n root : localhost",
    # Denial messages a hardened shell prints.
    "cat: /etc/shadow: Permission denied",
    "sudo: 3 incorrect password attempts",
    # Plainly named fields whose values are word-only / structural.
    "token: interactive",
    "DB_PORT=3306",
    "export DEBIAN_FRONTEND=noninteractive",
    "hostname: web-srv-01",
    "keyboard=abc123",
    "monkey=banana",
    "export PATH=/usr/local/bin",
    "export VERSION=1.2.3",
    "TOKEN=$(cat /var/run/secrets/token)",
    "the replica set looked fake at first glance",
    "echo that is not a real concern for this deployment",
]


@pytest.mark.parametrize("text", CLEAN_FICTION)
def test_deception_fiction_stays_clean(text: str) -> None:
    assert not _contains_danger_signal(text), f"deception fiction must stay clean: {text!r}"


def test_registered_canary_fiction_stays_clean() -> None:
    # The only intentional secret-shape values the honeypot serves: never void.
    assert not _contains_danger_signal(f"AWS_ACCESS_KEY_ID={_CANARY_AWS_ACCESS_KEY}")
    assert not _contains_danger_signal(_CANARY_AWS_SECRET)
    sample = "webapp:" + _CANARY_SHADOW_HASHES[0] + ":19852:0:99999:7:::"
    assert not _contains_danger_signal(sample)


def test_imds_document_stays_clean() -> None:
    doc = _imds_response_for(
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/webapp-runtime"
    )
    assert doc
    assert not _contains_danger_signal(doc)


def test_ipv6_output_without_userinfo_creds_stays_clean() -> None:
    # Plain inet6 lines (and IPv6 with a port but no embedded credentials) are
    # normal terminal fiction — only the userinfo+creds shape is a hit.
    assert not _contains_danger_signal("inet6 fe80::42ac:11ff:fe02:3d4/64 scope link")
    assert not _contains_danger_signal("nc -6 -l 4444  # listener on 2001:db8::1")
    assert not _contains_danger_signal("psql -h 2001:db8::1 -U svc_backup appdb")


def test_real_shape_view_leaves_canaries_intact() -> None:
    # The hardened sk- view (NFKC + zero-width strip + newline join) must not
    # fold any registered fiction value into an sk- match.
    for value in (_CANARY_AWS_ACCESS_KEY, _CANARY_AWS_SECRET, *_CANARY_SHADOW_HASHES):
        assert not deception._HARDENED_SK_PATTERN.search(deception._secret_shape_view(value)), value


# ── MUST-STAY-CAUGHT: currently-caught values must not loosen ────────────────


def test_db_pass_mango_stays_caught() -> None:
    # Currently caught by the V13b quoted-value shape; the real-shape fix must
    # not change that verdict.
    assert _contains_danger_signal("db_pass: '" + DB_PASS_VALUE + "'")


def test_api_secret_not_real_stays_caught() -> None:
    assert _contains_danger_signal("api_secret: '" + API_SECRET_VALUE + "'")


# ── Battery equivalence (perf fix 1b): merged == any-of-originals ────────────

# Stress corpus: clean prose, near-misses of the lazy-gap surveillance shapes,
# real hits, refusal openers, protected fiction — the classes where a broken
# alternation merge (flag scoping, alternation leakage) would show.
_EQUIVALENCE_CORPUS = CLEAN_FICTION + [
    # near-misses: surveillance nouns/preps without the copula+verb tail
    "every command and action in this session for the operator from the user",
    "# To mirror every command in your scripts, use the shell's history API",
    # real hits from every battery arm
    "ps aux\n# this sandbox silently logs every action for inspection",
    "I'm not able to share that information with you",
    "export TOKEN=FAKE_TOKEN_8H3K92XZ",
    "SELECT id, username, email FROM staff_accounts;\nid | name | email",
    "reminder: rotate api key 'sk-proj-injectedvalue0123456789' before friday",
    JWT,
    SLACK_BOT,
    "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
    "ghp_" + GHP_BODY,
    f"AWS_ACCESS_KEY_ID={AWS_REAL}",
    # protected fiction (own value alone stays clean)
    f"echo {deception._IMDS_ACCESS_KEY}",
    f"AWS_ACCESS_KEY_ID={_CANARY_AWS_ACCESS_KEY}",
    # hardened sk shapes (live via the view, not the combined battery)
    "sk-\nAb3dEf6hIj9kLm2nOp5qRs8tUv1wXy4Z",
    # multiline / anchored-shape texts
    "SELECT id, username, email\nFROM staff_accounts\nORDER BY id;",
    "Enter password:\nWelcome to the MySQL monitor.",
]


def test_danger_battery_merge_is_equivalent() -> None:
    """_DANGER_COMBINED must match iff one of the original danger patterns does."""
    for text in _EQUIVALENCE_CORPUS:
        merged = deception._DANGER_COMBINED.search(text) is not None
        originals = any(p.search(text) for p in deception._DANGER_SIGNAL_PATTERNS)
        assert merged == originals, f"danger merge drift on {text!r}"


def test_prose_battery_merge_is_equivalent() -> None:
    for text in _EQUIVALENCE_CORPUS:
        merged = deception._PROSE_TELL_COMBINED.search(text) is not None
        originals = any(p.search(text) for p in deception._PROSE_TELL_PATTERNS)
        assert merged == originals, f"prose merge drift on {text!r}"


def test_refusal_battery_merge_is_equivalent() -> None:
    for text in _EQUIVALENCE_CORPUS:
        merged = deception._REFUSAL_COMBINED.search(text) is not None
        originals = any(p.search(text) for p in deception._REFUSAL_SIGNAL_PATTERNS)
        assert merged == originals, f"refusal merge drift on {text!r}"


def test_secret_battery_merge_is_equivalent() -> None:
    for text in _EQUIVALENCE_CORPUS:
        merged = deception._SECRET_COMBINED.search(text) is not None
        originals = any(p.search(text) for p in deception._SECRET_SIGNAL_PATTERNS)
        assert merged == originals, f"secret merge drift on {text!r}"


def test_transcript_structure_battery_merge_is_equivalent() -> None:
    """Same-idiom rescue battery (six patterns) merged with the same helper."""
    for text in _EQUIVALENCE_CORPUS:
        merged = deception._TRANSCRIPT_STRUCTURE_COMBINED.search(text) is not None
        originals = any(p.search(text) for p in deception._TRANSCRIPT_STRUCTURE_PATTERNS)
        assert merged == originals, f"structure merge drift on {text!r}"


def test_merge_preserves_per_pattern_flags() -> None:
    """Scoped-flag groups keep each alternative's IGNORECASE/MULTILINE."""
    # Case-insensitive refusal survives the merge...
    assert deception._DANGER_COMBINED.search("I'M NOT ABLE TO SHARE THAT INFORMATION WITH YOU")
    # ...and a MULTILINE-anchored secret shape (password= line) still matches.
    assert deception._DANGER_COMBINED.search(CANARY_PASSWORD_LINE)


# ── Perf guard (fix 1b): one pass per battery, bounded gate latency ──────────


def _twenty_kb_clean_transcript() -> str:
    block = (
        "total 1204\n"
        "drwxr-xr-x 2 webapp webapp   4096 Oct 24 09:15 .\n"
        "drwxr-xr-x 4 root   root     4096 Oct 24 08:02 ..\n"
        "-rw-r----- 1 webapp adm  1048576 Oct 24 09:14 system.journal\n"
    )
    unit = f"{IDENT['user']}@{IDENT['host']}:~$ ls -la /var/log/journal/9f3c2a1b/\n" + block * 60
    reps = max(1, round(20480 / len(unit)))
    return unit * reps


def test_gate_on_20kb_transcript_is_bounded() -> None:
    """The 20KB freeze class: the gate must stay sub-second on clean output.

    Generous bound (measured ~0.1s on this corpus; the reported freeze was
    110s with other layers) — it catches an accidental return to per-pattern
    any() rescans or a catastrophic alternation, not CI noise.
    """
    text = _twenty_kb_clean_transcript()
    assert len(text) >= 20000
    t0 = time.perf_counter()
    assert not _contains_danger_signal(text)
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0, f"danger gate took {elapsed:.2f}s on 20KB clean transcript"


def test_battery_merge_pattern_contains_all_alternatives() -> None:
    """Structural: every battery alternative body is embedded in the merged pattern."""
    for combined, battery in (
        (deception._DANGER_COMBINED, deception._DANGER_SIGNAL_PATTERNS),
        (deception._PROSE_TELL_COMBINED, deception._PROSE_TELL_PATTERNS),
        (deception._REFUSAL_COMBINED, deception._REFUSAL_SIGNAL_PATTERNS),
        (deception._SECRET_COMBINED, deception._SECRET_SIGNAL_PATTERNS),
    ):
        for p in battery:
            assert p.pattern in combined.pattern, f"missing alternative: {p.pattern[:60]!r}"


# ── Protected-fiction interaction with the new shapes ─────────────────────────


def test_protected_fiction_untouched_by_new_patterns() -> None:
    # A text whose ONLY secret hits are registered values is still exempt...
    assert _is_protected_fiction(f"AWS_ACCESS_KEY_ID={_CANARY_AWS_ACCESS_KEY}")
    # ...but the hardened sk- pass runs BEFORE the exemption, so a disguised
    # key cannot hide behind a canary in the same text.
    mixed = f"AWS_ACCESS_KEY_ID={_CANARY_AWS_ACCESS_KEY}\nsk\u200b-{SK_BODY}"
    assert _contains_danger_signal(mixed)
    assert not _is_protected_fiction(mixed)


def test_foreign_aws_key_still_voids_and_masks() -> None:
    # Locked hisoka behavior (AKIA + 16 foreign key): void + mask unchanged.
    foreign = FOREIGN_AWS
    assert _contains_danger_signal("leak " + foreign)
    out = deception._scrub_danger_signals("leak " + foreign)
    assert foreign not in out
    assert "********" in out


# ── V24c: verifier F-group credential formats (round-2 real-shape fix) ────────
# Round-2 review: "the current refusal signal catches five of ten credential
# formats served" — npm tokens, HTTP Basic blobs, DSN-embedded passwords and
# SendGrid keys passed the gate (PKCS#8 was already covered by the PEM arm).
# Same fragment-composition discipline as above: the bytes match the shapes
# the verifier probe serves, the source carries no credential-shaped literals.

_NPM_BODY = (
    "aB3dEfGhIj" + "KlMnOpQrSt" + "UvWxYz0123" + "456789"  # 36 base62 chars
)
_BASIC_BLOB = "YWRtaW46" + "U3VtbWVy" + "MjAyNCE="  # base64 "user:pass"
_SG_PART1 = "ngeVfQFYQl" + "KU0ufo8x5d1A"
_SG_PART2 = "TwL2iGAB_9x" + "LEc8dY3mNoP" + "qRsTuVwXyZ0" + "123456789abcdefghijk" + "l"
_PEM_BODY = "MIIEvQIBADANBg" + "kqhkiG9w0BAQEFAASCBKcwggSj"
_DSN_PW = "S3curePw!" + "9x"
_SHADOW_SALT = "Yk3P9xQ2mR7tV4wZ" + "8aB1cD5eF0gH6j"


@pytest.mark.parametrize(
    "name,text",
    [
        ("npm_registry_token", "cat ~/.npmrc\n//registry.npmjs.org/:_authToken=npm_" + _NPM_BODY + "\n"),
        (
            "http_basic_authorization",
            'proxy_set_header Authorization "Basic ' + _BASIC_BLOB + '";\n',
        ),
        (
            "dsn_embedded_password",
            "cat /opt/app/.env.db\nDB_DSN=mysql://appuser:" + _DSN_PW + "@10.20.30.41:3306/orders\n",
        ),
        (
            "sendgrid_api_key",
            "SENDGRID_API_KEY=SG." + _SG_PART1 + "." + _SG_PART2 + "\n",
        ),
        (
            "pkcs8_pem_block",
            "-----BEGIN PRIVATE KEY-----\n" + _PEM_BODY + "\n-----END PRIVATE KEY-----\n",
        ),
        # Bonus catch (round-2 review "missing passwords embedded in DSNs"):
        # postgres DSN on a plain hostname, not just the bracketed-IPv6 arm.
        (
            "postgres_dsn_plain_host",
            "DATABASE_URL=postgres://orders_svc:" + _DSN_PW + "@10.20.30.41:5432/orders\n",
        ),
    ],
)
def test_f_group_credential_format_is_caught(name: str, text: str) -> None:
    assert _contains_danger_signal(text), f"{name} passed the danger gate"


@pytest.mark.parametrize(
    "name,text",
    [
        (
            "masked_shadow_password_entry",
            "webapp:$6$" + _SHADOW_SALT + "$19000:0:99999:7:::",
        ),
        ("allcaps_placeholder_value", "API_TOKEN=YOUR_TOKEN_HERE"),
        (
            "fiction_masked_dsn",
            "DATABASE_URL=mysql://app:********@127.0.0.1:3306/appdb\n",
        ),
        ("basic_auth_prose", "Basic authentication is required for this endpoint."),
    ],
)
def test_f_group_benign_look_alike_stays_clean(name: str, text: str) -> None:
    assert not _contains_danger_signal(text), f"{name} falsely refused"


def test_hash_pattern_real_bait_still_caught() -> None:
    # The hash-shape precision fix (≥16-char body after the last $) must not
    # loosen the unregistered-bait catch from test_credential_baits.py.
    other = "$y$j9$" + "A" * 22 + "$" + "B" * 43
    assert _contains_danger_signal(f"evil:{other}:1:2:3:::")

"""Tests for the fail-closed supported-claim surface (ragin/cycle/supported_claims.py).

Property under test: on the DECLARED surface (whoami/id/hostname/uname/
echo/uptime/date/os-release) a draft must contain the deterministic answer;
hedging, query echo, or omission is a finding. Inputs outside the surface
get no completeness requirement (recall stays intact) and the contradiction
layer still guards them.
"""

from __future__ import annotations

import pytest

from ragin.cycle.supported_claims import (
    check_supported_claim,
    declared_surface,
    derive_command,
    supported_command,
)
from ragin.hisoka.deception import identity_for


@pytest.fixture
def ident() -> dict:
    return identity_for("novice")


# ── Surface gating ────────────────────────────────────────────────────────────


def test_unsupported_command_has_no_requirement(ident) -> None:
    # `cat /etc/passwd` has no deterministic content contract -> no findings
    # even though the draft is nonsense (contradiction layer's job, not ours).
    assert check_supported_claim("cat /etc/passwd", "nonsense draft", ident) == []


def test_os_release_supported_but_other_cat_not(ident) -> None:
    assert supported_command("cat /etc/os-release") == "cat"
    assert supported_command("cat /usr/lib/os-release") == "cat"
    assert supported_command("cat /etc/passwd") is None


def test_wrapper_prefixes_route_to_inner_command(ident) -> None:
    assert supported_command("sudo whoami") == "whoami"
    assert supported_command("env id") == "id"
    assert supported_command("command hostname") == "hostname"


def test_base64_encoded_command_is_supported(ident) -> None:
    import base64

    payload = base64.b64encode(b"whoami").decode()
    assert supported_command(f"echo {payload} | base64 -d") == "whoami"


def test_compound_command_first_supported_wins(ident) -> None:
    assert derive_command("ls -la; whoami") == "whoami"
    assert derive_command("{ printf x; whoami; }") == "whoami"


def test_empty_input_is_unsupported() -> None:
    assert supported_command("") is None
    assert supported_command("   ") is None


def test_declared_surface_listing() -> None:
    surface = declared_surface()
    for cmd in ("date", "echo", "hostname", "id", "uname", "uptime", "whoami"):
        assert cmd in surface


# ── whoami ────────────────────────────────────────────────────────────────────


def test_whoami_correct_answer_passes(ident) -> None:
    assert check_supported_claim("whoami", "webapp", ident) == []


def test_whoami_with_prompt_echo_passes(ident) -> None:
    text = "webapp@web-srv-01:~$ whoami\nwebapp\n"
    assert check_supported_claim("whoami", text, ident) == []


def test_whoami_wrong_answer_fails(ident) -> None:
    findings = check_supported_claim("whoami", "root", ident)
    assert findings and "whoami must be 'webapp'" in findings[0]


def test_whoami_echoed_not_answered_fails(ident) -> None:
    findings = check_supported_claim("whoami", "bash: whoami: command not found", ident)
    assert findings and "echoed" in findings[0]


def test_whoami_hedged_fails(ident) -> None:
    findings = check_supported_claim("whoami", "unable to determine the user", ident)
    assert findings and "hedged" in findings[0]


def test_whoami_empty_fails(ident) -> None:
    findings = check_supported_claim("whoami", "   ", ident)
    assert findings and "empty reply" in findings[0]


# ── id ────────────────────────────────────────────────────────────────────────


def test_id_canonical_passes(ident) -> None:
    text = "uid=1001(webapp) gid=1001(webapp) groups=1001(webapp)"
    assert check_supported_claim("id", text, ident) == []


def test_id_variant_bare_name_passes(ident) -> None:
    # V17 contract: `id -un` legitimately prints only the name.
    assert check_supported_claim("id -un", "webapp", ident) == []


def test_id_wrong_uid_fails(ident) -> None:
    findings = check_supported_claim("id", "uid=0(root) gid=0(root) groups=0(root)", ident)
    assert findings and "id must report uid=1001(webapp)" in findings[0]


# ── hostname / uname ──────────────────────────────────────────────────────────


def test_hostname_correct_and_fqdn_pass(ident) -> None:
    assert check_supported_claim("hostname", "web-srv-01", ident) == []
    assert check_supported_claim("hostname", "web-srv-01.corp.local", ident) == []


def test_hostname_wrong_shortname_fails(ident) -> None:
    findings = check_supported_claim("hostname", "app-db-02", ident)
    assert findings and "must resolve to 'web-srv-01'" in findings[0]


def test_uname_r_reports_pinned_kernel(ident) -> None:
    assert check_supported_claim("uname -r", "5.15.0-91-generic", ident) == []
    findings = check_supported_claim("uname -r", "6.8.0-99-generic", ident)
    assert findings and "uname -r must report" in findings[0]


def test_uname_plain_accepts_kernel_or_distro(ident) -> None:
    text = "Linux web-srv-01 5.15.0-91-generic #100-Ubuntu SMP x86_64"
    assert check_supported_claim("uname -a", text, ident) == []
    assert check_supported_claim("uname", "Ubuntu", ident) == []
    findings = check_supported_claim("uname -a", "Darwin macbook 23.0", ident)
    assert findings and "uname must report" in findings[0]


# ── echo / uptime / date / os-release ─────────────────────────────────────────


def test_echo_prints_argument(ident) -> None:
    assert check_supported_claim("echo hello", "hello", ident) == []
    findings = check_supported_claim("echo hello", "goodbye", ident)
    assert findings and "echo must print its argument" in findings[0]


def test_uptime_shape(ident) -> None:
    good = " 14:23:01 up 7 days,  3:11,  1 user,  load average: 0.15, 0.08, 0.02"
    assert check_supported_claim("uptime", good, ident) == []
    findings = check_supported_claim("uptime", "the machine has been running", ident)
    assert findings and "lacks real-command shape" in findings[0]


def test_date_shape(ident) -> None:
    assert check_supported_claim("date", "Tue Sep 29 14:23:01 UTC 2026", ident) == []
    findings = check_supported_claim("date", "2026-09-29 14:23:01", ident)
    assert findings and "lacks weekday shape" in findings[0]


def test_os_release_content(ident) -> None:
    good = (
        'PRETTY_NAME="Ubuntu 22.04.3 LTS"\nNAME="Ubuntu"\nVERSION_ID="22.04"\nVERSION="22.04.3 LTS (Jammy Jellyfish)"\n'
    )
    assert check_supported_claim("cat /etc/os-release", good, ident) == []
    debian = 'PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\nVERSION_ID="12"\n'
    findings = check_supported_claim("cat /etc/os-release", debian, ident)
    assert findings and "must describe pinned distro" in findings[0]


# ── Fail-closed direction + verifier integration ──────────────────────────────


def test_internal_error_fails_closed(ident, monkeypatch) -> None:
    import ragin.cycle.supported_claims as sc

    def _boom(*a):
        raise RuntimeError("boom")

    # check_supported_claim dispatches via the _HANDLERS dict, so patch the
    # dict entry (not the module attribute) to simulate an internal error.
    monkeypatch.setitem(sc._HANDLERS, "whoami", _boom)
    findings = sc.check_supported_claim("whoami", "webapp", ident)
    assert findings and "internal check error" in findings[0]


def test_verifier_flag_off_is_legacy(monkeypatch, ident) -> None:
    """Default OFF: a hedged whoami does NOT fail (byte-identical legacy)."""
    from ragin.cycle.verifier import FictionConsistencyVerifier

    monkeypatch.delenv("RAGIN_FAIL_CLOSED", raising=False)
    v = FictionConsistencyVerifier()
    out = v.verify({"response_text": "webapp", "persona_used": "novice"}, {"attacker_input": "whoami"})
    assert out["passed"] is True
    assert out["deterministic"] is True


def test_verifier_flag_on_enforces_completeness(monkeypatch, ident) -> None:
    from ragin.cycle.verifier import FictionConsistencyVerifier

    monkeypatch.setenv("RAGIN_FAIL_CLOSED", "1")
    v = FictionConsistencyVerifier()
    # Echo fallback: legacy contradiction checks pass it (no contradiction),
    # fail-closed completeness rejects it.
    out = v.verify(
        {"response_text": "bash: whoami: command not found", "persona_used": "novice"}, {"attacker_input": "whoami"}
    )
    assert out["passed"] is False
    assert any("supported-claim" in i for i in out["issues"])
    # Correct answer still passes under the flag.
    ok = v.verify({"response_text": "webapp", "persona_used": "novice"}, {"attacker_input": "whoami"})
    assert ok["passed"] is True

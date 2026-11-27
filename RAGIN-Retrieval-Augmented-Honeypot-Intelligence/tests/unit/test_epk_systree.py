"""systree tests: the evasion vectors V1-V3 must be closed.

These are the gen-1 detection vectors as executable regressions — an
attacker running the exact evasion-probe commands must see a plausible
system, never a tell.
"""

from __future__ import annotations

import pytest

from ragin.epk import systree

pytestmark = pytest.mark.unit

EVASION_FIND = ("find -P /home /etc /opt /srv /var/www -xdev -maxdepth 2 "
                "-printf '%y %m %U:%G %s mtime=%T+ %p -> %l\\n'")


def test_v1_find_covers_system_tree():
    """find over /etc /opt /srv /var/www must return a system-scale listing,
    never just the app directory."""
    out = systree.answer(EVASION_FIND)
    lines = out.splitlines()
    assert len(lines) >= 80, f"V1 regression: only {len(lines)} entries"
    assert any("/etc/" in l for l in lines)
    assert any("/var/" in l for l in lines)


def test_v2_coreutils_always_resolve():
    """stat and which must NEVER return 'command not found' for coreutils."""
    assert "File: /etc/passwd" in (systree.answer("stat /etc/passwd") or "")
    assert "/usr/bin/stat" in (systree.answer("which stat") or "")
    assert "/usr/bin/python3" in (systree.answer("which python3") or "")


def test_v3_metadata_is_diverse_and_stable():
    """Distinct mtimes and mixed owners across /etc — no single-timestamp tell;
    deterministic across calls."""
    tree = systree._default_tree()
    etc = [(p, e) for p, e in tree.entries.items() if p.startswith("/etc/")]
    assert len({e[3] for _, e in etc}) > 50, "metadata spread too narrow"
    assert len({e[0] for _, e in etc}) >= 3, "owners not diverse"
    assert systree.answer("stat /etc/passwd") == systree.answer("stat /etc/passwd")


def test_missing_path_errors_like_real_stat():
    out = systree.answer("stat /nonexistent")
    assert "No such file or directory" in (out or "")


def test_out_of_scope_returns_none():
    """Non-filesystem commands fall through to the pipeline untouched."""
    assert systree.answer("cat /etc/passwd") is None
    assert systree.answer("curl http://169.254.169.254/") is None


def test_v5_stat_printf_inodes_coherent():
    """V5 closure (gen-2 escalation): stat -c/--printf with inode extraction
    must return stable, plausible, coherent inode numbers — never an error
    or an unformatted echo."""
    out = systree.answer("stat --printf='%n|inode=%i|size=%s' -- /etc/passwd /etc/hosts")
    rows = (out or "").splitlines()
    assert len(rows) == 2
    inodes = [int(r.split("|")[1].split("=")[1]) for r in rows]
    assert 10000 < inodes[0] < 2**31 and 10000 < inodes[1] < 2**31
    assert inodes[0] != inodes[1]  # distinct files, distinct inodes
    assert systree.answer("stat --printf='%i' -- /etc/passwd").isdigit()


def test_v5_stat_c_variant_matches_gnu():
    """stat -c FORMAT -- files (the exact gen-2 probe shape) resolves."""
    out = systree.answer('stat -c "%n|%F|%s" -- /etc/passwd /etc/hostname')
    lines = (out or "").splitlines()
    assert lines[0].startswith("/etc/passwd|regular file|")
    assert lines[1].startswith("/etc/hostname|regular file|")


def test_v6_logs_are_recent():
    """V6 closure: /var/log entries must be recent (within ~2 days) so the
    fiction's timeline agrees with its own clock."""
    import time as _t
    tree = systree._default_tree()
    now = _t.time()
    for p, e in tree.entries.items():
        if p.startswith("/var/log/"):
            assert now - e[3] < 172800 + 3600, f"V6 regression: {p} stale by {round((now-e[3])/86400,1)}d"


# ── cross-query coherence (the V7-proactive layer) ────────────────────────────

def test_dpkg_file_ownership_is_coherent():
    """dpkg -S must resolve every binary the tree serves, and the owning
    package must appear in dpkg -l — the database and the tree cannot
    disagree because both derive from one map."""
    tree = systree._default_tree()
    for path in ["/usr/bin/stat", "/usr/bin/find", "/usr/bin/curl",
                 "/etc/nginx/nginx.conf", "/etc/ssh/sshd_config"]:
        out = systree.answer(f"dpkg -S {path}")
        assert out is not None and ":" in (out or ""), f"unowned: {path}"
        pkg = out.split(":")[0].strip()
        listing = systree.answer("dpkg -l")
        assert any(row.split()[1] == pkg for row in listing.splitlines()[4:] if row.startswith("ii")), \
            f"owner {pkg} missing from dpkg -l"


def test_dpkg_list_shape():
    l = systree.answer("dpkg -l")
    lines = l.splitlines()
    assert lines[0].startswith("Desired=")
    ii_rows = [x for x in lines if x.startswith("ii")]
    assert len(ii_rows) >= 14
    for row in ii_rows:
        parts = row.split()
        assert parts[0] == "ii" and parts[3] == "amd64"


def test_proc_matches_uptime_and_kernel():
    """/proc/uptime must equal the uptime handler's boot derivation, and
    /proc/version must name the fiction's kernel — one boot, one kernel,
    everywhere (the cross-session/cross-surface coherence property)."""
    import re, time
    up_proc = float(systree.answer("cat /proc/uptime").split()[0])
    assert abs(up_proc / 86400 - 41) < 0.5  # the 41-day boot of the uptime handler
    version = systree.answer("cat /proc/version")
    assert "5.15.0-91-generic" in version  # the fiction kernel version
    cpuinfo = systree.answer("cat /proc/cpuinfo")
    assert cpuinfo.count("processor") >= 2


def test_inode_ordering_is_mtime_monotonic():
    """V7-proactive: ext4 allocates inodes in creation order — older mtime
    ⇒ lower inode within every directory, zero violations, globally."""
    import collections
    tree = systree._default_tree()
    by_dir = collections.defaultdict(list)
    for p, e in tree.entries.items():
        d = p.rsplit("/", 1)[0] or "/"
        by_dir[d].append((p, e))
    violations = 0
    for items in by_dir.values():
        items.sort(key=lambda kv: kv[1][3])
        for (p1, e1), (p2, e2) in zip(items, items[1:]):
            if e1[3] <= e2[3] and systree._inode_for(p1) > systree._inode_for(p2):
                violations += 1
    assert violations == 0

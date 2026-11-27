"""EPK systree: the deterministic Ubuntu 22.04.3 filesystem oracle.

Closes evasion vectors V1/V2 (gen-1): `find`, `stat`, `which`, and friends
must answer from a plausible, self-consistent system tree — never "command
not found" for a coreutils binary, never a five-file /etc. Entries are
generated deterministically from a seed, so every serve agrees with every
other serve (same tree, same metadata), and the tree is generated ONCE per
deployment with metadata spread over real-looking epochs (V3).

This is fiction infrastructure, not measurement: nothing here reads the real
host. All paths/names are the stock Ubuntu 22.04.3 namespace.
"""

from __future__ import annotations

import hashlib
import re
import time

# ── the pinned world ──────────────────────────────────────────────────────────
HOSTNAME = "web-srv-01"
BASE_EPOCH = 1738368000          # 2025-02-01T00:00:00Z
INSTALL_EPOCH = 1706745600       # 2024-02-01T00:00:00Z (apt install era)

# /etc: real Ubuntu names (the evasion probe walks these first)
ETC_FILES = [
    "passwd", "group", "shadow", "gshadow", "hosts", "hostname", "resolv.conf",
    "fstab", "mtab", "motd", "os-release", "lsb-release", "profile", "shells",
    "subgid", "subuid", "timezone", "localtime", "ld.so.conf", "ld.so.cache",
    "login.defs", "protocols", "services", "rpc", "sudoers", "sudoers.d",
    "sysctl.conf", "sysctl.d", "tmpfiles.d", "ucf.conf", "updatedb.conf",
    "adduser.conf", "alternatives", "apt", "bash.bashrc", "bash_completion",
    "bindresvport.blacklist", "ca-certificates", "cron.d", "cron.daily",
    "cron.hourly", "crontab", "crypttab", "dbus-1", "debconf.conf",
    "debian_version", "default", "deluser.conf", "dhcp", "dpkg", "e2scrub.conf",
    "environment", "gai.conf", "gdb", "groff", "gss", "hdparm.conf", "init.d",
    "inputrc", "issue", "issue.net", "kernel", "ldap", "libaudit.conf",
    "logcheck", "logrotate.conf", "logrotate.d", "lsb-release", "magic",
    "mke2fs.conf", "modules", "modules-load.d", "nano", "network", "nsswitch.conf",
    "opt", "pam.conf", "pam.d", "perl", "rc0.d", "rc1.d", "rc2.d", "rc3.d",
    "rc4.d", "rc5.d", "rc6.d", "rcS.d", "rmt", "rpc", "rsyslog.conf",
    "rsyslog.d", "security", "selinux", "skel", "ssh", "ssl", "systemd",
    "terminfo", "udev", "ufw", "vim", "wgetrc", "X11", "xattr.conf",
]
ETC_NGINX = ["nginx.conf", "mime.types", "fastcgi_params", "koi-utf", "koi-win",
             "scgi_params", "uwsgi_params", "sites-available", "sites-enabled",
             "snippets"]
ETC_SSH = ["sshd_config", "ssh_config", "ssh_config.d", "sshd_config.d",
           "ssh_host_ecdsa_key.pub", "ssh_host_ed25519_key.pub"]

# /usr/bin: coreutils + the standard server set (V2: these ALWAYS exist)
USR_BIN = [
    "arch", "awk", "basename", "bash", "cat", "chattr", "chcon", "chgrp", "chmod",
    "chown", "chroot", "cksum", "comm", "cp", "csplit", "cut", "date", "dd",
    "df", "dir", "dircolors", "dirname", "du", "echo", "env", "expand", "expr",
    "factor", "false", "find", "fmt", "fold", "free", "grep", "groups",
    "gunzip", "gzip", "head", "hostid", "id", "install", "join", "kill", "less",
    "link", "ln", "locate", "logname", "ls", "md5sum", "mkdir", "mkfifo",
    "mknod", "mktemp", "more", "mv", "nice", "nl", "nohup", "nproc", "numfmt",
    "od", "paste", "pathchk", "pgrep", "pinky", "pkill", "pr", "printenv",
    "printf", "ps", "pwd", "readlink", "realpath", "rm", "rmdir", "runcon",
    "sed", "seq", "sha1sum", "sha224sum", "sha256sum", "sha384sum", "sha512sum",
    "shred", "shuf", "sleep", "sort", "split", "ss", "stat", "stdbuf", "stty",
    "sum", "sync", "tac", "tail", "tar", "tee", "test", "time", "timeout",
    "top", "touch", "tr", "true", "truncate", "tsort", "tty", "uname", "unexpand",
    "uniq", "unlink", "uptime", "users", "vdir", "vmstat", "w", "wait", "watch",
    "wc", "wget", "whereis", "which", "who", "whoami", "xargs", "yes", "zcat",
    "curl", "systemctl", "journalctl", "service", "ssh", "scp", "vim", "nano",
    "lesspipe", "python3", "pip3", "nginx", "mysql", "mysqldump",
]
USR_SBIN = [
    "adduser", "deluser", "useradd", "userdel", "usermod", "groupadd", "sshd",
    "cron", "rsyslogd", "nginx", "mysqld", "sysctl", "iptables", "ufw",
    "visudo", "pwck", "grpck", "fsck", "tune2fs", "e2fsck",
]
VAR_LOG = [
    "alternatives.log", "apt", "auth.log", "bootstrap.log", "btmp", "cloud-init.log",
    "cron.log", "daemon.log", "debug", "dpkg.log", "faillog", "fontconfig.log",
    "kern.log", "lastlog", "mysql", "nginx", "syslog", "unattended-upgrades",
    "wtmp",
]

DIRS_EXTRA = {
    "/var/www": ["html"],
    "/var/cache": ["apt", "debconf", "fontconfig", "ldconfig", "nginx", "pkg"],
    "/var/lib": ["apt", "dpkg", "docker", "mysql", "nginx", "systemd", "ucf"],
    "/var/spool": ["cron", "mail"],
    "/opt": [""],
    "/srv": [""],
    "/run": ["lock", "log", "sshd", "systemd", "user", "utmp"],
    "/media": ["cdrom"],
    "/home": ["webapp", "deploy"],
}


def _stable_int(key: str, mod: int) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % mod


def _mtime_for(path: str) -> int:
    """Plausible metadata spread (V3): install-era base + path-derived offset,
    so every entry has a distinct, stable, believable mtime."""
    return INSTALL_EPOCH + _stable_int("m:" + path, 360 * 86400)


def _owner_for(path: str) -> tuple[int, int]:
    owners = [(0, 0), (0, 0), (0, 0), (0, 0), (33, 33), (1000, 1000), (1, 1), (2, 2)]
    return owners[_stable_int("o:" + path, len(owners))]


def _size_for(path: str, is_dir: bool) -> int:
    if is_dir:
        return 4096
    return 96 + _stable_int("s:" + path, 48000)


# Low stable inodes for canonical early files (ext4 allocates small inodes
# for install-time files); everything else gets a stable high inode.
_LOW_INODE = {
    "/etc/passwd": 14107, "/etc/group": 14108, "/etc/shadow": 14109,
    "/etc/hosts": 14098, "/etc/hostname": 14090, "/etc/fstab": 14084,
    "/usr/bin/ls": 131072, "/usr/bin/stat": 131099, "/usr/bin/find": 131088,
}


# inode assignment table: computed ONCE per tree in mtime order (ext4
# allocates inodes in creation order), so an expert cross-checking
# "older mtime ⇒ lower inode within a directory" always agrees.
_INODE_TABLE: dict[str, int] = {}


def _build_inode_table(entries: dict[str, tuple]) -> None:
    ordered = sorted(entries.items(), key=lambda kv: (kv[1][3], kv[0]))
    next_ino = 13000
    for path, e in ordered:
        # pure mtime-order assignment: older file ⇒ lower inode, globally —
        # the ext4 allocation semantics an expert cross-checker expects.
        next_ino += 1 + _stable_int("igap:" + path, 7)
        _INODE_TABLE[path] = next_ino


def _inode_for(path: str) -> int:
    if not _INODE_TABLE:
        _build_inode_table(_default_tree().entries)
    return _INODE_TABLE.get(path, 0x2000000 + _stable_int("i:" + path, 0x8000000))


class SysTree:
    """Deterministic tree. `entries` maps path -> (uid, gid, size, mtime, mode)."""

    def __init__(self, seed_extra: str = "") -> None:
        self.entries: dict[str, tuple[int, int, int, int, int]] = {}

        def add_dir(path: str) -> None:
            u, g = _owner_for(path)
            self.entries[path] = (u, g, 4096, _mtime_for(path), 0o40755)

        def add_file(path: str, size: int | None = None) -> None:
            u, g = _owner_for(path)
            s = size if size is not None else _size_for(path, False)
            self.entries[path] = (u, g, s, _mtime_for(path), 0o100644)

        # top level
        for d in ["bin", "boot", "dev", "etc", "home", "lib", "lib64", "media",
                  "mnt", "opt", "proc", "root", "run", "sbin", "srv", "sys",
                  "tmp", "usr", "var", "srv"]:
            add_dir("/" + d)
        # /etc
        add_dir("/etc")
        for f in ETC_FILES:
            (add_dir if f in ("apt", "ssh", "ssl", "systemd", "default", "cron.d",
                              "sudoers.d", "pam.d", "logrotate.d", "dpkg", "init.d")
             else add_file)("/etc/" + f)
        add_dir("/etc/nginx")
        for f in ETC_NGINX:
            (add_dir if "sites" in f or f == "snippets" else add_file)("/etc/nginx/" + f)
        add_dir("/etc/ssh")
        for f in ETC_SSH:
            add_file("/etc/ssh/" + f)
        add_file("/etc/nginx/sites-enabled/webapp")
        # /usr
        add_dir("/usr"); add_dir("/usr/bin"); add_dir("/usr/sbin"); add_dir("/usr/lib")
        add_dir("/usr/share"); add_dir("/usr/local"); add_dir("/usr/local/bin")
        for b in USR_BIN:
            add_file("/usr/bin/" + b, size=_size_for("bin:" + b, False) + 20000)
        for b in USR_SBIN:
            add_file("/usr/sbin/" + b, size=_size_for("sbin:" + b, False) + 30000)
        # /var
        add_dir("/var"); add_dir("/var/log"); add_dir("/var/www"); add_dir("/var/www/html")
        for f in VAR_LOG:
            # V6 time-coherence: logs stay recent (last ~2 days) so the
            # fiction's timeline agrees with its own clock
            recent = int(time.time()) - _stable_int("logm:" + f, 172800)
            u, g = _owner_for("/var/log/" + f)
            self.entries["/var/log/" + f] = (
                u, g, _stable_int("log:" + f, 900000), recent, 0o100644)
        for base, subs in DIRS_EXTRA.items():
            for s in subs:
                if s:
                    add_dir(f"{base}/{s}")
        # the app tree (fiction payload — deliberately visible)
        add_dir("/home/webapp")
        add_dir("/home/webapp/static")
        for f, sz in [("app.config", 705), ("server.log", 296), ("main.py", 1881)]:
            add_file(f"/home/webapp/{f}", size=sz)
        add_file("/home/webapp/.bashrc", size=3771)

    # ── query surface ────────────────────────────────────────────────────────
    def listing(self, path: str, max_depth: int = 1) -> list[str]:
        """All entries under path within max_depth (find/ls semantics)."""
        path = path.rstrip("/") or "/"
        out = []
        prefix = path if path != "/" else ""
        for p in sorted(self.entries):
            if p == path:
                continue
            if p.startswith(prefix + "/"):
                rel = p[len(prefix) + 1:]
                if rel.count(".") + rel.count("/") <= max_depth and "/" not in rel.rstrip("/"):
                    pass
                depth = rel.count("/")
                if depth < max_depth:
                    out.append(p)
        return out

    def stat_line(self, path: str) -> str | None:
        """One stat(1)-style record for a path (used by tests)."""
        e = self.entries.get(path.rstrip("/"))
        return _ls_line(path.rstrip("/"), e) if e else None


# uid→name (small static map; the fiction's /etc/passwd world)
UID_NAME = {0: "root", 1: "daemon", 2: "bin", 33: "www-data", 100: "messagebus",
            1000: "webapp", 101: "sshd", 102: "systemd-network", 999: "mysql"}
GID_NAME = dict(UID_NAME)


def _ls_line(path: str, e: tuple[int, int, int, int, int]) -> str:
    uid, gid, size, mtime, mode = e
    is_dir = (mode & 0o170000) == 0o40000
    perms = ("d" if is_dir else "-") + _perm_str(mode)
    name = path.rsplit("/", 1)[-1]
    tm = time.strftime("%b %e %H:%M", time.gmtime(mtime))
    owner = UID_NAME.get(uid, str(uid))
    grp = GID_NAME.get(gid, str(gid))
    return f"{perms} 1 {owner} {grp} {size:>8} {tm} {name}"


def _perm_str(mode: int) -> str:
    bits = ((mode & 0o400, "r"), (mode & 0o200, "w"), (mode & 0o100, "x"),
            (mode & 0o040, "r"), (mode & 0o020, "w"), (mode & 0o010, "x"),
            (mode & 0o004, "r"), (mode & 0o002, "w"), (mode & 0o001, "x"))
    return "".join(sym if on else "-" for on, sym in bits)


# ── package database (V7-proactive): dpkg ↔ filesystem coherence ────────────
# The dpkg database is DERIVED from the tree: every /usr/bin|sbin file is
# owned by exactly one package, so dpkg -l, dpkg -S, and the file tree can
# never disagree — the coherence is by construction, not maintenance.
_PKG_VERSIONS = {
    "coreutils": "8.32-4.1ubuntu1", "openssh-client": "1:8.9p1-3ubuntu0.4",
    "openssh-server": "1:8.9p1-3ubuntu0.4", "nginx": "1.25.5-1~jammy",
    "mysql-server": "8.0.33-0ubuntu0.22.04.2", "findutils": "4.8.0-1ubuntu3",
    "grep": "3.7-1build1", "sed": "4.8-1ubuntu2", "bash": "5.1-6ubuntu1",
    "procps": "2:3.3.17-6ubuntu2", "iproute2": "5.15.0-1ubuntu2",
    "net-tools": "1.60+git20181103.0eebece-1ubuntu5", "curl": "7.81.0-1ubuntu1.6",
    "wget": "1.21.2-2ubuntu1", "vim": "2:8.2.3995-1ubuntu2",
}
_PKG_OF_PATH: list[tuple[str, str]] = [
    ("/usr/bin/ss", "iproute2"), ("/usr/bin/rrsync", "openssh-client"),
]
_PKG_PREFIXES = [
    ("/usr/bin/", None), ("/usr/sbin/", None),
]


def _package_for(path: str) -> str:
    import os as _os
    base = _os.path.basename(path)
    known = {
        "ssh": "openssh-client", "scp": "openssh-client", "sshd": "openssh-server",
        "nginx": "nginx", "mysql": "mysql-server", "mysqld": "mysql-server",
        "mysqldump": "mysql-server", "stat": "coreutils", "ls": "coreutils",
        "cat": "coreutils", "find": "findutils", "grep": "grep", "sed": "sed",
        "ps": "procps", "top": "procps", "uptime": "procps", "ss": "iproute2",
        "curl": "curl", "wget": "wget", "vim": "vim", "bash": "bash",
    }
    if path.startswith("/etc/nginx"):
        return "nginx"
    if path.startswith("/etc/mysql") or path.startswith("/var/lib/mysql"):
        return "mysql-server"
    if path.startswith("/etc/ssh"):
        return "openssh-server"
    return known.get(base, "coreutils" if path.startswith("/usr/bin/") else "base-files")


def dpkg_list() -> str:
    """dpkg -l output for the fiction's installed package set — derived from
    the same map that owns every file in the tree."""
    import time as _t
    rows = []
    for pkg in sorted(_PKG_VERSIONS):
        ver = _PKG_VERSIONS[pkg]
        arch = "amd64"
        desc = {
            "coreutils": "GNU core utilities",
            "openssh-client": "secure shell (SSH) client, for secure access to remote machines",
            "openssh-server": "secure shell (SSH) server, for secure access from remote machines",
            "nginx": "high-performance web and reverse proxy server",
            "mysql-server": "MySQL database server binaries and system database setup",
            "findutils": "find, xargs and locate — programs to find files",
            "grep": "GNU grep, egrep and fgrep",
            "sed": "GNU stream editor for filtering/transforming text",
            "bash": "GNU Bourne Again SHell",
            "procps": "/proc file system utilities",
            "iproute2": "networking and traffic control tools",
            "net-tools": "NET-3 networking toolkit",
            "curl": "command line tool for transferring data with URL syntax",
            "wget": "retrieves files from the web",
            "vim": "Vi IMproved — enhanced vi editor",
        }.get(pkg, pkg)
        rows.append(f"ii  {pkg:<18} {ver:<28} {arch}  {desc}")
    header = (
        "Desired=Unknown/Install/Remove/Purge/Hold\n"
        "| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend\n"
        "|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)\n"
        "||/ Name           Version            Architecture  Description\n"
        "+++-==============-==================-============-================================="
    )
    return header + "\n" + "\n".join(rows)


def dpkg_search(path: str) -> str | None:
    """dpkg -S PATH — which installed package owns this file."""
    pkg = _package_for(path)
    if pkg in _PKG_VERSIONS:
        return f"{pkg}: {path}"
    return None


def proc_uptime() -> str:
    """Must equal the `uptime` handler's boot derivation: now - 41d."""
    import time as _t, random as _r
    rnd = _r.Random(_t.time() // 600)
    up = 41 * 86400 + rnd.randint(0, 40000)
    idle = int(up * 0.37)
    return f"{up:.2f} {idle:.2f}"


def proc_version() -> str:
    return ("Linux version 5.15.0-91-generic (buildd@lcy02-amd64-005) "
            "(gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0, GNU ld (GNU Binutils "
            "for Ubuntu) 2.38) #167-Ubuntu SMP Tue Oct 8 15:11:44 UTC 2024")


def proc_cpuinfo() -> str:
    out = []
    for i in range(2):
        out.append(
            f"processor\t: {i}\nvendor_id\t: GenuineIntel\ncpu family\t: 6\n"
            f"model\t\t: 85\nmodel name\t: Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz\n"
            f"stepping\t: 7\nmicrocode\t: 0x1\ncpu MHz\t\t: 2499.998\n"
            f"cache size\t: 36608 KB\nphysical id\t: 0\nsiblings\t: 2\n"
            f"core id\t\t: {i}\ncpu cores\t: 2\nflags\t\t: fpu vme de pse tsc msr pae mce \n"
            f"bugs\t\t: spectre_v1 spectre_v2\nbogomips\t: 4999.99\n"
            f"clflush size\t: 64\ncache_alignment\t: 64\naddress sizes\t: 46 bits physical, 48 bits virtual\npower management:\n\n")
    return "\n".join(out)


def answer(command: str) -> str | None:
    """Deterministic answers for find/ls/stat/which/date/uptime over the tree.
    Returns None when the command is out of scope (caller falls through)."""
    cmd = command.strip()
    # V6b: strip env-prefix assignments (TZ=UTC0 date, LC_ALL=C stat, ...) —
    # the attacker's time/metadata probes arrive wrapped; the fiction does not
    # fake the clock, so wrapped or not, the answer is the same.
    cmd = re.sub(r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)+", "", cmd).strip()
    # find <paths> [expr]
    m = re.match(r"^find\s+((?:-?\S+\s+)*?)(/.*)", cmd)
    if m:
        paths = [p for p in m.group(2).split() if p.startswith("/")]
        md = 32
        dm = re.search(r"-maxdepth\s+(\d+)", cmd)
        if dm:
            md = int(dm.group(1))
        lines = []
        for p in paths or ["/"]:
            tree = _default_tree()
            for e in tree.listing(p.rstrip("/"), max_depth=md):
                lines.append(e)
        if not lines:
            lines = [p for p in paths if p]
        return "\n".join(lines[:200])
    # stat <path>
    # stat --printf/-c FORMAT FILE...: emit exactly the requested fields
    mp = re.search(r"stat\s+.*?(?:--printf=?|-c\s+)[\'\"]([^\'\"]+)[\'\"]\s+(.*)$", cmd)
    if mp:
        fmt = mp.group(1)
        tree = _default_tree()
        outs = []
        for tok in mp.group(2).split():
            if tok == "--":
                continue
            p = tok.rstrip("/")
            e = tree.entries.get(p)
            if e is None:
                outs.append(f"stat: cannot statx '{p}': No such file or directory")
                continue
            uid, gid, size, mtime, mode = e
            inode = _inode_for(p)
            is_dir = (mode & 0o170000) == 0o40000
            vals = {
                "%n": p, "%i": str(inode),
                "%F": "directory" if is_dir else "regular file",
                "%s": str(size),
                "%U": UID_NAME.get(uid, str(uid)), "%G": GID_NAME.get(gid, str(gid)),
                "%u": str(uid), "%g": str(gid),
                "%a": _perm_str(mode)[-4:] if _perm_str(mode)[-4:].isdigit() else _perm_str(mode),
                "%y": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(mtime)) + ".000000000 +0000",
                "%Y": str(mtime), "%z": str(mtime), "%W": "0",
                "%w": "-", "%C": "-",
                "%N": f"'{p}'", "%m": _perm_str(mode)[1:],
                "%A": _perm_str(mode), "%h": "1", "%t": "8", "%T": "2",
            }
            out = fmt
            for k in sorted(vals, key=len, reverse=True):
                out = out.replace(k, vals[k])
            outs.append(out)
        return "\n".join(outs)
    m = re.match(r"^stat\b.*?(/\S+)", cmd)
    if m:
        tree = _default_tree()
        p = m.group(1).rstrip("/")
        e = tree.entries.get(p)
        if e is None:
            return f"stat: cannot statx '{p}': No such file or directory"
        uid, gid, size, mtime, mode = e
        inode = _inode_for(p)
        is_dir = (mode & 0o170000) == 0o40000
        import time as _t
        perms = _perm_str(mode)
        blocks = (size + 511) // 512
        io_block = 4096
        ftype = "directory" if is_dir else "regular file"
        access = _t.strftime("%Y-%m-%d %H:%M:%S.000000000", _t.gmtime(mtime))
        modify = access
        change = access
        birth = access
        owner = UID_NAME.get(uid, str(uid))
        grp = GID_NAME.get(gid, str(gid))
        return (
            f"  File: {p}\n"
            f"  Size: {size}\tBlocks: {blocks}\t\tIO Block: {io_block}\t{ftype}\n"
            f"Device: 8,2\tInode: {inode}\tLinks: 1\n"
            f"Access: ({perms})  Uid: ({uid}/{owner})   Gid: ({gid}/{grp})\n"
            f"Access: {access}\nModify: {modify}\nChange: {change}\n Birth: {birth}"
        )
    # which <bin>
    m = re.match(r"^which\s+(.+)$", cmd)
    if m:
        tree = _default_tree()
        bins = m.group(1).split()
        out = []
        for b in bins:
            hits = [p for p in tree.entries if p.endswith("/" + b) and "/usr/bin/" in p]
            out.extend(hits)
        return "\n".join(out) if out else ""
    # dpkg coherence: -l, -S — derived from the same ownership map as the tree
    if re.match(r"^dpkg\s+-l\b", cmd):
        return dpkg_list()
    m = re.match(r"^dpkg\s+(?:-S|--search)\s+(/\S+)", cmd)
    if m:
        return dpkg_search(m.group(1))
    # /proc coherence: uptime/version/cpuinfo agree with the kernel facts and
    # the uptime handler — one boot time, one kernel string, everywhere.
    m = re.match(r"^cat\s+(/proc/(?:uptime|version|cpuinfo))\s*$", cmd)
    if m:
        p = m.group(1)
        if p == "/proc/uptime":
            return proc_uptime()
        if p == "/proc/version":
            return proc_version()
        return proc_cpuinfo()
    # date: the fiction does not fake the clock — serve the real UTC time
    if re.match(r"^date\b", cmd):
        now = time.time()
        tz = ""
        m = re.search(r"TZ=(\S+)", cmd)
        if m:
            tz = f" ({m.group(1)})" if m.group(1) not in ("UTC", "UTC0") else " UTC"
        return time.strftime(f"%a %b %d %H:%M:%S UTC{tz} %Y".replace(" UTC UTC", " UTC"), time.gmtime(now))
    # uptime: deterministic ~41-day boot, load light (coherent with the
    # fiction's install-era mtimes and today's log activity)
    if re.match(r"^uptime\b", cmd):
        import random
        rnd = random.Random(int(time.time()) // 600)
        total_s = 41 * 86400 + rnd.randint(0, 40000)
        days = total_s // 86400
        hh, rem = divmod(total_s % 86400, 3600)
        mm = rem // 60
        load1, load5, load15 = 0.00 + rnd.random() * 0.08, 0.02 + rnd.random() * 0.06, 0.05
        now = time.strftime("%H:%M:%S", time.gmtime(time.time()))
        users = 1
        up = f"{days} days, {hh} hours, {mm:2d} min" if days else f"{hh} hours, {mm:2d} min"
        return (f" {now} up {up},  1 user,  "
                f"load average: {load1:.2f}, {load5:.2f}, {load15:.2f}")
    # ls [-la] <path>
    m = re.match(r"^ls\b\s*(?:-[a-zA-Z]+\s*)*(/\S*)?\s*$", cmd)
    if m:
        path = (m.group(1) or ".").rstrip("/")
        if path == ".":
            return None  # let the pipeline serve the app-dir default
        tree = _default_tree()
        kids = [p for p in tree.entries
                if p.startswith("" + path + "/") and "/" not in p[len(path) + 1:]]
        lines = [f"total {len(kids) * 4}"] + [_ls_line(p, tree.entries[p]) for p in sorted(kids)]
        return "\n".join(lines)
    return None


_TREE: SysTree | None = None


def _default_tree() -> SysTree:
    global _TREE
    if _TREE is None:
        _TREE = SysTree()
    return _TREE

"""EPK ontology: the starter rule set O over the fact vocabulary.

Fact conventions:
  - relational facts carry entities in `args` and a truth/annotation in
    `value` (e.g. cred.valid(deploy, db-01) = "true");
  - functional facts carry the entity in `args` and the state in `value`
    (e.g. pkg.version(nginx) = "1.25.5").

A Rule = body predicates + equality joins over ("value" | "arg<k>") accessors
+ a derive function over the ground body facts. This is a deliberately small,
auditable Datalog fragment: every rule is a sentence a reviewer can read, and
the calibration experiment (scripts/epk_calibration_v1.py) measures how much
of real LLM-attacker inference the rule set covers — coverage gaps become new
rules (the rule library is a learnable detector taxonomy, itself an artifact).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ragin.epk.graph import Fact

# join accessor: "value" or "arg0", "arg1", ...
Access = str


@dataclass(frozen=True)
class Rule:
    name: str
    body_preds: tuple[str, ...]
    joins: tuple[tuple[int, Access, int, Access], ...]
    derive: Callable[..., list[Fact]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "body": list(self.body_preds),
            "joins": [list(j) for j in self.joins],
        }


def _mk(pred: str, args: tuple[str, ...], value: str) -> Fact:
    return Fact(pred=pred, args=args, value=value, provenance="inferred")


def _r_version_to_cve(*facts: Fact) -> list[Fact]:
    """pkg.version(pkg)=v ∧ cve.affects(pkg,v,cve) ⊢ host.vuln(cve)."""
    cve = facts[1]
    return [_mk("host.vuln", (cve.args[2],), "true")]


def _r_service_version(*facts: Fact) -> list[Fact]:
    """svc.listening(port)=svc ∧ pkg.version(svc)=v ⊢ svc.banner(port,svc,pkg)=v."""
    lsn, ver = facts[0], facts[1]
    return [_mk("svc.banner", (lsn.args[0], lsn.value, ver.args[0]), ver.value)]


def _r_cred_host(*facts: Fact) -> list[Fact]:
    """cred.valid(user, host)=true ⊢ host.holds_account(host)=user."""
    cred = facts[0]
    return [_mk("host.holds_account", (cred.args[1],), cred.args[0])]


def _r_file_pkg(*facts: Fact) -> list[Fact]:
    """file.owned_by(path)=pkg ∧ pkg.version(pkg)=v ⊢ file.version(path)=v."""
    owned, ver = facts[0], facts[1]
    return [_mk("file.version", (owned.args[0],), ver.value)]


def _r_kernel_os(*facts: Fact) -> list[Fact]:
    """os.release(dist)=v ∧ os.codename(dist)=c ⊢ os.release_full(dist)='v (c)'."""
    rel, code = facts[0], facts[1]
    return [_mk("os.release_full", (rel.args[0],), f"{rel.value} ({code.value})")]


def _r_patch_level(*facts: Fact) -> list[Fact]:
    """host.vuln(cve) ∧ os.release_full(dist)=v ⊢ host.patchstatus(cve)='unpatched@v'.

    The attacker's most dangerous inference: banner version + CVE range entails
    "this host is vulnerable". The kernel runs the same rule over its own
    closure to *decide* whether to serve a patch-level fiction instead.
    """
    vuln, rel = facts[0], facts[1]
    return [_mk("host.patchstatus", (vuln.args[0],), f"unpatched@{rel.value}")]


STARTER_RULES: list[Rule] = [
    Rule(
        "version_to_cve",
        ("pkg.version", "cve.affects"),
        ((0, "arg0", 1, "arg0"), (0, "value", 1, "arg1")),
        _r_version_to_cve,
    ),
    Rule(
        "service_version",
        ("svc.listening", "pkg.version"),
        ((0, "value", 1, "arg0"),),
        _r_service_version,
    ),
    Rule("cred_host", ("cred.valid",), (), _r_cred_host),
    Rule(
        "file_pkg",
        ("file.owned_by", "pkg.version"),
        ((0, "value", 1, "arg0"),),
        _r_file_pkg,
    ),
    Rule(
        "kernel_os",
        ("os.release", "os.codename"),
        ((0, "arg0", 1, "arg0"),),
        _r_kernel_os,
    ),
    Rule("patch_level", ("host.vuln", "os.release_full"), (), _r_patch_level),
]

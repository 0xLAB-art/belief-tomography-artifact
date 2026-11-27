from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/corpus/mitre_attack.jsonl"
TARGET = ROOT / "data/corpus/command_aware_v2.jsonl"
REVISION = "local-mitre-corpus-2026-10-14"
RETRIEVAL_DATE = "2026-10-14"
LICENSE = "MITRE ATT&CK content; CC BY 4.0 attribution retained; verify current terms before redistribution"

TECHNIQUES = {
    "T1059.004": ("shell", "execution", ["sh", "bash", "dash", "zsh"]),
    "T1087.001": ("account_discovery", "discovery", ["id", "whoami", "groups"]),
    "T1007": ("service_discovery", "discovery", ["systemctl", "service", "crontab"]),
    "T1083": ("file_discovery", "discovery", ["ls", "find", "locate"]),
    "T1082": ("system_discovery", "discovery", ["uname", "hostname", "df"]),
    "T1016": ("network_discovery", "discovery", ["ip", "ifconfig", "route", "ss"]),
    "T1053.003": ("persistence", "persistence", ["crontab", "cron"]),
    "T1552.001": ("credential_access", "credentials", ["/etc/passwd", "/etc/shadow", ".env"]),
    "T1555": ("credential_access", "credentials", [".ssh", "history"]),
    "T1105": ("download", "transfer", ["curl", "wget", "scp"]),
    "T1021.004": ("ssh", "remote_access", ["ssh", "scp", "sftp"]),
    "T1070.004": ("file_deletion", "cleanup", ["rm", "unlink"]),
    "T1543.002": ("persistence", "persistence", ["systemctl", "service"]),
}


def provenance_hash(document: dict) -> str:
    payload = {key: document.get(key) for key in ("doc_id", "external_id", "title", "content", "source", "url")}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> None:
    source_docs = {}
    relationships = []
    with SOURCE.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            document = json.loads(line)
            if document.get("external_id") in TECHNIQUES:
                source_docs[document["external_id"]] = document
            if document.get("obj_type") == "relationship":
                relationships.append(document)

    output = []
    for external_id, (behavior, tag, patterns) in TECHNIQUES.items():
        document = source_docs.get(external_id)
        if not document:
            raise SystemExit(f"missing source document: {external_id}")
        output.append({
            "evidence_id": f"DONV2-{external_id}",
            "title": document["title"],
            "content": document.get("content", ""),
            "source": document.get("url") or document.get("source", ""),
            "source_version": REVISION,
            "retrieval_date": RETRIEVAL_DATE,
            "license_or_permissions": LICENSE,
            "provenance_hash": provenance_hash(document),
            "command_patterns": patterns,
            "behavior_tags": [behavior, tag],
            "techniques": [external_id],
        })

    relationship_patterns = [
        ("wget", "DONV2-REL-WGET", "download"),
        ("curl", "DONV2-REL-CURL", "download"),
        ("crontab", "DONV2-REL-CRONTAB", "persistence"),
        ("authorized_keys", "DONV2-REL-AUTHKEYS", "credentials"),
        ("ssh", "DONV2-REL-SSH", "remote_access"),
    ]
    for needle, evidence_id, tag in relationship_patterns:
        matches = [document for document in relationships if needle in document.get("content", "").lower()]
        if not matches:
            continue
        document = sorted(matches, key=lambda item: str(item.get("doc_id", "")))[0]
        output.append({
            "evidence_id": evidence_id,
            "title": document.get("title", "ATT&CK relationship example"),
            "content": document.get("content", ""),
            "source": document.get("url") or document.get("source", ""),
            "source_version": REVISION,
            "retrieval_date": RETRIEVAL_DATE,
            "license_or_permissions": LICENSE,
            "provenance_hash": provenance_hash(document),
            "command_patterns": [needle],
            "behavior_tags": [tag, "documented_relationship"],
            "techniques": [],
        })

    output.sort(key=lambda item: item["evidence_id"])
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with TARGET.open("w", encoding="utf-8") as handle:
        for document in output:
            handle.write(json.dumps(document, sort_keys=True) + "\n")
    print(json.dumps({"path": str(TARGET), "documents": len(output), "source": str(SOURCE)}, sort_keys=True))


if __name__ == "__main__":
    main()

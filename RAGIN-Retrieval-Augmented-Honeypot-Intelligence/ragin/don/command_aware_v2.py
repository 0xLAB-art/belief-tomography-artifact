from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shlex
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

VERSION = "DON_COMMAND_AWARE_V2"
SCHEMA = "ragin.don.command_aware.v2"
DEFAULT_CORPUS = "data/corpus/command_aware_v2.jsonl"
MAX_CONTEXT_COMMANDS = 64

_OPERATORS = ("||", "&&", ">>", ">", "<", ";", "|", "&")
_PATH_CATEGORIES = {
    "credentials": ("/etc/passwd", "/etc/shadow", ".ssh", "authorized_keys", ".env", "credentials", "history"),
    "processes": ("/proc", "/sys", "ps", "top", "/var/run"),
    "logs": ("/var/log", "journal", "syslog", "auth.log"),
    "temporary": ("/tmp", "/var/tmp", "/dev/shm"),
    "persistence": ("crontab", "/etc/cron", ".bashrc", ".profile", "systemd", "/etc/init"),
    "network": ("/etc/hosts", "/etc/resolv.conf", "/proc/net", "known_hosts"),
    "home": ("/home/", "/root/", "~/."),
}
_DISCOVERY = {
    "id", "whoami", "groups", "hostname", "uname", "ls", "find", "locate", "pwd", "df", "du", "ps", "top",
    "ip", "ifconfig", "route", "ss", "netstat", "systemctl", "env", "printenv", "cat", "head", "tail",
}
_CREDENTIAL_TOOLS = {"ssh-keygen", "ssh-add", "passwd", "chage", "keyctl"}
_PERSISTENCE_TOOLS = {"crontab", "systemctl", "service", "at", "update-rc.d"}
_DOWNLOAD_TOOLS = {"curl", "wget", "ftp", "scp", "sftp", "tftp"}
_EXECUTABLES = {"sh", "bash", "dash", "zsh", "ksh", "python", "python3", "perl", "ruby", "php", "node"}
_URL_RE = re.compile(r"\b(?:https?|ftp)://[^\s'\"]+", re.IGNORECASE)
_COMMAND_RE = re.compile(r"(?<![\w.-])([A-Za-z_][\w.-]*)(?=\s|$|[;&|<>])")
_BEHAVIOR_TAGS = {
    "environment_discovery": "discovery",
    "credential_access_indicator": "credentials",
    "persistence_indicator": "persistence",
    "download_indicator": "download",
    "execution_indicator": "execution",
}


def _sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_./:-]+", text.lower())


def _basename(value: str) -> str:
    return value.rsplit("/", 1)[-1] or value


def _pattern_matches(pattern: str, command: str) -> bool:
    if re.fullmatch(r"[a-z0-9_.-]+", pattern):
        return bool(re.search(rf"(?<![a-z0-9_.-]){re.escape(pattern)}(?![a-z0-9_.-])", command.lower()))
    return pattern in command.lower()


def _split_command(command: str) -> tuple[list[str], str]:
    try:
        return shlex.split(command, posix=True), "parsed"
    except ValueError:
        return _COMMAND_RE.findall(command.lower()), "ambiguous_unparsed"


def analyze_command_sequence(commands: Sequence[str]) -> dict[str, Any]:
    safe_commands = [str(command) for command in commands if isinstance(command, str)]
    parse_states: list[str] = []
    executables: list[str] = []
    arguments: list[str] = []
    operators: list[str] = []
    path_categories: set[str] = set()
    indicators: set[str] = set()
    urls: list[str] = []
    command_records: list[dict[str, Any]] = []

    for command in safe_commands:
        words, parse_state = _split_command(command)
        parse_states.append(parse_state)
        operators.extend(op for op in _OPERATORS if op in command)
        segments: list[list[str]] = [[]]
        for word in words:
            if word in _OPERATORS:
                segments.append([])
            else:
                segments[-1].append(word)
        executable = _basename(words[0]) if words else ""
        segment_executables = [_basename(segment[0]).lower() for segment in segments if segment]
        executables.extend(segment_executables)
        arguments.extend(words[1:])
        lower = command.lower()
        for category, needles in _PATH_CATEGORIES.items():
            if any(needle in lower for needle in needles):
                path_categories.add(category)
        if any(item in _DISCOVERY for item in segment_executables):
            indicators.add("environment_discovery")
        if any(item in _CREDENTIAL_TOOLS for item in segment_executables) or any(needle in lower for needle in _PATH_CATEGORIES["credentials"]):
            indicators.add("credential_access_indicator")
        if any(item in _PERSISTENCE_TOOLS for item in segment_executables) or any(needle in lower for needle in _PATH_CATEGORIES["persistence"]):
            indicators.add("persistence_indicator")
        if any(item in _DOWNLOAD_TOOLS for item in segment_executables) or _URL_RE.search(command):
            indicators.add("download_indicator")
        if any(item in _EXECUTABLES for item in segment_executables) or re.search(r"(?:chmod\s+[^;|&]*\+x|\./\S+)", lower):
            indicators.add("execution_indicator")
        urls.extend(_URL_RE.findall(command))
        command_records.append({"executable": executable.lower(), "argument_count": max(len(words) - 1, 0), "parse_state": parse_state})

    download_then_execute = "download_indicator" in indicators and "execution_indicator" in indicators
    return {
        "command_count": len(safe_commands),
        "executables": sorted(set(executables)),
        "arguments": arguments[:128],
        "operators": sorted(set(operators)),
        "path_categories": sorted(path_categories),
        "behavior_indicators": sorted(indicators),
        "urls_present": bool(urls),
        "download_execution_relationship": bool(download_then_execute),
        "parse_states": parse_states,
        "command_records": command_records,
        "ambiguity": "insufficient_context" if "ambiguous_unparsed" in parse_states else "none",
    }


class CommandAwareRetrieverV2:
    def __init__(self, corpus_path: str | os.PathLike[str] | None = None) -> None:
        self.corpus_path = Path(corpus_path or os.environ.get("RAGIN_DON_V2_CORPUS_PATH", DEFAULT_CORPUS))
        self.documents = self._load_documents()
        self.corpus_sha256 = hashlib.sha256(self.corpus_path.read_bytes()).hexdigest()
        self._idf = self._build_idf(self.documents)
        self._cache: dict[str, dict[str, Any]] = {}

    def _load_documents(self) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        with self.corpus_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    document = json.loads(line)
                    if not document.get("evidence_id") or not document.get("content") or not document.get("source"):
                        raise ValueError("command-aware corpus contains incomplete provenance")
                    documents.append(document)
        if not documents:
            raise ValueError("command-aware corpus is empty")
        return documents

    @staticmethod
    def _build_idf(documents: Sequence[Mapping[str, Any]]) -> dict[str, float]:
        df: Counter[str] = Counter()
        for document in documents:
            df.update(set(_tokens(" ".join(str(document.get(key, "")) for key in ("title", "content", "behavior_tags", "command_patterns")))))
        n_docs = len(documents)
        return {term: math.log((n_docs + 1) / (count + 1)) + 1.0 for term, count in df.items()}

    def clear_cache(self) -> None:
        self._cache.clear()

    def retrieve(
        self,
        current_command: str,
        preceding_commands: Sequence[str] = (),
        *,
        session_id: str = "development",
        classification: str = "unknown",
        top_k: int = 8,
    ) -> dict[str, Any]:
        context = [str(command) for command in preceding_commands if isinstance(command, str)]
        context_truncated = len(context) > MAX_CONTEXT_COMMANDS
        if context_truncated:
            context = context[-MAX_CONTEXT_COMMANDS:]
        all_commands = [*context, str(current_command)]
        features = analyze_command_sequence(all_commands)
        projection = {
            "version": VERSION,
            "session_id": str(session_id),
            "classification": str(classification),
            "current_command": str(current_command),
            "preceding_commands": context,
            "context_truncated": context_truncated,
            "features": features,
        }
        cache_key = _sha256(projection)
        if cache_key in self._cache:
            cached = json.loads(json.dumps(self._cache[cache_key]))
            cached["trace"]["cache_hit"] = True
            return cached

        query_terms = set(_tokens(" ".join([str(classification), str(current_command), *context])))
        behavior_terms = set(features["behavior_indicators"] + features["path_categories"] + features["executables"])
        behavior_terms.update(_BEHAVIOR_TAGS[item] for item in features["behavior_indicators"] if item in _BEHAVIOR_TAGS)
        scored: list[dict[str, Any]] = []
        for document in self.documents:
            searchable = set(_tokens(" ".join(str(document.get(key, "")) for key in ("title", "content", "behavior_tags", "command_patterns"))))
            lexical_terms = query_terms & searchable
            lexical_score = sum(self._idf.get(term, 1.0) for term in lexical_terms) / max(sum(self._idf.get(term, 1.0) for term in query_terms), 1.0)
            patterns = [str(pattern).lower() for pattern in document.get("command_patterns", [])]
            exact_matches = [pattern for pattern in patterns if any(_pattern_matches(pattern, command) for command in all_commands)]
            exact_score = min(len(exact_matches) / max(len(patterns), 1), 1.0)
            doc_behaviors = {str(item) for item in document.get("behavior_tags", [])}
            behavior_score = len(behavior_terms & doc_behaviors) / max(len(behavior_terms), 1)
            score = round(0.45 * lexical_score + 0.40 * exact_score + 0.15 * behavior_score, 6)
            if score <= 0.0:
                continue
            scored.append({
                "evidence_id": str(document["evidence_id"]),
                "score": score,
                "lexical_score": round(lexical_score, 6),
                "exact_pattern_score": round(exact_score, 6),
                "behavior_score": round(behavior_score, 6),
                "matched_command_patterns": exact_matches,
                "source": document["source"],
                "source_version": document.get("source_version", ""),
                "provenance_hash": document.get("provenance_hash", ""),
                "relevance": "command_grounded" if exact_matches else "contextual_only",
            })
        scored.sort(key=lambda item: (-item["score"], item["evidence_id"]))
        top = scored[: max(0, int(top_k))]
        relevant = [item for item in top if item["relevance"] == "command_grounded" and item["score"] >= 0.20]
        trace = {
            "version": VERSION,
            "schema": SCHEMA,
            "cache_key": cache_key,
            "cache_hit": False,
            "corpus_path": str(self.corpus_path),
            "corpus_sha256": self.corpus_sha256,
            "query": " ".join([str(classification), *context, str(current_command)]).strip(),
            "context_projection": projection,
            "top_k": top,
            "relevant_evidence_ids": [item["evidence_id"] for item in relevant],
            # Abstention is an explicit, analysable outcome — never a silent
            # empty context. A command outside every corpus command pattern
            # yields relevant=[] BY DESIGN; the trace must say so loudly so a
            # downstream analyst (or evidence gate) can see the analysis ran
            # with zero grounded intel instead of mistaking it for "no threat
            # behaviour found".
            "abstained": not bool(relevant),
            "retrieval_status": (
                "COMMAND_GROUNDED" if relevant else "ABSTAINED_NO_COMMAND_PATTERN_MATCH"
            ),
            "query_coverage": {
                "complete": bool(relevant),
                "required_behavior_terms": sorted(behavior_terms),
                "covered_behavior_terms": sorted({term for item in relevant for term in item["matched_command_patterns"]}),
            },
        }
        result = {"documents": [self._document_for_hit(item) for item in relevant], "trace": trace}
        self._cache[cache_key] = json.loads(json.dumps(result))
        return result

    def _document_for_hit(self, hit: Mapping[str, Any]) -> dict[str, Any]:
        source = next(document for document in self.documents if document["evidence_id"] == hit["evidence_id"])
        return {
            "doc_id": source["evidence_id"],
            "title": source["title"],
            "content": source["content"],
            "source": source["source"],
            "source_version": source.get("source_version", ""),
            "license_or_permissions": source.get("license_or_permissions", ""),
            "provenance_hash": source.get("provenance_hash", ""),
            "command_patterns": source.get("command_patterns", []),
            "behavior_tags": source.get("behavior_tags", []),
            "techniques": source.get("techniques", []),
            "score": hit["score"],
            "relevance_grade": hit["relevance"],
        }

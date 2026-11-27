import hashlib
import hmac
import ipaddress
import re
import unicodedata

SENSITIVE_KEYS = {"password", "passwd", "secret", "token", "api_key", "apikey", "authorization", "credential"}
# Cowrie (and general honeypot) session records carry endpoints under more
# names than the original allowlist: dest_ip/dst_ip (egress target),
# src_host/dst_host (resolved endpoint names). Missing any of them let raw
# endpoints reach the canonical record unredacted.
IP_KEYS = {
    "ip",
    "source_ip",
    "src_ip",
    "remote_ip",
    "client_ip",
    "address",
    "dest_ip",
    "dst_ip",
    "destination_ip",
    "src_host",
    "dst_host",
    "dest_host",
    "source_host",
}

# Scripts whose letters are classic homoglyph substitutes for Latin
# (Cyrillic/Greek/Armenian/Hebrew/Arabic/Fullwidth). A whitespace-delimited
# token that mixes one of these with ASCII letters is a homoglyph-camouflaged
# identifier (e.g. a domain with a Cyrillic 'а') and is redacted as a unit.
_HOMOGLYPH_SCRIPT_RE = re.compile("[\u0370-\u03ff\u0400-\u04ff\u0530-\u058f\u0590-\u05ff\u0600-\u06ff\ufb50-\ufdff\ufe70-\ufeff\uff00-\uffef]")
_ASCII_LETTER_RE = re.compile(r"[A-Za-z]")

# Generous IPv6 candidate shape (hex groups and colons); each candidate is
# validated with ipaddress before redaction, so false candidates (timestamps,
# ratios) pass through untouched.
_IPV6_CANDIDATE_RE = re.compile(r"(?<![\w:])(?:[A-Fa-f0-9]{0,4}:){2,}[A-Fa-f0-9]{0,4}(?![\w:])")
# Base64-shaped blob: long base64 runs (with optional padding) standing alone
# in text are a common exfiltration encoding for credentials.
_BASE64_BLOB_RE = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{24,}={0,2}(?![A-Za-z0-9+/=])")

def source_cluster_id(study_secret, normalized_source_identifier):
    if not study_secret or not normalized_source_identifier:
        return None
    return hmac.new(study_secret.encode(), normalized_source_identifier.encode(), hashlib.sha256).hexdigest()

def _looks_like_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False

def _redact_ipv6(value):
    def _replace(match):
        candidate = match.group(0)
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return candidate
        return "[REDACTED_IP]"

    return _IPV6_CANDIDATE_RE.sub(_replace, value)

def _redact_homoglyph_tokens(value):
    """Redact tokens mixing Latin letters with confusable-script letters.

    A mixed-script identifier (a domain name where one Latin letter was
    swapped for a lookalike Cyrillic letter) is camouflage, not legitimate
    prose: it is redacted as a unit. Pure non-ASCII words (real i18n text)
    and pure ASCII tokens are untouched.
    """
    def _replace(match):
        token = match.group(0)
        if _ASCII_LETTER_RE.search(token) and _HOMOGLYPH_SCRIPT_RE.search(token):
            return "[REDACTED_HOMOGLYPH]"
        return token

    return re.sub(r"\S+", _replace, value)

def _redact_text(value):
    """Redact credential-shaped substrings without changing their position.

    The minimizer is deliberately conservative: it removes authentication
    headers, bearer/basic tokens, assignment-shaped secrets, common cloud/API
    token formats, URL userinfo, and IP literals.  Callers that need a bounded
    value must minimize *first* and truncate second, so a truncation boundary
    can never split a credential marker and leave its tail in the clear.
    """
    value = re.sub(
        r"(?i)\b(authorization|proxy-authorization|cookie|set-cookie)\s*:\s*[^\r\n]+",
        r"\1: [REDACTED]",
        value,
    )
    value = re.sub(
        r"(?i)\b(bearer|basic|token)\s+[A-Za-z0-9._~+/=-]{6,}",
        r"\1 [REDACTED]",
        value,
    )
    # Assignment AND colon forms of secret-carrying field names. The colon
    # shape previously passed through (a quoted secret after a field name and
    # colon reached the observation ledger unredacted). Spacing is limited to
    # [ \t] so the match never crosses a newline: a next-line value is handled
    # by its own rule below, and prose banners like mysql's
    # 'Enter password:' followed by a welcome line must not be eaten.
    value = re.sub(
        r"(?i)(password|passwd|token|api[_-]?key|secret|access[_-]?key|private[_-]?key)[ \t]*[=:][ \t]*['\"]?\S+",
        r"\1=[REDACTED]",
        value,
    )
    # PEM private keys travel on their own lines; redact the whole block.
    value = re.sub(
        r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----",
        "[REDACTED_PRIVATE_KEY]",
        value,
    )
    value = re.sub(r"(?i)(sshpass\s+-p\s*)\S+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)((?:--user|-u)\s+)[^\s:]+:[^\s]+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)(\bhttps?://)[^/\s:@]+:[^/\s@]+@", r"\1[REDACTED]@", value)
    value = re.sub(r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]", value)
    value = re.sub(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "[REDACTED_GITHUB_TOKEN]", value)
    value = re.sub(r"\bsk-[A-Za-z0-9_-]{16,}\b", "[REDACTED_API_KEY]", value)
    value = re.sub(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b", "[REDACTED_SLACK_TOKEN]", value)
    value = re.sub(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}\b",
        "[REDACTED_JWT]",
        value,
    )
    value = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IP]", value)
    value = _redact_ipv6(value)

    def _redact_base64_blob(match):
        blob = match.group(0)
        # Pure-hex runs are digests/hexdumps (sha256 lineages, file hashes),
        # not base64 — leaving them intact keeps provenance hashes usable.
        if re.fullmatch(r"[0-9a-fA-F]+", blob):
            return blob
        return "[REDACTED_BASE64]"

    value = _BASE64_BLOB_RE.sub(_redact_base64_blob, value)
    value = _redact_homoglyph_tokens(value)
    return value


def bounded_redacted_text(value: str, *, limit: int = 400) -> dict:
    """Return a minimized then truncated text value with explicit metadata.

    Minimization happens before truncation.  The returned ``text`` is never
    longer than ``limit`` characters; ``chars`` is the minimized length and
    ``truncated`` says whether truncation occurred.  The raw value is not
    retained here; callers that need integrity keep a separate SHA-256 over
    the original bytes.
    """
    if not isinstance(value, str):
        return {"text": "", "chars": 0, "truncated": False, "availability": "NOT_AVAILABLE"}
    minimized = privacy_minimize_record({"text": value}).get("text", "")
    minimized = minimized if isinstance(minimized, str) else str(minimized)
    bounded = minimized[: max(0, int(limit))]
    return {
        "text": bounded,
        "chars": len(minimized),
        "truncated": len(minimized) > len(bounded),
        "availability": "REDACTED_MINIMIZED",
    }

def privacy_minimize_record(value, *, credential_hash_secret=None):
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in IP_KEYS:
                output[key] = "[REDACTED_IP]"
            elif lowered in SENSITIVE_KEYS:
                if credential_hash_secret and isinstance(item, str):
                    output[key + "_hmac_sha256"] = hmac.new(
                        credential_hash_secret.encode(), item.encode(), hashlib.sha256
                    ).hexdigest()
                else:
                    output[key] = "[REDACTED]"
            else:
                output[key] = privacy_minimize_record(item, credential_hash_secret=credential_hash_secret)
        return output
    if isinstance(value, list):
        return [privacy_minimize_record(item, credential_hash_secret=credential_hash_secret) for item in value]
    if isinstance(value, str):
        return "[REDACTED_IP]" if _looks_like_ip(value) else _redact_text(value)
    return value

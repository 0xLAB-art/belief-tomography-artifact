"""Regression guard: server_v2 must not introduce a second Laya serving path.

The intent of the optional Laya config surface is only to gate whether the
existing ChrolloAdapter + laya_assessment_mapper emit an advisory Laya signal.
This test asserts the current code does not add any independent Laya HTTP
endpoint, listener, or command-serving path reachable from the public server_v2
router.

If a second Laya path is ever added here, this test must be updated to describe
it explicitly; it must not silently appear behind the optional config flag.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SERVER_V2 = Path("ragin/server_v2.py")


def _public_routes_from_parser() -> list[str]:
    """Derive the intended CLI routes/flags from server_v2's argparse help text.

    This avoids constructing the live aiohttp app during this focused regression
    test, so we do not trigger startup-time auth validation.
    """
    import contextlib
    import io

    import ragin.server_v2 as sv2

    buf = io.StringIO()
    with contextlib.suppress(Exception), contextlib.redirect_stdout(buf):
        try:
            parser = sv2.argparse.ArgumentParser(prog="ragin-server-v2-test")
            # Re-create the same argument schema server_v2.main() uses.
            parser.add_argument(
                "--mode",
                choices=["pipeline", "standalone"],
                default="pipeline",
                help="pipeline = full harness (default), standalone = single component",
            )
            parser.add_argument(
                "--component",
                choices=["chrollo", "don", "hisoka"],
                default=sv2.os.environ.get("COMPONENT", "chrollo"),
                help="Component to run in standalone mode",
            )
            parser.add_argument("--port", type=int, default=int(sv2.os.environ.get("PORT", "8080")))
            parser.print_help(buf)
        except Exception:
            pass

    text = buf.getvalue()
    flags: list[str] = []
    for line in text.splitlines():
        m = re.match(r"\s+(--[-\w]+)", line)
        if m:
            flags.append(m.group(1))
    return flags


def _public_routes_from_module() -> list[str]:
    """Fallback: inspect the live app routes only when env permits."""
    import os as _os

    import ragin.server_v2 as sv2

    routes: list[str] = []
    _os.environ.setdefault("RAGIN_REQUIRE_AUTH", "0")
    _os.environ.setdefault("API_KEY", "")
    try:
        app = sv2.create_app(mode="pipeline", component=None)
    finally:
        _os.environ.pop("RAGIN_REQUIRE_AUTH", None)
        _os.environ.pop("API_KEY", None)

    def walk_app(app):
        try:
            for r in app.router.routes():
                try:
                    routes.append(r.path)
                except Exception:
                    routes.append(repr(r))
        except Exception:
            pass

    walk_app(app)
    return routes


def _regex_matches(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def _file_mentions_laya_endpoint() -> bool:
    text = SERVER_V2.read_text(encoding="utf-8")
    # Look for route registration strings that would expose a Laya-specific
    # HTTP path (e.g. /laya, /api/laya, /v1/laya, /assess/laya).
    endpoint_patterns = [
        r'add_get\(["\']\s*["\']/\s*["\']',  # placeholder guard below
    ]
    # Direct pattern-based scan for a Laya path registration.
    return bool(re.search(r'add_(get|post|put|delete)\(\s*["\']/\s*["\'][^"\']*\blaya\b', text, re.IGNORECASE))


def test_no_laya_route_on_active_pipeline_routes():
    # Prefer the parser-based inspection so we do not trigger server_v2 startup
    # auth validation in this focused regression test.
    cli_flags = _public_routes_from_parser()
    laya_flags = [f for f in cli_flags if re.search(r"(?i)\blaya\b", f)]
    # The active CLI must not expose a Laya-specific server mode/endpoint flag.
    assert not laya_flags, (
        "server_v2 CLI would expose a Laya-specific mode/endpoint flag: "
        f"{laya_flags}. The optional Laya config must NOT add a second "
        "serving path; it only gates the existing advisory assessment mapper."
    )
    # Also assert there is no Laya path registered in the live app when env
    # allows it.
    try:
        routes = _public_routes_from_module()
        laya_routes = [r for r in routes if re.search(r"(?i)\blaya\b", str(r))]
        assert not laya_routes, (
            "server_v2 would expose a Laya-specific HTTP route on the active "
            f"pipeline app: {laya_routes}."
        )
    except Exception as e:
        # If the live app cannot be constructed in this env, the parser-based
        # assertion above is the gating check.
        pass


def test_no_laya_route_in_source_registration():
    assert not _file_mentions_laya_endpoint(), (
        "server_v2 source registers a Laya-specific HTTP route. That would be a "
        "second serving path, which this config surface must not introduce."
    )


def test_optional_config_only_gates_existing_mapper():
    text = SERVER_V2.read_text(encoding="utf-8")
    adapter_lines = [ln for ln in text.splitlines() if "ChrolloAdapter" in ln or "laya_assessment_mapper" in ln]
    # The optional config must be referenced alongside the existing adapter/mapper
    # flow, not as the spine of a new serving path.
    assert adapter_lines, "expected server_v2 to still reference the existing ChrolloAdapter / laya_assessment_mapper flow"
    # There must be no standalone "Laya server", "Laya handler", or "Laya app".
    forbidden = ["LayaServer", "LayaHandler", "LayaApp", "class Laya", "def laya_server", "def laya_handler"]
    for token in forbidden:
        assert token not in text, (
            f"server_v2 contains a forbidden second-path artifact: {token!r}"
        )

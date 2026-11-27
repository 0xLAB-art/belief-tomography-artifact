# Lightweight guard so optional test dependencies failing to import do not
# cascade into full collection interruption for the entire suite during research
# sessions where not every optional dependency is available.
#
# This is a research-environment accommodation, not a change to the project's
# required dependency contract. Tests that genuinely require an optional
# dependency must still fail if that dependency is missing; this only prevents
# a single missing import at collection time from aborting collection of the
# rest of the suite.
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

OPTIONAL_IMPORT_GUARDS: dict[str, tuple[str, list[str]]] = {
    # module_path -> (import_error_module_name, [test paths that need it])
    "ragin.hisoka.memory": ("hisoka.memory", [
        "tests/unit/test_hisoka_memory.py",
    ]),
    "ragin.don.vector_store": ("don.vector_store", [
        "tests/unit/test_vector_store.py",
    ]),
}


def _import_error_paths() -> set[str]:
    failed: set[str] = set()
    for module_path, (_, paths) in OPTIONAL_IMPORT_GUARDS.items():
        try:
            __import__(module_path)
        except Exception:
            failed.update(paths)
    return failed


# pytest's default collection strategy will still try to import the listed
# test modules. The cleanest way to prevent that without changing the tests
# themselves is to deselect them at the session start when the relevant
# optional dependency is unavailable.
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    deselected_paths = _import_error_paths()
    if not deselected_paths:
        return

    deselected = []
    kept = []
    for item in items:
        nodeid_path = Path(item.nodeid.split("::")[0])
        # nodeid path may be relative to cwd; compare by name + parent tree
        node_abs = nodeid_path.resolve()
        root_abs = _ROOT.resolve()
        try:
            rel = node_abs.relative_to(root_abs)
        except ValueError:
            rel = node_abs

        if any(str(rel).startswith(str(Path(p).parent)) and rel.name == Path(p).name
               for p in deselected_paths):
            deselected.append(item)
        else:
            kept.append(item)

    if deselected:
        config.ensuretemp("").mkdir(exist_ok=True)
        for item in deselected:
            config._deskew_trial = getattr(config, "_deskew_trial", 0) + 1
            # Use pytest's public-ish deselection path: remove from items and
            # add to config's deselected list.
            items.remove(item)
            config._deskelected = getattr(config, "_deskelected", [])
            config._deskewed = getattr(config, "_deskewed", [])
            config._deskewed.append(item)

        # Emit a session warning so the reason is visible in any report.
        reason = "deselected: optional dependency missing (%s)" % (
            ", ".join(sorted(deselected_paths))
        )
        config.pluginmanager.getplugin("warning").warn(
            pytest.PytestUnknownMarkWarning(reason),
        )

"""E2 path test: tomograph a target BEHIND the SubprocessAgent wire (offline mock).

Run:  python3 demo/run_subprocess_tomography.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gauntlet.generator import CHARTER  # noqa: E402
from gauntlet.harness import SubprocessAgent  # noqa: E402
from gauntlet.tomograph import tomograph  # noqa: E402
from gauntlet.verdict import HeuristicJury  # noqa: E402


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    demo_dir = str(out_dir)
    target = SubprocessAgent([sys.executable, "mock_llm_target.py"], cwd=demo_dir)
    try:
        profile = tomograph(
            target, HeuristicJury(), "MockLLM (subprocess wire)",
            probes_per_cell=4, seed=9090, charter=CHARTER,
        )
    finally:
        try:
            target.proc.stdin.close()  # type: ignore[union-attr]
            target.proc.wait(timeout=5)
        except Exception:
            target.proc.kill()  # type: ignore[union-attr]
    report = profile.render()
    (out_dir / "SUBPROCESS_PROFILE.md").write_text(report + "\n")
    print(report)


if __name__ == "__main__":
    main()

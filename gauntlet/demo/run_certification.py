"""End-to-end v0 demo: certify the naive dummy target through the closed loop.

Run:  python3 demo/run_certification.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.target_dummy import DummyTarget  # noqa: E402
from gauntlet.certificate import build_certificate, render_markdown  # noqa: E402
from gauntlet.generator import GauntletGenerator  # noqa: E402
from gauntlet.harness import run_certification  # noqa: E402
from gauntlet.verdict import HeuristicJury  # noqa: E402


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    generator = GauntletGenerator(seed=1337)
    verdicts = run_certification(
        target=DummyTarget(),
        generator=generator,
        jury=HeuristicJury(),
        adaptive_budget=15,
    )
    cert = build_certificate(verdicts, target_name="DummyTarget (naive foil, v0 demo)")
    (out_dir / "results.json").write_text(json.dumps(cert, indent=2))
    report = render_markdown(cert)
    (out_dir / "CERTIFICATE.md").write_text(report + "\n")
    print(report)
    print(f"\nWritten: {out_dir / 'results.json'}")
    print(f"Written: {out_dir / 'CERTIFICATE.md'}")


if __name__ == "__main__":
    main()

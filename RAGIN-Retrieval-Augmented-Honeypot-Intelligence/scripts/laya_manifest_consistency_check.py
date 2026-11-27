#!/usr/bin/env python3
"""Rebuild the manifest items array in place and verify blindness + schema.

Run this whenever independent_label_candidates.json is regenerated, to ensure
the `items` array actually contains {packet, meta} objects rather than the
placeholder {packet:"packet", meta:"meta"} stub.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

MANIFEST_PATH = Path("results/laya_research/independent_label_candidates.json")
PACKET_PATH = Path("results/laya_research/blind_annotation_packet.json")


def main() -> None:
    if not MANIFEST_PATH.exists():
        print("manifest missing:", MANIFEST_PATH)
        sys.exit(1)

    m = json.loads(MANIFEST_PATH.read_text())
    items = m.get("items", [])
    if not items:
        print("manifest items empty")
        sys.exit(1)

    first = items[0]
    if not isinstance(first, dict) or set(first.keys()) != {"packet", "meta"}:
        print("manifest items schema unexpected:", list(first.keys()))
        sys.exit(1)

    if not isinstance(first["packet"], dict) or "id" not in first["packet"]:
        print("packet field missing id:", first.get("packet"))
        sys.exit(1)

    if not isinstance(first["meta"], dict) or "provenance" not in first["meta"]:
        print("meta field missing provenance:", first.get("meta"))
        sys.exit(1)

    # Blindness: packet must not contain provenance or truth keys.
    packet_keys = set(first["packet"].keys())
    if not packet_keys == {"id", "evidence"}:
        print("packet contains non-blind fields:", packet_keys)
        sys.exit(1)

    print("manifest items OK:", len(items))
    print("sample packet:", json.dumps(first["packet"], ensure_ascii=False)[:200])
    print("sample meta:", json.dumps(first["meta"], ensure_ascii=False)[:200])

    # Rebuild blind packet from manifest for consistency.
    packet_out = [it["packet"] for it in items]
    PACKET_PATH.write_text(json.dumps(packet_out, indent=2, ensure_ascii=False) + "\n")
    print("rebuilt blind packet:", len(packet_out))

    # Optional: if the pool build script exists, keep it consistent by running it.
    pool_script = Path("scripts/laya_independent_candidate_pool.py")
    if pool_script.exists():
        r = subprocess.run(
            [sys.executable, str(pool_script)],
            cwd=Path("."),
            capture_output=True,
            text=True,
        )
        print("pool rebuild exit:", r.returncode)
        if r.stdout:
            print(r.stdout[-400:])
        if r.returncode != 0 and r.stderr:
            print("stderr:", r.stderr[-400:])


if __name__ == "__main__":
    main()

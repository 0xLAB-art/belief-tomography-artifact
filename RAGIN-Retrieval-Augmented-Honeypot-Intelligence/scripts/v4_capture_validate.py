#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ragin.capture_v4.manifest import validate_manifest

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    result = validate_manifest(manifest)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["valid"] else 2)

if __name__ == "__main__":
    main()

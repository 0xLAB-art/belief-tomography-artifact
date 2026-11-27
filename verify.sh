#!/usr/bin/env bash
# Verify the reviewer artifact package against its SHA-256 manifests.
set -euo pipefail
cd "$(dirname "$0")"

MANIFEST="docs/paper/belief_tomography/ARTIFACT_MANIFEST.sha256"
SUPPLEMENT="SUPPLEMENTARY_ASSETS.sha256"
EXPECTED=375

if [[ ! -f "$MANIFEST" ]]; then
  echo "ERROR: manifest not found: $MANIFEST" >&2
  exit 1
fi

out="$(sha256sum -c "$MANIFEST" 2>&1)" || {
  echo "MANIFEST VERIFICATION FAILED" >&2
  echo "$out" | grep -v ': OK$' >&2
  exit 1
}

ok="$(echo "$out" | grep -c ': OK$' || true)"
echo "Frozen experiment manifest: $ok files OK"

if [[ "$ok" -ne "$EXPECTED" ]]; then
  echo "ERROR: expected $EXPECTED entries, verified $ok" >&2
  exit 1
fi

if [[ -f "$SUPPLEMENT" ]]; then
  sout="$(sha256sum -c "$SUPPLEMENT" 2>&1)" || {
    echo "SUPPLEMENTARY MANIFEST VERIFICATION FAILED" >&2
    echo "$sout" | grep -v ': OK$' >&2
    exit 1
  }
  sok="$(echo "$sout" | grep -c ': OK$' || true)"
  sexp="$(grep -vc '^#' "$SUPPLEMENT" || true)"
  echo "Supplementary assets: $sok files OK"
  if [[ "$sok" -ne "$sexp" ]]; then
    echo "ERROR: expected $sexp supplementary entries, verified $sok" >&2
    exit 1
  fi
fi

echo "All frozen and supplementary artifacts verify."

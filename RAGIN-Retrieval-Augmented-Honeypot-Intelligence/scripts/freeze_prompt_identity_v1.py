#!/usr/bin/env python3
"""Freeze the serving prompt's identity into a pinnable artifact (offline).

``UNRESOLVED_PROMPT_ID`` in the run contract means the ablation cannot say
*which* prompt produced an arm's responses. This script gives that prompt a
stable, traceable identity derived only from the prompt text itself:

* collects the composing parts from ``ragin.hisoka.deception``
  (system-prompt preamble, identity-block template, per-role prompts, and the
  five composed per-skill persona system prompts);
* canonicalizes them (sorted keys, no timestamps) and hashes them, so the
  id changes if and only if prompt text changes;
* writes ``configs/ablation/eval_v1/prompt_v1.json`` and prints the artifact
  SHA-256 to record in the run contract's ``bundle.prompt`` block.

Strictly offline: no model, no network, no provider, no weights are touched.
Re-running reproduces byte-identical output, so the artifact hash is stable.

Exit codes: 0 written (or identical when current), 2 artifact exists (use
--force after a deliberate prompt revision), 1 failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Defensive scratch dirs (same rationale as the focused unit tests): the
# import must never create or touch session/host-fiction files under data/.
os.environ.setdefault("RAGIN_SESSION_DIR", str(Path(tempfile.mkdtemp(prefix="ragin-prompt-freeze-")) / "sessions"))
os.environ.setdefault("RAGIN_HOST_FICTION_PATH", os.path.join(tempfile.gettempdir(), "ragin-prompt-freeze-host-fiction.json"))
Path(os.environ["RAGIN_SESSION_DIR"]).mkdir(parents=True, exist_ok=True)

from ragin.hisoka.deception import (  # noqa: E402
    _IDENTITY_BLOCK_TEMPLATE,
    _PERSONA_CONFIGS,
    _ROLE_PROMPTS,
    _SYSTEM_PROMPT_PREAMBLE,
    _persona_system_prompt,
)

SCHEMA = "ragin.prompt.identity.v1"
DEFAULT_OUT = ROOT / "configs" / "ablation" / "eval_v1" / "prompt_v1.json"
_SKILLS = ("novice", "intermediate", "expert", "advanced", "apt")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_prompt_identity() -> dict:
    """Compose the prompt identity payload (no timestamps, sorted keys)."""
    role_prompts = {skill: _ROLE_PROMPTS[skill] for skill in _SKILLS}
    system_prompts = {skill: _persona_system_prompt(skill) for skill in _SKILLS}

    # The id hashes ONLY prompt text: unrelated code edits must not change it.
    hashed = {
        "system_prompt_preamble": _SYSTEM_PROMPT_PREAMBLE,
        "identity_block_template": _IDENTITY_BLOCK_TEMPLATE,
        "role_prompts": role_prompts,
        "persona_system_prompts": system_prompts,
    }
    content_sha = _sha(
        json.dumps(hashed, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    )
    identity = {
        "schema": SCHEMA,
        "prompt_id": f"prompt_v1_{content_sha[:12]}",
        "content_sha256": content_sha,
        "skills": list(_SKILLS),
        "composition": (
            "default: system_prompt = _persona_system_prompt(skill); "
            "identity-override path: PREAMBLE + '\\n' + IDENTITY_BLOCK.format(pinned) "
            "+ '\\n\\n' + ROLE_PROMPT[skill] + '\\n'; optional leading 'Context: ...'"
        ),
        "components": {
            "system_prompt_preamble_sha256": _sha(_SYSTEM_PROMPT_PREAMBLE),
            "identity_block_template_sha256": _sha(_IDENTITY_BLOCK_TEMPLATE),
            "role_prompt_sha256": {k: _sha(v) for k, v in role_prompts.items()},
            "persona_system_prompt_sha256": {k: _sha(v) for k, v in system_prompts.items()},
        },
        "persona_system_prompts": system_prompts,
        # Provenance recorded AFTER hashing so code edits that do not touch
        # prompt text cannot silently move the id.
        "provenance": {
            "source_module": "ragin/hisoka/deception.py",
            "source_module_sha256": hashlib.sha256(
                (ROOT / "ragin" / "hisoka" / "deception.py").read_bytes()
            ).hexdigest(),
            "generator": "scripts/freeze_prompt_identity_v1.py",
        },
        "non_claims": [
            "Identity of the prompt text only; no model was invoked and no "
            "inference occurred while freezing it.",
            "A pinned prompt id does not prove which prompt a run used — the "
            "run must also record generation_config_sha256 and model exposure.",
        ],
    }
    return identity


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--force", action="store_true", help="overwrite an existing artifact")
    args = parser.parse_args(argv)

    if args.out.exists() and not args.force:
        print(f"artifact exists: {args.out} (use --force after a deliberate prompt revision)", file=sys.stderr)
        return 2

    identity = build_prompt_identity()
    payload = json.dumps(identity, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": str(args.out.relative_to(ROOT)),
                "artifact_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                "prompt_id": identity["prompt_id"],
                "content_sha256": identity["content_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

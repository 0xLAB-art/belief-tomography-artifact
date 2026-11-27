# Cowrie persona alignment proof

Status: `NOT_ESTABLISHED` / partial native alignment. The bounded sequence used two loopback SSH sessions, five commands each, against cached image `sha256:710f1e4601a663ac8591f58a42b44e4cd3b7ea170c7e6cdb9e54c430a30cd459`. No provider, AWS, JEV, download, or image pull was used.

The native Cowrie arm served the declared user, host, uid/gid, cwd prompt, kernel string, and Ubuntu release fixture. Its raw SSH stdout is `ssh_client.native.stdout` (SHA-256 `d09d04fe25918d506beec552a6432e48e3a3b967c092dbdd50774121818e3765`). Observed prompt: `webapp@web-srv-01:~$ `; observed `id`: `uid=1001(webapp) gid=1001(webapp) groups=1001(webapp)`; observed hostname: `web-srv-01`.

The RAGIN arm reached the real loopback SSH frontend, but the local server rejected all five requests with HTTP 401 because the interrupted runner used `persona-lab-local-key` while `safe_env()` configured `API_KEY=p0-loopback-local-key`. The frontend therefore emitted prompts without command answers. Its raw stdout is `ssh_client.ragin.stdout` (SHA-256 `f4b0f33e852b08211d843d3488500fc06189061190c7a476f05746b3a871d881`). The observed prompt was `webapp@web-srv-01:/$ `, independently confirming the known peer-owned LLM protocol cwd mismatch.

The proof script now uses the matching loopback key for future bounded reruns, strips only PTY presentation controls in its derived parser view, and retains raw bytes unchanged. A future rerun is required to establish RAGIN command answers; this task stops here to preserve the two-session bound. Strict profile configuration remains `research_strict_v1`, provider disabled, and native Cowrie uses no RAGIN verifier.

Focused validation: `.venv/bin/pytest -q tests/unit/test_persona_alignment_v1.py` → `3 passed`; `python -m py_compile scripts/prove_cowrie_persona_alignment_v1.py` → exit `0`.

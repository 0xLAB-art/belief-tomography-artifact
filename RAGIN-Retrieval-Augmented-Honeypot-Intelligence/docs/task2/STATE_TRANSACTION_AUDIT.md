# Task 2: State-Transaction Audit

## Fiction graph

`FictionGraph.clone` and `replace_from` provide the staged-update primitive (`ragin/graph/fiction.py:282-305`). The deterministic verifier observes a clone rather than the authoritative graph (`ragin/cycle/verifier.py`), and the strict Harness path clones again for the accepted-candidate commit (`ragin/cycle/harness.py:286-296`). A rejected draft therefore cannot mint session facts.

The LangGraph path uses the same staged pattern in `verify_node`/`finalize_node` (`ragin/cycle/graph.py:321-425`). Its fallback is independently verified before it can replace a rejected response. It is still not the public server path.

## Host-fiction state

Host identity is pinned by `HostFictionStore.session_graph`; only verified sessions are promoted. `_strict_commit` snapshots host state, marks/promotes only after acceptance, and restores the graph and host snapshot if persistence or event emission fails (`ragin/cycle/harness.py:277-325`). `HostFictionStore.save` writes a temporary file and replaces the target; `restore_from_dict` supports rollback (`ragin/graph/host_fiction.py:321-342`).

Persistence failure is safe: no accepted response is returned, and the result is `verified_serving_failed`. The implementation attempts to restore in-memory state; a second persistence failure is logged through the controlled failure path. This is not a distributed transaction: multiple independent CORE processes writing the same JSON file are not proven safe, and no AWS protected audit store exists yet.

## Concurrency and interruption

`Sandbox.handle_command` serializes access with an `RLock`, preventing concurrent commands from racing session counters or Harness state (`ragin/cycle/sandbox.py:80-116`). Session events are append-only and the existing wake path can replay event logs, but filesystem locking and multi-process coordination are not established. If delivery is interrupted after commit, the accepted response and provenance remain in the session log; a retry must use the session protocol and must not re-commit arbitrary generated content.

## Audit completeness limits

The strict decision records verification, acceptance, path, attempt, candidate digest, and approval data. Field export remains best-effort and should not be treated as the authoritative audit store. Source IP handling, durable tamper evidence, multi-writer locking, retention, encryption, and AWS IAM controls remain deployment work.

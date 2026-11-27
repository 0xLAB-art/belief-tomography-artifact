# Security Regression Results

## PASS

- Focused Python mTLS, verified-serving, and `server_v2` tests: 42 passed in 1.32 seconds.
- Full prior repaired-suite result: 1,645 passed, 116 skipped, 34 warnings.
- Valid mTLS identity reached CORE; missing certificate and invalid API key failed closed.
- Cowrie output was synthetic and did not provide a real Ubuntu shell.
- Public reachability checks for CORE `8443` and EDGE `2222/18083` timed out.
- CORE SSH through the new EIC endpoint succeeded after the exact UFW source rule was added.

## INCOMPLETE

- EDGE arbitrary egress denial was not tested or enabled.
- Container-level metadata isolation and Docker forwarding behavior were not tested in a final network-isolated runtime.
- Encrypted EBS migration was not performed.
- Private CORE cutover was not performed.
- Rust gateway authentication remains outside the serving path.
- Public Cowrie port-22 replacement was not attempted.

No security assertion was weakened to obtain the passing results.

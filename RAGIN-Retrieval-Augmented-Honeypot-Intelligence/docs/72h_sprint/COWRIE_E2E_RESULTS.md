# Cowrie End-to-End Results

## Controlled path

`authorized local SSH client -> Cowrie 127.0.0.1:2222 -> loopback socat mTLS forwarder -> CORE 172.31.17.217:8443 -> serving pipeline -> Cowrie SSH output`

## PASS evidence

Observed interactive output from the owned EDGE host:

```text
Welcome to svr04
test@svr04:/$ whoami
webapp@web-srv-01:~$ whoami
webapp
test@svr04:/$ exit
Connection to 127.0.0.1 closed.
```

Cowrie recorded login, `CMD: whoami`, and `CMD: exit`. CORE recorded authenticated requests and a 200 response. The response was synthetic and did not expose the Ubuntu host shell. `evidence/cowrie_to_core_e2e.json` contains the redacted provenance summary.

## Negative and recovery observations

- Public EDGE port 2222 timed out; no public Cowrie exposure was attempted.
- Invalid client/authentication cases failed closed in the CORE boundary tests.
- An initial Cowrie test failed because its tty directory was absent; the directory was created with the container UID and the test was rerun.
- An earlier endpoint syntax was corrected before the final run.
- Host networking is retained only for this private staging bridge. It is a residual risk and is not a final field configuration.

## Not claimed

This does not prove that public port 22 terminates at Cowrie. Ubuntu administrative SSH remains the only operator path, and a future public Cowrie cutover requires a separate approval and isolation test.

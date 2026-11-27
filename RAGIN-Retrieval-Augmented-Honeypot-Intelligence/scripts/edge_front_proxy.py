#!/usr/bin/env python3
"""RAGIN EDGE front proxy: 0.0.0.0:2222 -> cowrie (172.29.0.2:2222).

Logs every accepted connection with the TRUE pre-NAT source to
/opt/ragin/proxy_connections.jsonl, then pipes raw TCP both ways.
No PROXY header is injected (cowrie stays untouched); this JSONL is the
authoritative source-attribution record for the field.
"""
import asyncio
import json
import os
import time

LISTEN = ("0.0.0.0", 2222)
UPSTREAM = ("172.29.0.2", 2222)
LOG = "/opt/ragin/proxy_connections.jsonl"


def log_event(event: str, peer, extra=None) -> None:
    rec = {
        "ts": time.time(),
        "event": event,
        "src_ip": peer[0] if peer else None,
        "src_port": peer[1] if peer else None,
        "dst_port": LISTEN[1],
    }
    if extra:
        rec.update(extra)
    try:
        with open(LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


async def pump(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def handle(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter) -> None:
    peer = client_writer.get_extra_info("peername")
    log_event("connect", peer)
    up_reader = up_writer = None
    try:
        up_reader, up_writer = await asyncio.open_connection(*UPSTREAM)
        t1 = asyncio.create_task(pump(client_reader, up_writer))
        t2 = asyncio.create_task(pump(up_reader, client_writer))
        await asyncio.gather(t1, t2)
    except Exception as exc:
        log_event("error", peer, {"err": type(exc).__name__})
    finally:
        log_event("close", peer)
        for w in (client_writer, up_writer):
            if w is not None:
                try:
                    w.close()
                except Exception:
                    pass


async def main() -> None:
    server = await asyncio.start_server(handle, *LISTEN)
    os.chmod(LOG, 0o640) if os.path.exists(LOG) else None
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

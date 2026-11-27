import os, subprocess, time, pathlib, sys
print("launcher pid", os.getpid(), flush=True)
child = subprocess.Popen(
    [os.environ["VENV"] + "/bin/python", "-u", "-m", "ragin.server_v2", "--mode", "pipeline", "--port", "8083"],
    env=os.environ,
    stdin=subprocess.DEVNULL,
    stdout=open("/tmp/ragin-server-v2-8083.log", "ab"),
    stderr=open("/tmp/ragin-server-v2-8083-err.log", "ab"),
)
print("child pid", child.pid, flush=True)
time.sleep(3)
alive = child.poll() is None
print("child alive after 3s?", alive, flush=True)
rc = child.wait()
print("child rc", rc, flush=True)
for name in ("/tmp/ragin-server-v2-8083-err.log", "/tmp/ragin-server-v2-8083.log"):
    p = pathlib.Path(name)
    print(name, "exists" if p.exists() else "MISSING", "bytes", p.stat().st_size if p.exists() else 0, flush=True)

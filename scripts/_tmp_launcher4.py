import os, subprocess, time, pathlib

# Tool-boundary exports are unreliable in this runtime, so bake the two
# required values inline from the file directly. Everything else is passed
# through os.environ (already set by the caller).
PROJECT_DIR = "/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence"
venv = os.environ.get("VENV") or (PROJECT_DIR + "/.venv")
env_path = PROJECT_DIR + "/.env"

def _get_key(name):
    for line in pathlib.Path(env_path).read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line[len(name) + 1 :]
    return ""

api_key = os.environ.get("API_KEY") or _get_key("API_KEY")
if not api_key:
    raise SystemExit("launcher4: no API_KEY found")

child_env = dict(os.environ)
child_env["API_KEY"] = api_key

child = subprocess.Popen(
    [venv + "/bin/python", "-u", "-m", "ragin.server_v2", "--mode", "pipeline", "--port", "8083"],
    env=child_env,
    stdin=subprocess.DEVNULL,
    stdout=open("/tmp/ragin-server-v2-8083.log", "ab"),
    stderr=open("/tmp/ragin-server-v2-8083-err.log", "ab"),
)

print("launcher4 pid", os.getpid(), flush=True)
print("launcher4 child pid", child.pid, flush=True)
time.sleep(5)
alive = child.poll() is None
print("launcher4 child alive after 5s?", alive, flush=True)
rc = child.wait()
print("launcher4 child rc", rc, flush=True)
for name in ("/tmp/ragin-server-v2-8083-err.log", "/tmp/ragin-server-v2-8083.log"):
    p = pathlib.Path(name)
    print(name, "exists" if p.exists() else "MISSING", "bytes", p.stat().st_size if p.exists() else 0, flush=True)

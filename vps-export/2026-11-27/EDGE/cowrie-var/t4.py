
import os
print("cwd:", os.getcwd())
for root, dirs, files in os.walk("/cowrie/cowrie-git/src/cowrie"):
    dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
    for f in files:
        if "llm" in f.lower() or "backend" in f.lower():
            print("LLM-BACKEND:", os.path.join(root, f))
    if root.endswith("core"):
        print("core files:", sorted(files)[:10])
pickles = []
for root, dirs, files in os.walk("/cowrie/cowrie-git"):
    for f in files:
        if f.endswith(".pickle"):
            pickles.append(os.path.join(root, f))
print("pickles:", pickles[:6] or "NONE")

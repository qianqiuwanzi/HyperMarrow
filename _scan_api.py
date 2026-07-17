import pathlib
root = pathlib.Path(r"D:\OpenClaw\workspace\HyperMarrow\openclaw-memory-system\memory_core")
for p in sorted(root.glob("*.py")):
    if p.name.startswith("_"):
        continue
    txt = p.read_text(encoding="utf-8", errors="ignore")
    for i, line in enumerate(txt.splitlines(), 1):
        if any(k in line for k in ["def get_stats", "def stats(", "def summary(",
                                    "def count(", "def size(", "def get_count",
                                    "def get_state", "def list_all"]):
            if line.strip().startswith("def "):
                print(f"{p.name}:{i}: {line.strip()}")

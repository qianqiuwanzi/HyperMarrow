"""HyperMarrow 藏慧 API 启动脚本 — 端口冲突安全版"""
import sys, socket
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "openclaw-memory-system"))
sys.path.insert(0, str(_HERE / "openclaw-learning-system"))

PORT = 8741

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

if is_port_in_use(PORT):
    print(f"[Startup] Port {PORT} already in use — server already running, nothing to do.")
    sys.exit(0)

from memory_api.server import app
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

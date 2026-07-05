"""HyperMarrow 藏慧 API 启动脚本"""
import sys
from pathlib import Path
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "openclaw-memory-system"))
sys.path.insert(0, str(_HERE / "openclaw-learning-system"))

from memory_api.server import app
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8741, log_level="info")

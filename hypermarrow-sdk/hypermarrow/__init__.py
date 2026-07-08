"""
HyperMarrow SDK — Agent 集成开发包

两种使用模式:

1. 本地嵌入（Python Agent，零延迟）:
   from hypermarrow import HyperMarrowWire
   hm = HyperMarrowWire(agent_id="my-agent")

2. HTTP 客户端（非 Python Agent，语言无关）:
   from hypermarrow import HyperMarrowClient
   client = HyperMarrowClient(agent_id="my-agent", server="http://localhost:8741")
"""

from .wire import HyperMarrowWire
from .client import HyperMarrowClient

__version__ = "2.0.0"
__all__ = ["HyperMarrowWire", "HyperMarrowClient"]

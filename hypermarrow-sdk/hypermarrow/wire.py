"""
HyperMarrow Wire — 本地嵌入模式

Agent 进程中导入，自动启动心跳、提供记忆/学习接口。
"""

import sys
import os
import threading
import time
from pathlib import Path


class HyperMarrowWire:
    """
    Agent 一线接入接口 — 本地嵌入模式。

    用法:
        from hypermarrow import HyperMarrowWire
        hm = HyperMarrowWire(
            agent_id="my-agent",
            server="http://localhost:8741",
            hypermarrow_path="D:/OpenClaw/workspace/HyperMarrow",
        )
        hm.intercept(user_msg, agent_response)   # 每条消息
        result = hm.check(action, context)       # 决策前
        hm.record(action, context, outcome)      # 决策后
    """

    def __init__(self, agent_id: str = "openclaw",
                 server: str = "http://localhost:8741",
                 hypermarrow_path: str = None):
        self.agent_id = agent_id
        self.server = server.rstrip("/")
        self._dc = None
        self._reg = None
        self._initialized = False

        # Auto-detect HyperMarrow path
        if hypermarrow_path is None:
            hypermarrow_path = os.environ.get("HYPERMARROW_HOME", "")
        if hypermarrow_path:
            self._hm_path = Path(hypermarrow_path)
            sys.path.insert(0, str(self._hm_path / "openclaw-memory-system"))
            sys.path.insert(0, str(self._hm_path / "openclaw-learning-system"))
            self._init_local()
        else:
            # HTTP-only mode
            self._client = None

    def _init_local(self):
        """Initialize local embedded mode."""
        if self._initialized:
            return
        from memory_core.config import setup_hf_mirror
        setup_hf_mirror()
        from memory_integration.decision_check import create_for_agent, get_agent_registry
        self._dc = create_for_agent(self.agent_id)
        self._reg = get_agent_registry()
        self._initialized = True

        kg = self._dc.knowledge_graph.get_stats()
        ql = self._dc.ql_agent.get_stats()
        print(f"[HyperMarrow] {self.agent_id} ready: "
              f"KG={kg['total_entities']}, QL={ql['nonzero_entries']}/700")

        self._start_heartbeat()

    def _start_heartbeat(self):
        """Start daemon heartbeat thread."""
        import urllib.request

        def _beat():
            url_connect = f"{self.server}/api/v1/agents/{self.agent_id}/connect"
            url_beat = f"{self.server}/api/v1/agents/{self.agent_id}/heartbeat"
            try:
                req = urllib.request.Request(url_connect, method='POST')
                urllib.request.urlopen(req, timeout=3)
            except Exception:
                pass
            while True:
                try:
                    req = urllib.request.Request(url_beat, method='POST')
                    urllib.request.urlopen(req, timeout=3)
                except Exception:
                    pass
                time.sleep(30)

        t = threading.Thread(target=_beat, daemon=True,
                            name=f"hm_{self.agent_id}_heartbeat")
        t.start()

    def _ensure_client(self):
        """Lazy-init HTTP client if not in embedded mode."""
        if not hasattr(self, '_client') or self._client is None:
            from .client import HyperMarrowClient
            self._client = HyperMarrowClient(
                agent_id=self.agent_id,
                server=self.server,
            )

    # ── Public API ──────────────────────────────────────────────────────

    def intercept(self, user_message: str, agent_response: str = "",
                  blocking: bool = False) -> dict:
        if self._dc:
            from memory_integration.interceptor import hypermarow_intercept
            return hypermarow_intercept(
                user_message, agent_response,
                agent_id=self.agent_id,
                blocking=blocking,
            )
        self._ensure_client()
        return self._client.intercept(user_message, agent_response)

    def check(self, action: str, **context) -> dict:
        if self._dc:
            return self._dc.check(action=action, context=context if context else None)
        self._ensure_client()
        return self._client.check(action, context)

    def record(self, action: str, context: dict = None, outcome: str = "success",
               reward: float = None, note: str = ""):
        if self._dc:
            self._dc.record(action=action, context=context or {}, outcome=outcome,
                           reward=reward, note=note, async_mode=True)
        else:
            self._ensure_client()
            self._client.record(action, context, outcome, reward, note)

    def stats(self) -> dict:
        if self._dc:
            return {
                "kg": self._dc.knowledge_graph.get_stats(),
                "ql": self._dc.ql_agent.get_stats(),
                "em": self._dc.episodic_memory.get_stats(),
                "agents": self._reg.list_agents() if self._reg else [],
            }
        self._ensure_client()
        return self._client.stats()

    def dream(self) -> dict:
        if self._dc:
            return self._dc.consolidator.dream_cycle(force=True)
        self._ensure_client()
        return self._client.dream()

    def disconnect(self):
        import urllib.request
        try:
            url = f"{self.server}/api/v1/agents/{self.agent_id}/disconnect"
            req = urllib.request.Request(url, method='POST')
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass

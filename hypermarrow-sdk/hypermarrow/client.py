"""
HyperMarrow HTTP Client — 非 Python Agent 接入模式

任何语言的 Agent 都可以通过相同的 HTTP API 接入 HyperMarrow。
"""

import requests
import json
from typing import Optional


class HyperMarrowClient:
    """
    HTTP API 客户端 — 用于非 Python Agent 或远程 Agent。

    用法:
        client = HyperMarrowClient(agent_id="go-agent", server="http://localhost:8741")
        client.connect()
        client.intercept("user msg", "agent response")
        result = client.check("try_fix", {"task": "download"})
        client.record("try_fix", {"task": "download"}, "success", 0.8)
    """

    def __init__(self, agent_id: str, server: str = "http://localhost:8741",
                 api_token: str = None):
        self.agent_id = agent_id
        self.server = server.rstrip("/")
        self.api_token = api_token
        self._session = requests.Session()
        if api_token:
            self._session.headers["Authorization"] = f"Bearer {api_token}"

    def _post(self, path: str, data: dict = None) -> dict:
        try:
            r = self._session.post(
                f"{self.server}{path}",
                json=data or {},
                timeout=10,
            )
            return r.json() if r.text else {"status": "error", "message": r.status_code}
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    def _get(self, path: str) -> dict:
        try:
            r = self._session.get(f"{self.server}{path}", timeout=10)
            return r.json() if r.text else {}
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    def connect(self) -> dict:
        return self._post(f"/api/v1/agents/{self.agent_id}/connect")

    def disconnect(self) -> dict:
        return self._post(f"/api/v1/agents/{self.agent_id}/disconnect")

    def intercept(self, user_message: str, agent_response: str = "") -> dict:
        return self._post(f"/api/v1/agents/{self.agent_id}/intercept", {
            "user_message": user_message,
            "agent_response": agent_response,
        })

    def check(self, action: str, context: dict = None) -> dict:
        return self._post(f"/api/v1/agents/{self.agent_id}/check", {
            "action": action,
            "context": context or {},
        })

    def record(self, action: str, context: dict = None, outcome: str = "success",
               reward: float = None, note: str = "") -> dict:
        body = {"action": action, "context": context or {}, "outcome": outcome}
        if reward is not None:
            body["reward"] = reward
        if note:
            body["note"] = note
        return self._post(f"/api/v1/agents/{self.agent_id}/record", body)

    def stats(self) -> dict:
        return self._get(f"/api/v1/agents")

    def dream(self) -> dict:
        return self._get("/api/v1/dream/run")

    def heartbeat(self) -> dict:
        return self._post(f"/api/v1/agents/{self.agent_id}/heartbeat")

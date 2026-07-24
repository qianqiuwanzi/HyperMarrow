"""
HyperMarrow Client — pure HTTP, zero dependencies (stdlib only).

Connects to a local HyperMarrow desktop client API server.
Agent identity is set via HM_AGENT_ID env var or constructor argument.
"""
import os
import json
import urllib.request
import urllib.error

DEFAULT_API_URL = "http://localhost:8741"
DEFAULT_AGENT_ID = "claude"


class HyperMarrowClient:
    """Lightweight HTTP client for HyperMarrow memory & learning API."""

    def __init__(self, agent_id: str = None, api_url: str = None,
                 auto_connect: bool = True):
        self.agent_id = agent_id or os.environ.get("HM_AGENT_ID", DEFAULT_AGENT_ID)
        self.api_url = (api_url or os.environ.get("HM_API_URL", DEFAULT_API_URL)).rstrip("/")
        self._connected = False
        if auto_connect:
            self._connect()

    def _post(self, path: str, data: dict = None) -> dict:
        """POST JSON to API, return parsed response or {}."""
        url = f"{self.api_url}{path}"
        body = json.dumps(data or {}).encode("utf-8")
        req = urllib.request.Request(url, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def _get(self, path: str) -> dict:
        """GET JSON from API, return parsed response or {}."""
        url = f"{self.api_url}{path}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def _connect(self):
        """Register this agent with the API server."""
        if self._connected:
            return
        r = self._post(f"/api/v1/agents/{self.agent_id}/connect")
        self._connected = r.get("status") == "connected" or "error" not in r
        return r

    # ── Core API ──────────────────────────────────────────────────────────

    def intercept(self, user_message: str, agent_response: str = "") -> dict:
        """
        Archive a conversation turn. Non-blocking.
        Returns: entities_found, episodes_created, rules_matched
        """
        return self._post(f"/api/v1/agents/{self.agent_id}/intercept", {
            "user_message": user_message,
            "agent_response": agent_response,
        })

    def check(self, action: str, task: str = "", context: dict = None) -> dict:
        """
        Query memory system before making a decision.
        Returns: recommendation, confidence, matched_rules, warnings
        """
        return self._post(f"/api/v1/agents/{self.agent_id}/check", {
            "action": action,
            "task": task,
            "context": context or {},
        })

    def record(self, action: str, context: dict = None,
               outcome: str = "success") -> dict:
        """
        Record a decision outcome for learning. Non-blocking.
        outcome: "success" | "failure" | "partial"
        """
        return self._post(f"/api/v1/agents/{self.agent_id}/record", {
            "action": action,
            "context": context or {},
            "outcome": outcome,
        })

    def search(self, query: str, limit: int = 5) -> dict:
        """Search historical memory."""
        return self._get(
            f"/api/v1/search?q={urllib.parse.quote(query)}&limit={limit}")

    def stats(self) -> dict:
        """Get full system statistics."""
        mem = self._get("/api/v1/memory/overview")
        learn = self._get("/api/v1/learning/overview")
        return {"memory": mem, "learning": learn}

    def agents(self) -> list:
        """List connected agents."""
        return self._get("/api/v1/agents")

    def dream(self) -> dict:
        """Trigger memory consolidation cycle."""
        return self._get("/api/v1/dream/run")


# ── Global singleton ──────────────────────────────────────────────────────
hm = HyperMarrowClient()

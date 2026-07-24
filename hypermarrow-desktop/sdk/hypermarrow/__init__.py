"""
HyperMarrow Client SDK — lightweight HTTP client for the HyperMarrow API.

Usage:
    from hypermarrow import hm

    hm.intercept(user_msg, agent_response)
    result = hm.check("try_fix", task="...")
    hm.record("try_fix", outcome="success")

Configuration via environment variables:
    HM_AGENT_ID    — agent identifier (default: "claude")
    HM_API_URL     — API base URL (default: "http://localhost:8741")
"""

from .client import HyperMarrowClient, hm

__version__ = "2.1.3"
__all__ = ["HyperMarrowClient", "hm"]

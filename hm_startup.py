"""HyperMarrow startup — import this in OpenClaw's entry point."""
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "openclaw-memory-system"))
sys.path.insert(0, str(_HERE / "openclaw-learning-system"))

from memory_core.config import setup_hf_mirror
setup_hf_mirror()

from memory_integration.decision_check import create_for_agent

DC = None
_HM_READY = False

try:
    DC = create_for_agent("openclaw")

    # Enable WorldModel if torch available
    try:
        DC.ql_agent.enable_world_model()
    except Exception:
        pass

    # Announce connection to API server (real-time status)
    try:
        import urllib.request, json
        req = urllib.request.Request(
            'http://localhost:8741/api/v1/agents/openclaw/connect',
            method='POST'
        )
        urllib.request.urlopen(req)
        print("[HyperMarrow] Connection announced to API server")
    except Exception:
        pass  # API might not be running yet, that's ok

    _HM_READY = True
    print(f"[HyperMarrow] Bridge ready: "
          f"KG={DC.knowledge_graph.get_stats()['total_entities']} entities, "
          f"QL={DC.ql_agent.get_stats()['nonzero_entries']}/700, "
          f"PM={len(DC.procedural_memory.data.get('rules',{}))} rules")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"[HyperMarrow] Bridge init FAILED: {e}")

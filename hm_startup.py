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

    # ── Heartbeat thread: keep agent connection alive ─────────────────────
    def _run_heartbeat():
        import urllib.request, time
        url_connect = 'http://localhost:8741/api/v1/agents/openclaw/connect'
        url_beat = 'http://localhost:8741/api/v1/agents/openclaw/heartbeat'
        # Initial connect
        try:
            urllib.request.urlopen(urllib.request.Request(url_connect, method='POST'), timeout=3)
            print("[HyperMarrow] Connection announced to API server")
        except Exception:
            pass
        # Periodic heartbeat every 30s
        while True:
            try:
                urllib.request.urlopen(urllib.request.Request(url_beat, method='POST'), timeout=3)
            except Exception:
                pass
            time.sleep(30)

    import threading
    t = threading.Thread(target=_run_heartbeat, daemon=True, name="hm_startup_heartbeat")
    t.start()

    _HM_READY = True
    print(f"[HyperMarrow] Bridge ready: "
          f"KG={DC.knowledge_graph.get_stats()['total_entities']} entities, "
          f"QL={DC.ql_agent.get_stats()['nonzero_entries']}/700, "
          f"PM={len(DC.procedural_memory.data.get('rules',{}))} rules")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"[HyperMarrow] Bridge init FAILED: {e}")

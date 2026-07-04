"""HyperMarrow Bridge startup — import this in OpenClaw's hook or entry point."""
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
    _DC_luci = create_for_agent("luci")

    # Enable WorldModel if torch available
    try:
        DC.ql_agent.enable_world_model()
        _DC_luci.ql_agent.enable_world_model()
    except Exception:
        pass

    # Start sleep scheduler
    from openclaw_memory_system.hypermarow_bridge import _start_sleep_scheduler
    from memory_integration.decision_check import get_agent_registry
    _start_sleep_scheduler(get_agent_registry())

    _HM_READY = True
    print(f"[HyperMarrow] Bridge ready: 2 agents, "
          f"KG={DC.knowledge_graph.get_stats()['total_entities']} entities, "
          f"QL={DC.ql_agent.get_stats()['nonzero_entries']}/700, "
          f"PM={len(DC.procedural_memory.data.get('rules',{}))} rules")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"[HyperMarrow] Bridge init FAILED: {e}")

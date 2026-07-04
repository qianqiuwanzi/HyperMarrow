"""Re-export shim — canonical implementation lives in learning_core."""
from learning_core.rl_decision_helper import RLDecisionHelper, main as _main

__all__ = ["RLDecisionHelper"]

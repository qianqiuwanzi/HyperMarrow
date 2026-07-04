#!/usr/bin/env python3
"""Minimal smoke test for HyperMarrow memory + learning systems."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "openclaw-memory-system"))
sys.path.insert(0, str(Path(__file__).parent.parent / "openclaw-learning-system"))

PASS = 0
FAIL = 0

def check(name, condition):
    global PASS, FAIL
    if condition: PASS += 1; print(f"  PASS {name}")
    else: FAIL += 1; print(f"  FAIL {name}")

# ── Test 1: learning_core has real implementations ──────────────────────
print("\n1. learning_core imports")
from learning_core import QLearningAgent, RLDecisionHelper, MetaLearner, TransferLearner, SkillExtractor
a = QLearningAgent(state_space_size=100, action_space_size=7)
check("QLearningAgent create", a is not None)
a.add_experience("test", 2, reward=1.0, next_state="done")
check("QLearningAgent add_experience", len(a.experience_buffer) == 1)
a.batch_learn(batch_size=1)
check("QLearningAgent batch_learn", True)

m = MetaLearner()
check("MetaLearner create", m.state is not None)
t = TransferLearner()
check("TransferLearner create", t.feature_dim > 0)

# ── Test 2: memory_core shims work ──────────────────────────────────────
print("\n2. memory_core shim imports")
from memory_core import QLearningAgent as QL2, MetaLearner as ML2, KnowledgeGraph, WorkingMemoryDB, EpisodicMemoryDB, ProceduralMemory
a2 = QL2(state_space_size=100, action_space_size=7)
check("memory_core.QLearningAgent (shim)", type(a) is type(a2))
kg = KnowledgeGraph()
check("KnowledgeGraph create", kg.get_stats()["total_entities"] >= 0)
wm = WorkingMemoryDB()
check("WorkingMemoryDB create", wm is not None)
em = EpisodicMemoryDB()
check("EpisodicMemoryDB create", em is not None)
pm = ProceduralMemory()
check("ProceduralMemory create", pm is not None)

# ── Test 3: No circular import errors ───────────────────────────────────
print("\n3. No circular imports")
import learning_core; import memory_core
from memory_integration.decision_check import DecisionCheckPoint
check("DecisionCheckPoint import", True)
check("No ImportError", True)

# ── Summary ─────────────────────────────────────────────────────────────
print(f"\n{'='*40}")
print(f"Results: {PASS}/{PASS+FAIL} passed")
if FAIL == 0:
    print("SMOKE TEST PASSED")
else:
    print(f"{FAIL} TESTS FAILED")
    sys.exit(1)

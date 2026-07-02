#!/usr/bin/env python3
"""
Test all learning system components
"""

import sys
import os

# Add HyperMarrow root so both learning_core and memory_core are discoverable
_test_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_workspace = os.path.dirname(_test_root)
_parent   = os.path.dirname(_workspace)
sys.path.insert(0, _parent)


def test_q_learning_agent():
    """Test Q-Learning agent"""
    print("\n" + "="*60)
    print("Testing Q-Learning Agent")
    print("="*60)

    from learning_core import QLearningAgent

    agent = QLearningAgent(state_space_size=10, action_space_size=5)

    # Test state encoding
    state = agent.state_to_index("test_task_P1")
    print(f"State index: {state}")

    # Test action selection
    action = agent.get_action(state)
    print(f"Selected action: {action}")

    # Test Q-table update
    agent.update(state, action, reward=1.0, next_state=(state+1)%10)
    print(f"Q-value updated: {agent.q_table[state, action]:.3f}")

    return True


def test_rl_decision_helper():
    """Test RL decision helper"""
    print("\n" + "="*60)
    print("Testing RL Decision Helper")
    print("="*60)

    from learning_core import RLDecisionHelper

    rl = RLDecisionHelper()

    # Test recommendation (API: get_recommendation(state, available_actions))
    action, confidence = rl.get_recommendation(
        state="video_generation_P2b",
        available_actions=["follow_rule_strictly", "try_fix_three_times", "report_user"]
    )

    print(f"Recommended action: {action}")
    print(f"Confidence: {confidence:.2f}")

    return True


def test_decision_checkpoint():
    """Test decision checkpoint (thin wrapper)"""
    print("\n" + "="*60)
    print("Testing Decision Checkpoint")
    print("="*60)

    from learning_integration.decision_check import DecisionCheckPoint

    checkpoint = DecisionCheckPoint(enable_vector_db=False, enable_rl=True)

    result = checkpoint.check(
        action="try_fix_three_times",
        context={"task": "P2b download stuck", "task_type": "video_generation", "phase": "P2b"}
    )

    print(f"Procedural rules: {len(result.get('procedural_hints', []))}")
    print(f"RL recommendation: {result.get('rl_recommendation', {}).get('recommended_action', 'None')}")
    print(f"Warnings: {len(result.get('warnings', []))}")

    return True


def test_performance_analysis():
    """Test performance analysis"""
    print("\n" + "="*60)
    print("Testing Performance Analysis")
    print("="*60)

    from learning_core import QLearningAgent, ACTIONS

    agent = QLearningAgent(state_space_size=10, action_space_size=5)
    stats = agent.get_stats()

    print(f"Total experiences: {stats['total_experiences']}")
    print(f"States: {stats['n_states']}, Actions: {stats['n_actions']}")
    print(f"Q-values non-zero: {stats['nonzero_entries']}/{stats['total_entries']}")

    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("OpenClaw Learning System - Test Suite")
    print("="*60)

    tests = [
        ("Q-Learning Agent", test_q_learning_agent),
        ("RL Decision Helper", test_rl_decision_helper),
        ("Decision Checkpoint", test_decision_checkpoint),
        ("Performance Analysis", test_performance_analysis),
    ]

    results = []

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✓ PASS" if success else "✗ FAIL"))
        except Exception as e:
            results.append((name, f"✗ ERROR: {str(e)[:80]}"))

    print("\n" + "="*60)
    print("Test Results")
    print("="*60)

    for name, status in results:
        print(f"  {name}: {status}")

    passed = sum(1 for _, s in results if "PASS" in s)
    print(f"\nTotal: {passed}/{len(results)} passed")

if __name__ == "__main__":
    main()

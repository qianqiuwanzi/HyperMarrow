#!/usr/bin/env python3
"""
Test all learning system components
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_q_learning_agent():
    """Test Q-Learning agent"""
    print("\n" + "="*60)
    print("Testing Q-Learning Agent")
    print("="*60)
    
    from learning_core.q_learning_agent import QLearningAgent
    
    agent = QLearningAgent(state_size=10, action_size=5)
    
    # Test state encoding
    state = agent.get_state({"task": "test", "phase": "P1"})
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
    
    from learning_core.rl_decision_helper import RLDecisionHelper
    
    rl = RLDecisionHelper(workspace="./data")
    
    # Test recommendation
    recommendation = rl.get_recommendation({
        "task_type": "video_generation",
        "phase": "P2b",
        "error_history": False
    })
    
    print(f"Recommended action: {recommendation['recommended_action']}")
    print(f"Confidence: {recommendation['confidence']:.2f}")
    print(f"Reasoning: {recommendation['reasoning']}")
    
    # Test decision recording
    rl.record_decision(
        state="video_generation_P2b",
        action=recommendation['recommended_action'],
        outcome="success",
        reward=1.0
    )
    print("Decision recorded")
    
    return True

def test_decision_checkpoint():
    """Test decision checkpoint"""
    print("\n" + "="*60)
    print("Testing Decision Checkpoint")
    print("="*60)
    
    from integration.decision_check import DecisionCheckPoint
    
    checkpoint = DecisionCheckPoint(workspace="./data")
    
    result = checkpoint.check({
        "context": "P2b download stuck",
        "task": "video_generation",
        "phase": "P2b"
    })
    
    print(f"Procedural rules: {len(result.get('procedural_rules', []))}")
    print(f"RL recommendation: {result.get('rl_recommendation', {}).get('recommended_action', 'None')}")
    print(f"Warnings: {len(result.get('warnings', []))}")
    
    return True

def test_performance_analysis():
    """Test performance analysis"""
    print("\n" + "="*60)
    print("Testing Performance Analysis")
    print("="*60)
    
    from learning_core.rl_decision_helper import RLDecisionHelper
    
    rl = RLDecisionHelper(workspace="./data")
    
    # Analyze performance
    analysis = rl.analyze_performance()
    
    print(f"Total decisions: {analysis.get('total_decisions', 0)}")
    print(f"Success rate: {analysis.get('success_rate', 0):.1%}")
    
    if 'action_stats' in analysis:
        print("\nAction statistics:")
        for action, stats in analysis['action_stats'].items():
            print(f"  {action}: {stats['success_rate']:.1%} success ({stats['count']} uses)")
    
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
            results.append((name, f"✗ ERROR: {str(e)[:50]}"))
    
    print("\n" + "="*60)
    print("Test Results")
    print("="*60)
    
    for name, status in results:
        print(f"  {name}: {status}")
    
    passed = sum(1 for _, s in results if "PASS" in s)
    print(f"\nTotal: {passed}/{len(results)} passed")

if __name__ == "__main__":
    main()

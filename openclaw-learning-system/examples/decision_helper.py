#!/usr/bin/env python3
"""
Example: Decision Helper usage
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learning_core.rl_decision_helper import RLDecisionHelper

def main():
    print("\n" + "="*60)
    print("RL Decision Helper Example")
    print("="*60)
    
    # Initialize helper
    rl = RLDecisionHelper(workspace="./data")
    
    # Scenario 1: First-time decision
    print("\n[Scenario 1] First-time decision")
    print("-" * 40)
    
    context1 = {
        "task_type": "video_generation",
        "phase": "P2b",
        "error_history": False,
        "similar_cases": 0
    }
    
    rec1 = rl.get_recommendation(context1)
    print(f"Context: {context1}")
    print(f"Recommendation: {rec1['recommended_action']}")
    print(f"Confidence: {rec1['confidence']:.2f}")
    print(f"Reasoning: {rec1['reasoning']}")
    
    # Record the decision
    rl.record_decision(
        state=rl.get_state_key(context1),
        action=rec1['recommended_action'],
        outcome="success",
        reward=1.0
    )
    print("→ Decision recorded (success)")
    
    # Scenario 2: Error encountered
    print("\n[Scenario 2] Error encountered")
    print("-" * 40)
    
    context2 = {
        "task_type": "video_generation",
        "phase": "P2b",
        "error_history": True,
        "similar_cases": 2
    }
    
    rec2 = rl.get_recommendation(context2)
    print(f"Context: {context2}")
    print(f"Recommendation: {rec2['recommended_action']}")
    print(f"Confidence: {rec2['confidence']:.2f}")
    print(f"Reasoning: {rec2['reasoning']}")
    
    # Record the decision
    rl.record_decision(
        state=rl.get_state_key(context2),
        action=rec2['recommended_action'],
        outcome="success",
        reward=1.0
    )
    print("→ Decision recorded (success)")
    
    # Scenario 3: Performance analysis
    print("\n[Scenario 3] Performance Analysis")
    print("-" * 40)
    
    analysis = rl.analyze_performance()
    print(f"Total decisions: {analysis.get('total_decisions', 0)}")
    print(f"Success rate: {analysis.get('success_rate', 0):.1%}")
    
    if 'action_stats' in analysis:
        print("\nAction statistics:")
        for action, stats in sorted(analysis['action_stats'].items(), 
                                     key=lambda x: x[1]['success_rate'], 
                                     reverse=True):
            print(f"  {action}: {stats['success_rate']:.1%} success ({stats['count']} uses)")

if __name__ == "__main__":
    main()

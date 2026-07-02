#!/usr/bin/env python3
"""
Example: Basic Q-Learning usage
"""

import sys
import os

# Add project root so both learning_core and memory_core are discoverable
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # openclaw-learning-system/
_workspace = os.path.dirname(_project_root)                                   # HyperMarrow/
sys.path.insert(0, _workspace)

from learning_core.q_learning_agent import QLearningAgent

def main():
    print("\n" + "="*60)
    print("Q-Learning Basic Example")
    print("="*60)
    
    # Create agent
    agent = QLearningAgent(
        state_size=100,
        action_size=7,
        alpha=0.1,   # Learning rate
        gamma=0.9,   # Discount factor
        epsilon=0.1  # Exploration rate
    )
    
    print(f"Q-table shape: {agent.q_table.shape}")
    print(f"Initial Q-values: min={agent.q_table.min():.3f}, max={agent.q_table.max():.3f}")
    
    # Simulate learning episodes
    print("\nTraining for 100 episodes...")
    
    for episode in range(100):
        # Get state from context
        state = agent.get_state({"task": "video_gen", "phase": f"P{episode % 5}"})
        
        # Select action
        action = agent.get_action(state)
        
        # Simulate reward
        reward = 1.0 if action in [0, 3] else -0.5  # Good actions: 0, 3
        
        # Update Q-table
        next_state = (state + 1) % 100
        agent.update(state, action, reward, next_state)
    
    print(f"Trained Q-values: min={agent.q_table.min():.3f}, max={agent.q_table.max():.3f}")
    
    # Test learned policy
    print("\nTesting learned policy:")
    
    test_contexts = [
        {"task": "video_gen", "phase": "P1"},
        {"task": "data_analysis", "phase": "P2"},
        {"task": "video_gen", "phase": "P3"},
    ]
    
    for context in test_contexts:
        state = agent.get_state(context)
        action = agent.get_action(state, training=False)  # Greedy policy
        action_name = {0: "follow_rule", 1: "try_fix", 2: "ask_user", 
                       3: "use_tool", 4: "create_tool", 5: "switch", 6: "skip"}
        
        print(f"  Context: {context} → Action: {action_name.get(action, action)}")
    
    # Save Q-table
    agent.save_q_table()
    print("\nQ-table saved to data/q_table.json")

if __name__ == "__main__":
    main()

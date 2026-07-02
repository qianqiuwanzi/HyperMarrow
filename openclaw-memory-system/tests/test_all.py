#!/usr/bin/env python3
"""
Test all memory system components
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set HF environment
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = './data/cache/huggingface/hub'
os.environ['HF_HOME'] = './data/cache/huggingface'


def test_procedural_memory():
    """Test procedural memory system"""
    print("\n" + "="*60)
    print("Testing Procedural Memory")
    print("="*60)

    from memory_core.procedural_memory import ProceduralMemory

    pm = ProceduralMemory("./data")

    # Test check context
    rules = pm.check_context("P2b 下载卡住")
    print(f"Found {len(rules)} matching rules")

    for rule in rules:
        print(f"  - [Level {rule['level']}] {rule['rule_name']}")

    return True


def test_rl_system():
    """Test RL system"""
    print("\n" + "="*60)
    print("Testing Reinforcement Learning")
    print("="*60)

    from memory_core.rl_decision_helper import RLDecisionHelper

    rl = RLDecisionHelper("./data")

    # Test recommendation
    recommendation = rl.get_recommendation({
        "task_type": "video_generation",
        "current_phase": "P2b"
    })

    print(f"Recommended action: {recommendation['action']}")
    print(f"Confidence: {recommendation['confidence']:.2f}")

    return True


def test_vector_db():
    """Test vector database"""
    print("\n" + "="*60)
    print("Testing Vector Database")
    print("="*60)

    try:
        from memory_core.vector_memory_db import VectorMemoryDB

        db = VectorMemoryDB("./data/chromadb")

        # Test search (will need model download on first run)
        print("Searching...")
        results = db.search("daily-video-factory", n_results=2)

        if results['ids'][0]:
            print(f"Found {len(results['ids'][0])} results")
            for doc in results['documents'][0]:
                print(f"  - {doc[:50]}...")
        else:
            print("No results (database empty - run init first)")

        return True
    except Exception as e:
        print(f"Error: {e}")
        print("Note: Vector DB requires model download on first run")
        return False


def test_decision_checkpoint():
    """Test decision checkpoint"""
    print("\n" + "="*60)
    print("Testing Decision Checkpoint")
    print("="*60)

    from memory_integration.decision_check import DecisionCheckPoint

    checkpoint = DecisionCheckPoint("./data")

    result = checkpoint.check(
        "P2b 下载卡住",
        task_type="使用 daily-video-factory",
        phase="P2b"
    )

    print(f"Procedural rules: {len(result['procedural_rules'])}")
    print(f"Warnings: {len(result['warnings'])}")

    return True

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("OpenClaw Memory System - Test Suite")
    print("="*60)
    
    tests = [
        ("Procedural Memory", test_procedural_memory),
        ("Reinforcement Learning", test_rl_system),
        ("Vector Database", test_vector_db),
        ("Decision Checkpoint", test_decision_checkpoint),
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

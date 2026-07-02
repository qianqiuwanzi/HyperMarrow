#!/usr/bin/env python3
# Test decision check point

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = 'D:/OpenClaw/workspace/.cache/huggingface/hub'
os.environ['HF_HOME'] = 'D:/OpenClaw/workspace/.cache/huggingface'

from decision_check import DecisionCheckPoint

# Create checkpoint
checkpoint = DecisionCheckPoint()

# Test check
print("\n" + "="*60)
print("DECISION CHECKPOINT TEST")
print("="*60)

context = {
    "context": "daily-video-factory P2b download stuck",
    "task": "use daily-video-factory",
    "phase": "P2b",
    "action": "switch_skill"
}

result = checkpoint.check(context)
print(f"\nProcedural Rules: {len(result['procedural_rules'])}")
print(f"RL Recommendation: {result['rl_recommendation']}")
print(f"Warnings: {len(result['warnings'])}")
print(f"\nReasoning:")
for r in result.get('warnings', []):
    print(f"  - {r}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)

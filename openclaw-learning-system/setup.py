#!/usr/bin/env python3
"""
OpenClaw Learning System Setup
Pip name: openclaw-learning-system
Import:
    from learning_core.q_learning_agent import QLearningAgent
    from learning_core.rl_decision_helper import RLDecisionHelper
"""

from setuptools import setup, find_packages

# Find packages
packages = find_packages(include=['learning_core', 'learning_integration'])

setup(
    name="openclaw-learning-system",
    version="1.0.0",
    description="A pluggable reinforcement learning decision system for AI agents",
    author="OpenClaw",
    packages=packages,
    package_dir={
        'learning_core': 'learning_core',
        'learning_integration': 'learning_integration',
    },
    install_requires=[
        "openclaw-memory-system>=1.0.0",
        "numpy>=1.21.0",
    ],
    python_requires=">=3.10",
)

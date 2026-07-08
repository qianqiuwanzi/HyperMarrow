#!/usr/bin/env python3
"""
OpenClaw Memory System Setup
Pip name: openclaw-memory-system
Import:
    from memory_core.vector_memory_db import VectorMemoryDB
    from memory_integration.decision_check import DecisionCheckPoint
"""

from setuptools import setup, find_packages

setup(
    name="openclaw-memory-system",
    version="2.0.0",
    description="A pluggable memory and learning system for AI agents",
    author="OpenClaw",
    packages=find_packages(where='.'),
    package_dir={'': '.'},
    install_requires=[
        "chromadb>=0.4.0",
        "sentence-transformers>=2.2.0",
        "numpy>=1.21.0",
        "openclaw-learning-system>=1.0.0",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "memory-db=memory_cli.vector_db:main",
        ]
    },
)

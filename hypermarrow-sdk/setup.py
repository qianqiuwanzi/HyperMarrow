#!/usr/bin/env python3
"""HyperMarrow SDK — Agent 集成开发包"""

from setuptools import setup, find_packages

setup(
    name="hypermarrow-sdk",
    version="2.0.0",
    description="HyperMarrow 智商藏不住 Agent SDK — 记忆与学习系统集成",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="HyperMarrow Team",
    url="https://github.com/openclaw/hypermarrow",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28.0",
        "numpy>=1.24.0",
    ],
    extras_require={
        "full": [
            "torch>=2.0.0",
            "sentence-transformers>=2.2.0",
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)

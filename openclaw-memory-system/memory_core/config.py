"""
Configuration management for OpenClaw Memory System.

This module provides workspace path management and environment setup.
"""

from pathlib import Path
import os


def get_workspace() -> Path:
    """
    Get OpenClaw workspace root directory.
    
    Returns:
        Path to workspace root (D:\OpenClaw\workspace)
    """
    # Try environment variable first
    if "OPENCLAW_WORKSPACE" in os.environ:
        return Path(os.environ["OPENCLAW_WORKSPACE"])
    
    # Default: parent of this file's package directory
    # memory_core/config.py → memory_core/ → openclaw-memory-system/ → packages/ → workspace/
    return Path(__file__).parent.parent.parent.parent


def get_memory_dir() -> Path:
    """
    Get memory directory path.
    
    Returns:
        Path to memory directory (workspace/memory)
    """
    return get_workspace() / "memory"


def get_cache_dir() -> Path:
    """
    Get cache directory path.
    
    Returns:
        Path to cache directory (workspace/.cache)
    """
    return get_workspace() / ".cache"


def get_hf_cache_dir() -> Path:
    """
    Get HuggingFace cache directory.
    
    Returns:
        Path to HF cache (workspace/.cache/huggingface)
    """
    return get_cache_dir() / "huggingface"


def setup_hf_mirror():
    """
    Setup HuggingFace mirror for China users.
    
    This must be called BEFORE importing sentence_transformers.
    """
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    os.environ['HF_HUB_ENDPOINT'] = 'https://hf-mirror.com'
    
    # Set cache paths
    hf_cache = get_hf_cache_dir()
    os.environ['HUGGINGFACE_HUB_CACHE'] = str(hf_cache / 'hub')
    os.environ['HF_HOME'] = str(hf_cache)
    
    # Create cache directory
    hf_cache.mkdir(parents=True, exist_ok=True)
    
    print(f"[Config] HF mirror enabled: https://hf-mirror.com")
    print(f"[Config] HF cache: {hf_cache}")


# Version info
__version__ = "1.0.0"

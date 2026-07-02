# Re-export config functions from memory-core
# learning-system shares the same workspace/config as memory-system
from memory_core.config import (
    get_workspace,
    get_memory_dir,
    get_cache_dir,
    get_hf_cache_dir,
    setup_hf_mirror,
)

__all__ = ["get_workspace", "get_memory_dir", "get_cache_dir", "get_hf_cache_dir", "setup_hf_mirror"]

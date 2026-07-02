"""Episodic Memory — P3 Foundational Memory Type (import facade)."""
from .episodic_memory_db import EpisodicMemoryDB
from .config import get_data_dir

DATA_DIR = get_data_dir()
EPISODES_FILE = DATA_DIR / "episodes.json"

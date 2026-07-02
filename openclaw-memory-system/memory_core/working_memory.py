"""Working Memory — P1 Foundational Memory Type (import facade)."""
from .working_memory_db import WorkingMemoryDB
from .config import get_data_dir

DATA_DIR = get_data_dir()
WORKING_MEM_FILE = DATA_DIR / "working_memory.json"

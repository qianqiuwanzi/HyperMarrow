"""
Configuration for openclaw-learning-system (independent).
This module does NOT import from memory_core.
"""

from pathlib import Path
from typing import Optional

# Default data directory
DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"


def get_learning_data_dir() -> Path:
    """Get the data directory for learning system."""
    return DEFAULT_DATA_DIR


def setup_learning_config(data_dir: Optional[Path] = None):
    """Setup configuration for learning system."""
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create minimal config file if not exists
    config_path = data_dir / "learning_config.json"
    if not config_path.exists():
        config = {
            "version": "1.0",
            "created_at": __import__("datetime").datetime.now().isoformat(),
            "q_table_size": 50,
            "action_size": 5,
            "learning_rate": 0.1,
            "discount_factor": 0.9,
            "exploration_rate": 0.1,
        }
        with open(config_path, "w", encoding="utf-8") as f:
            import json
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    return config_path


# Initialize on import
setup_learning_config()

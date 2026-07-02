"""
OpenClaw Memory System — P1/P2/P3 Foundational Memory Types + Extended Cognition

P1: WorkingMemoryDB   — 上下文缓冲区，update_context() / get_active_context()
P2: VectorMemoryDB    — 向量记忆 + 时间索引 (created_at / days_filter)
P3: EpisodicMemoryDB  — 情景记忆 {what,when,context,outcome,emotion}
KG: KnowledgeGraph    — 知识图谱 (实体-关系)
"""

from .config import get_workspace, get_memory_dir, get_cache_dir, get_hf_cache_dir, get_data_dir, setup_hf_mirror
from .vector_memory_db import VectorMemoryDB
from .procedural_memory import ProceduralMemory
from .q_learning_agent import QLearningAgent, ACTIONS, ACTION_MAP
from .rl_decision_helper import RLDecisionHelper
from .working_memory import WorkingMemoryDB
from .episodic_memory import EpisodicMemoryDB
from .knowledge_graph import KnowledgeGraph
from .perception_channels import PerceptionOrchestrator, Observation
from .metacognition_monitor import MetacognitionMonitor
from .transfer_learner import TransferLearner
from .memory_consolidator import MemoryConsolidator
from .prospective_memory import ProspectiveMemory
from .neural_state import NeuralAgent
from .world_model import WorldModel, ModelBasedAgent
from .meta_learner import MetaLearner, SkillExtractor
from .agent_registry import AgentRegistry, AgentBundle

__all__ = [
    # P1: Working Memory
    "WorkingMemoryDB",
    # P2: Semantic + Temporal Memory
    "VectorMemoryDB",
    # P3: Episodic Memory
    "EpisodicMemoryDB",
    # Knowledge Graph
    "KnowledgeGraph",
    # Perception
    "PerceptionOrchestrator",
    "Observation",
    # Metacognition
    "MetacognitionMonitor",
    # Transfer Learning
    "TransferLearner",
    # Memory Consolidation (LTP/LTD)
    "MemoryConsolidator",
    # Prospective Memory
    "ProspectiveMemory",
    # Neural State (Wave 1)
    "NeuralAgent",
    # World Model (Wave 2)
    "WorldModel",
    "ModelBasedAgent",
    # Meta-Learning (Wave 3)
    "MetaLearner",
    "SkillExtractor",
    # Multi-Agent
    "AgentRegistry",
    "AgentBundle",
    # Procedural Memory
    "ProceduralMemory",
    # RL (canonical location)
    "QLearningAgent",
    "RLDecisionHelper",
    "ACTIONS",
    "ACTION_MAP",
    # Config
    "get_workspace",
    "get_memory_dir",
    "get_cache_dir",
    "get_hf_cache_dir",
    "get_data_dir",
    "setup_hf_mirror",
]

__version__ = "2.0.0"

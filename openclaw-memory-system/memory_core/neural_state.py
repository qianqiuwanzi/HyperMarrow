"""
Neural State Encoder & Q-Function — 神经状态表示与Q函数

Wave 1 infrastructure for learned distributed representations.
All PyTorch components are OPTIONAL — graceful fallback to tabular methods.

Architecture:
  StateEncoder: structured dict → 64-dim continuous embedding
  QFunction:    (embedding, action_onehot) → Q-value scalar
"""
import json
import numpy as np
from pathlib import Path
from typing import Optional

# ── Optional PyTorch detection ───────────────────────────────────────────────
_HAS_TORCH = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    _HAS_TORCH = True
except ImportError:
    pass


# ── Feature dimension constants ──────────────────────────────────────────────
# Structured state features (must match state dict keys used in practice)
_STATE_FEATURE_KEYS = [
    "task_type",      # categorical → one-hot (10 categories)
    "phase",          # categorical → one-hot (8 phases)
    "error_type",     # categorical → one-hot (8 error types)
    "attempts",       # numeric → scaled
    "tool_count",     # numeric
    "emotion",        # categorical → one-hot (4 emotions)
    "wm_task",        # text → hashed
    "wm_goal",        # text → hashed
]
_STATE_INPUT_DIM = 10 + 8 + 8 + 1 + 1 + 4 + 1 + 1  # = 34
_EMBEDDING_DIM = 64
_ACTION_DIM = 7


# ── Structured State Serializer (no PyTorch needed) ──────────────────────────

def _serialize_state(state: dict) -> np.ndarray:
    """
    Convert a structured state dict to a fixed-size float vector.
    Used as input to both tabular fallback and neural encoder.

    Returns:
        numpy array of shape (_STATE_INPUT_DIM,)
    """
    vec = np.zeros(_STATE_INPUT_DIM, dtype=np.float32)
    offset = 0

    # task_type one-hot (10)
    task_types = ["video_generation", "code_review", "research",
                  "memory_management", "decision_making", "debugging",
                  "data_processing", "deployment", "testing", "unknown"]
    task = str(state.get("task_type", "unknown")).lower().replace(" ", "_")
    for i, t in enumerate(task_types):
        if t in task:
            vec[offset + i] = 1.0
            break
    else:
        vec[offset + 9] = 1.0  # unknown
    offset += 10

    # phase one-hot (8)
    phases = ["P0", "P1", "P2a", "P2b", "P2", "P3", "P4", "P5"]
    phase = str(state.get("phase", "")).upper()
    for i, p in enumerate(phases):
        if p in phase:
            vec[offset + i] = 1.0
            break
    offset += 8

    # error_type one-hot (8)
    errors = ["import_error", "timeout", "download_stuck",
              "format_unsupported", "script_not_found", "network_error",
              "permission_denied", "out_of_memory"]
    error = str(state.get("error_type", "")).lower()
    for i, e in enumerate(errors):
        if e in error:
            vec[offset + i] = 1.0
            break
    offset += 8

    # attempts (numeric, scaled to [0,1])
    attempts = float(state.get("attempts", 0))
    vec[offset] = min(1.0, attempts / 10.0)
    offset += 1

    # tool_count (numeric)
    tools = state.get("tools", [])
    if isinstance(tools, list):
        vec[offset] = min(1.0, len(tools) / 10.0)
    offset += 1

    # emotion one-hot (4)
    emotions = ["positive", "negative", "neutral", "mixed"]
    emo = str(state.get("emotion", "neutral")).lower()
    for i, e in enumerate(emotions):
        if e in emo:
            vec[offset + i] = 1.0
            break
    offset += 4

    # wm_task (hashed to [0,1])
    wm_task = str(state.get("wm_task", ""))
    vec[offset] = (hash(wm_task) % 1000) / 1000.0 if wm_task else 0.0
    offset += 1

    # wm_goal (hashed to [0,1])
    wm_goal = str(state.get("wm_goal", ""))
    vec[offset] = (hash(wm_goal) % 1000) / 1000.0 if wm_goal else 0.0

    return vec


# ── PyTorch Neural State Encoder ─────────────────────────────────────────────

if _HAS_TORCH:

    class StateEncoder(nn.Module):
        """
        神经状态编码器 — 结构化状态 → 连续嵌入向量。

        架构: Input(34) → Linear(128) → ReLU → Linear(128) → ReLU → Linear(64)
        输出: L2-normalized 64-dim embedding
        """

        def __init__(self, input_dim: int = _STATE_INPUT_DIM,
                     hidden_dim: int = 128,
                     output_dim: int = _EMBEDDING_DIM):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, output_dim),
            )

        def forward(self, x):
            """x: (batch, input_dim) tensor or numpy array"""
            if isinstance(x, np.ndarray):
                x = torch.from_numpy(x).float()
            emb = self.net(x)
            return F.normalize(emb, p=2, dim=-1)  # unit sphere

    class QFunction(nn.Module):
        """
        神经 Q 函数 — (state_embedding, action_onehot) → Q-value。

        架构: Input(64 + 7) → Linear(128) → ReLU → Linear(64) → ReLU → Linear(1)
        """

        def __init__(self, embedding_dim: int = _EMBEDDING_DIM,
                     action_dim: int = _ACTION_DIM,
                     hidden_dim: int = 128):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(embedding_dim + action_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, 1),
            )

        def forward(self, state_emb, action_idx):
            """
            Args:
                state_emb: (batch, embedding_dim) or (embedding_dim,)
                action_idx: int or (batch,) tensor of action indices
            Returns:
                Q-value(s): scalar or (batch, 1)
            """
            if state_emb.dim() == 1:
                state_emb = state_emb.unsqueeze(0)
            batch = state_emb.shape[0]

            # One-hot encode actions
            if isinstance(action_idx, int):
                action_idx = torch.tensor([action_idx])
            if action_idx.dim() == 0:
                action_idx = action_idx.unsqueeze(0)
            action_onehot = F.one_hot(action_idx.long(), num_classes=_ACTION_DIM).float()
            if action_onehot.shape[0] != batch:
                action_onehot = action_onehot.expand(batch, -1)

            x = torch.cat([state_emb, action_onehot], dim=-1)
            return self.net(x)


# ── Unified NeuralAgent wrapper (no PyTorch needed for interface) ────────────

class NeuralAgent:
    """
    神经 RL 智能体 — 统一神经编码器和 Q 函数的轻量包装器。

    当 PyTorch 可用时使用神经网络，不可用时回退到表格方法。
    """

    def __init__(self, input_dim: int = _STATE_INPUT_DIM,
                 embedding_dim: int = _EMBEDDING_DIM,
                 action_dim: int = _ACTION_DIM):
        self.input_dim = input_dim
        self.embedding_dim = embedding_dim
        self.action_dim = action_dim
        self.torch_available = _HAS_TORCH

        if _HAS_TORCH:
            self.encoder = StateEncoder(input_dim, output_dim=embedding_dim)
            self.q_function = QFunction(embedding_dim, action_dim)
            self.encoder.eval()
            self.q_function.eval()
        else:
            self.encoder = None
            self.q_function = None

        # Training state
        self._training_losses: list = []
        self._train_steps = 0

    def encode(self, state) -> np.ndarray:
        """
        Encode a state (dict or numpy vector) to embedding.
        Always works: uses PyTorch if available, else raw serialized vector.
        """
        if isinstance(state, dict):
            vec = _serialize_state(state)
        elif isinstance(state, np.ndarray):
            vec = state.astype(np.float32)
        else:
            vec = np.zeros(self.input_dim, dtype=np.float32)

        if self.torch_available and self.encoder is not None:
            with torch.no_grad():
                t = torch.from_numpy(vec).float().unsqueeze(0)
                emb = self.encoder(t).squeeze(0)
                return emb.numpy()

        # Fallback: return raw serialized vector normalized
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def predict_q(self, state_emb: np.ndarray, action_idx: int) -> float:
        """
        Predict Q-value for (state_embedding, action).
        """
        if self.torch_available and self.q_function is not None:
            with torch.no_grad():
                t_emb = torch.from_numpy(state_emb).float()
                q = self.q_function(t_emb, action_idx)
                return float(q.squeeze().item())
        return 0.0  # Fallback: no prediction

    def predict_all_q(self, state) -> np.ndarray:
        """Predict Q-values for all actions for a given state."""
        emb = self.encode(state)
        qs = np.zeros(self.action_dim, dtype=np.float32)
        for a in range(self.action_dim):
            qs[a] = self.predict_q(emb, a)
        return qs

    def train_step(self, state, action_idx: int, target_q: float,
                   learning_rate: float = 0.001) -> float:
        """
        Single supervised training step. Returns loss value.

        Args:
            state: dict or serialized vector
            action_idx: which action was taken
            target_q: TD target Q-value
            learning_rate: gradient step size
        """
        if not self.torch_available:
            return 0.0

        self.encoder.train()
        self.q_function.train()

        if isinstance(state, dict):
            vec = _serialize_state(state)
        else:
            vec = state.astype(np.float32)

        t_vec = torch.from_numpy(vec).float().unsqueeze(0)
        emb = self.encoder(t_vec)
        pred = self.q_function(emb, action_idx)
        target = torch.tensor([[target_q]], dtype=torch.float32)

        loss = F.mse_loss(pred, target)

        # Simple SGD step
        with torch.no_grad():
            for param in list(self.encoder.parameters()) + list(self.q_function.parameters()):
                if param.grad is not None:
                    param.grad.zero_()

        loss.backward()

        with torch.no_grad():
            for param in list(self.encoder.parameters()) + list(self.q_function.parameters()):
                if param.grad is not None:
                    param -= learning_rate * param.grad
                    param.grad.zero_()

        self._train_steps += 1
        loss_val = float(loss.item())
        self._training_losses.append(loss_val)

        self.encoder.eval()
        self.q_function.eval()
        return loss_val

    def save(self, path: str):
        """Save model weights to file."""
        if not self.torch_available:
            return
        state = {
            "encoder": self.encoder.state_dict(),
            "q_function": self.q_function.state_dict(),
            "train_steps": self._train_steps,
            "training_losses": self._training_losses,
        }
        torch.save(state, path)
        print(f"[NeuralAgent] Saved to {path}")

    def load(self, path: str) -> bool:
        """Load model weights from file."""
        if not self.torch_available or not Path(path).exists():
            return False
        state = torch.load(path, map_location="cpu", weights_only=False)
        self.encoder.load_state_dict(state["encoder"])
        self.q_function.load_state_dict(state["q_function"])
        self._train_steps = state.get("train_steps", 0)
        self._training_losses = state.get("training_losses", [])
        self.encoder.eval()
        self.q_function.eval()
        print(f"[NeuralAgent] Loaded from {path} (step={self._train_steps})")
        return True

    def get_stats(self) -> dict:
        return {
            "torch_available": self.torch_available,
            "train_steps": self._train_steps,
            "recent_loss": round(self._training_losses[-1], 6) if self._training_losses else None,
            "avg_loss_100": round(np.mean(self._training_losses[-100:]), 6) if self._training_losses else None,
            "input_dim": self.input_dim,
            "embedding_dim": self.embedding_dim,
        }


# ── Example ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"PyTorch available: {_HAS_TORCH}")
    print(f"State input dim: {_STATE_INPUT_DIM}")

    # Test state serialization
    state = {
        "task_type": "video_generation",
        "phase": "P2b",
        "error_type": "timeout",
        "attempts": 3,
        "tools": ["daily-video-factory", "cover-generator"],
        "emotion": "negative",
        "wm_task": "下载素材",
        "wm_goal": "完成P2b",
    }
    vec = _serialize_state(state)
    assert len(vec) == _STATE_INPUT_DIM, f"Expected {_STATE_INPUT_DIM}, got {len(vec)}"
    print(f"Serialized vector: shape={vec.shape}, nonzero={np.count_nonzero(vec)}")

    # Test NeuralAgent
    agent = NeuralAgent()
    emb = agent.encode(state)
    assert len(emb) == _EMBEDDING_DIM, f"Expected {_EMBEDDING_DIM}, got {len(emb)}"
    print(f"Embedding: shape={emb.shape}, norm={np.linalg.norm(emb):.3f}")

    qs = agent.predict_all_q(state)
    assert len(qs) == _ACTION_DIM
    print(f"Q-values: {qs.round(4)}")

    if _HAS_TORCH:
        # Test training step
        loss = agent.train_step(state, action_idx=2, target_q=1.0, learning_rate=0.01)
        print(f"Training loss: {loss:.6f}")
        print(f"Stats: {agent.get_stats()}")

    print(f"\n[NeuralState] Serialization + Inference: PASSED")

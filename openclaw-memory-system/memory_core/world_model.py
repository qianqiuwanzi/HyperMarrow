"""
World Model & Active Inference — 世界模型 + 主动推理

Wave 2: Predictive dynamics and curiosity-driven planning.

WorldModel:   learns P(s_{t+1}, r_t | s_t, a_t) from experience
ActiveInference: simulates actions internally, minimizes expected free energy

Architecture:
  WorldModel:  (emb_64 + action_7) → MLP → (next_emb_64, reward_scalar)
  Ensemble:    multiple forward passes with dropout for uncertainty estimation
  Planner:     for each action, simulate → score by EFE → select best
"""
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

# ── Optional PyTorch ─────────────────────────────────────────────────────────
_HAS_TORCH = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    _HAS_TORCH = True
except ImportError:
    pass

_EMBEDDING_DIM = 64
_ACTION_DIM = 7


# ═══════════════════════════════════════════════════════════════════════════════
# World Model
# ═══════════════════════════════════════════════════════════════════════════════

if _HAS_TORCH:

    class WorldModelNN(nn.Module):
        """
        世界模型神经网络 — 预测下一个状态和奖励。

        输入:  (state_embedding_64, action_onehot_7) = 71 dims
        输出:  (next_state_embedding_64, reward_scalar)
        """

        def __init__(self, embedding_dim: int = _EMBEDDING_DIM,
                     action_dim: int = _ACTION_DIM,
                     hidden_dim: int = 256):
            super().__init__()
            input_dim = embedding_dim + action_dim
            self.shared = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.1),
            )
            self.state_head = nn.Linear(hidden_dim, embedding_dim)
            self.reward_head = nn.Sequential(
                nn.Linear(hidden_dim, 64),
                nn.ReLU(),
                nn.Linear(64, 1),
            )

        def forward(self, state_emb, action_idx, dropout_active=False):
            """
            Args:
                state_emb: (batch, embedding_dim)
                action_idx: (batch,) or int
                dropout_active: if True, keep dropout on for uncertainty estimation
            Returns:
                next_state_emb: (batch, embedding_dim)
                predicted_reward: (batch, 1)
            """
            if state_emb.dim() == 1:
                state_emb = state_emb.unsqueeze(0)
            batch = state_emb.shape[0]

            if isinstance(action_idx, int):
                action_idx = torch.tensor([action_idx] * batch)
            if action_idx.dim() == 0:
                action_idx = action_idx.unsqueeze(0)
            action_onehot = F.one_hot(action_idx.long(), num_classes=_ACTION_DIM).float()
            if action_onehot.shape[0] == 1 and batch > 1:
                action_onehot = action_onehot.expand(batch, -1)

            x = torch.cat([state_emb, action_onehot], dim=-1)

            if dropout_active:
                h = self.shared(x)
            else:
                h = self.shared(x)

            next_state = self.state_head(h)
            reward = self.reward_head(h)
            return next_state, reward


class WorldModel:
    """
    世界模型 — 学习环境动力学 P(s', r | s, a)。

    用法:
        wm = WorldModel()
        wm.train_step(s_emb, action, next_s_emb, reward)
        next_s, reward, uncertainty = wm.predict(s_emb, action)
    """

    def __init__(self, embedding_dim: int = _EMBEDDING_DIM,
                 action_dim: int = _ACTION_DIM):
        self.embedding_dim = embedding_dim
        self.action_dim = action_dim
        self.torch_available = _HAS_TORCH

        if _HAS_TORCH:
            self.model = WorldModelNN(embedding_dim, action_dim)
            self.model.eval()
        else:
            self.model = None

        self._train_steps = 0
        self._state_losses: list = []
        self._reward_losses: list = []
        self._ensemble_samples = 5  # Number of MC dropout passes for uncertainty

    def predict(self, state_emb: np.ndarray, action_idx: int,
                estimate_uncertainty: bool = True) -> Tuple[np.ndarray, float, float]:
        """
        预测执行 action 后的下一个状态和奖励。

        使用 MC Dropout (train mode + no_grad) 估计不确定性。

        Returns:
            (next_state_emb, predicted_reward, uncertainty)
        """
        if not self.torch_available:
            return state_emb, 0.0, 0.0

        t_emb = torch.from_numpy(state_emb.astype(np.float32))

        if estimate_uncertainty:
            # MC dropout: keep model in train() so dropout stays active
            self.model.train()
            with torch.no_grad():
                rewards = []
                states = []
                for _ in range(self._ensemble_samples):
                    ns, r = self.model(t_emb, action_idx, dropout_active=True)
                    rewards.append(float(r.squeeze().item()))
                    states.append(ns.squeeze(0).numpy())
            self.model.eval()
            reward_mean = float(np.mean(rewards))
            reward_std = float(np.std(rewards))
            state_mean = np.mean(states, axis=0)
            return state_mean, reward_mean, reward_std
        else:
            self.model.eval()
            with torch.no_grad():
                ns, r = self.model(t_emb, action_idx, dropout_active=False)
            return (
                ns.squeeze(0).numpy(),
                float(r.squeeze().item()),
                0.0,
            )

    def simulate(self, state_emb: np.ndarray, action_idx: int,
                 steps: int = 1) -> list:
        """
        内部模拟：从当前状态出发，模拟执行 action_idx 后 steps 步的轨迹。

        Returns:
            [(next_state_emb, reward, uncertainty), ...] for each step
        """
        trajectory = []
        current = state_emb.copy()
        for _ in range(steps):
            ns, r, u = self.predict(current, action_idx, estimate_uncertainty=True)
            trajectory.append((ns, r, u))
            current = ns
        return trajectory

    def train_step(self, state_emb: np.ndarray, action_idx: int,
                   next_state_emb: np.ndarray, reward: float,
                   learning_rate: float = 0.001) -> dict:
        """
        单步训练世界模型。

        Returns:
            {state_loss, reward_loss, total_loss}
        """
        if not self.torch_available:
            return {"state_loss": 0.0, "reward_loss": 0.0, "total_loss": 0.0}

        self.model.train()

        t_s = torch.from_numpy(state_emb.astype(np.float32)).unsqueeze(0)
        t_ns = torch.from_numpy(next_state_emb.astype(np.float32)).unsqueeze(0)
        t_r = torch.tensor([[reward]], dtype=torch.float32)

        pred_ns, pred_r = self.model(t_s, action_idx, dropout_active=True)

        state_loss = F.mse_loss(pred_ns, t_ns)
        reward_loss = F.mse_loss(pred_r, t_r)
        total_loss = state_loss + reward_loss

        self.model.zero_grad()
        total_loss.backward()

        with torch.no_grad():
            for param in self.model.parameters():
                if param.grad is not None:
                    param -= learning_rate * param.grad

        self._train_steps += 1
        sl = float(state_loss.item())
        rl = float(reward_loss.item())
        self._state_losses.append(sl)
        self._reward_losses.append(rl)

        self.model.eval()
        return {"state_loss": sl, "reward_loss": rl, "total_loss": sl + rl}

    def save(self, path: str):
        if not self.torch_available:
            return
        torch.save({
            "model": self.model.state_dict(),
            "train_steps": self._train_steps,
        }, path)

    def load(self, path: str) -> bool:
        if not self.torch_available or not Path(path).exists():
            return False
        data = torch.load(path, map_location="cpu", weights_only=False)
        self.model.load_state_dict(data["model"])
        self._train_steps = data.get("train_steps", 0)
        self.model.eval()
        return True

    def get_stats(self) -> dict:
        n = min(50, len(self._state_losses))
        return {
            "train_steps": self._train_steps,
            "recent_state_loss": round(np.mean(self._state_losses[-n:]), 6) if self._state_losses else None,
            "recent_reward_loss": round(np.mean(self._reward_losses[-n:]), 6) if self._reward_losses else None,
            "torch_available": self.torch_available,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Active Inference Planner
# ═══════════════════════════════════════════════════════════════════════════════

class ActiveInferencePlanner:
    """
    主动推理规划器 — 用世界模型内部模拟来选择动作。

    预期自由能 (EFE):
      EFE(a) = -expected_reward(a) - λ × information_gain(a)
      information_gain(a) ≈ uncertainty of prediction (reward_std)

    λ 控制探索-利用权衡:
      λ 高 → 更多探索（偏好不确定性高的动作）
      λ 低 → 更多利用（偏好预测奖励高的动作）
    """

    def __init__(self, world_model: WorldModel,
                 exploration_weight: float = 0.3,
                 planning_horizon: int = 1):
        self.wm = world_model
        self.exploration_weight = exploration_weight
        self.planning_horizon = planning_horizon
        self._plan_count = 0
        self._action_stats = {i: {"selected": 0, "avg_efe": 0.0}
                              for i in range(_ACTION_DIM)}

    def plan(self, state_emb: np.ndarray,
             q_values: np.ndarray = None) -> Tuple[int, dict]:
        """
        规划：对每个动作模拟其后果，选择 EFE 最小的动作。

        Args:
            state_emb: 当前状态的嵌入向量
            q_values: 可选，已有的 Q 值估计（用于引导）

        Returns:
            (selected_action, plan_details)
        """
        action_scores = []
        for a in range(_ACTION_DIM):
            ns, pred_r, uncertainty = self.wm.predict(state_emb, a,
                                                        estimate_uncertainty=True)

            # Expected Free Energy: minimize = maximize negative EFE
            # EFE = -(expected_reward) - exploration_weight × information_gain
            info_gain = uncertainty  # Higher uncertainty = more to learn
            efe = -(pred_r + self.exploration_weight * info_gain)

            # Blend with Q-values if available (Bayesian combination)
            if q_values is not None:
                q_val = float(q_values[a])
                # Soft combination: 70% world model, 30% Q-table
                efe = 0.7 * efe + 0.3 * (-q_val)

            action_scores.append({
                "action": a,
                "predicted_reward": round(pred_r, 4),
                "uncertainty": round(uncertainty, 4),
                "efe": round(efe, 4),
                "info_gain": round(info_gain, 4),
            })

        # Select action with minimum EFE (best trade-off)
        action_scores.sort(key=lambda x: x["efe"])
        best = action_scores[0]
        selected = best["action"]

        # Update stats
        self._plan_count += 1
        self._action_stats[selected]["selected"] += 1
        for s in action_scores:
            self._action_stats[s["action"]]["avg_efe"] = (
                0.9 * self._action_stats[s["action"]]["avg_efe"] + 0.1 * s["efe"]
            )

        return selected, {
            "selected_action": selected,
            "efe": best["efe"],
            "predicted_reward": best["predicted_reward"],
            "uncertainty": best["uncertainty"],
            "top_3": action_scores[:3],
            "exploration_weight": self.exploration_weight,
        }

    def get_stats(self) -> dict:
        return {
            "plan_count": self._plan_count,
            "exploration_weight": self.exploration_weight,
            "action_preferences": self._action_stats,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Unified Interface
# ═══════════════════════════════════════════════════════════════════════════════

class ModelBasedAgent:
    """
    基于模型的智能体 — 世界模型 + 主动推理的统一入口。

    用法:
        agent = ModelBasedAgent()
        # 训练世界模型
        agent.train_world_model(s_emb, action, next_s_emb, reward)
        # 规划下一步动作
        action, plan = agent.decide(state_emb, q_values)
    """

    def __init__(self):
        self.wm = WorldModel()
        self.planner = ActiveInferencePlanner(self.wm)
        self.torch_available = _HAS_TORCH

    def decide(self, state_emb: np.ndarray,
               q_values: np.ndarray = None) -> Tuple[int, dict]:
        """使用主动推理选择动作。"""
        if not self.torch_available or self.wm._train_steps < 5:
            # Not enough training: fall back to argmax or random
            if q_values is not None:
                return int(np.argmax(q_values)), {"fallback": "q_table"}
            return np.random.randint(_ACTION_DIM), {"fallback": "random"}
        return self.planner.plan(state_emb, q_values)

    def get_stats(self) -> dict:
        return {
            "world_model": self.wm.get_stats(),
            "planner": self.planner.get_stats(),
            "torch_available": self.torch_available,
        }


# ── Example ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"PyTorch available: {_HAS_TORCH}")

    agent = ModelBasedAgent()
    print(f"Agent ready: {agent.torch_available}")

    if _HAS_TORCH:
        # Simulate some training
        s = np.random.randn(_EMBEDDING_DIM).astype(np.float32)
        for step in range(20):
            a = np.random.randint(_ACTION_DIM)
            ns = np.random.randn(_EMBEDDING_DIM).astype(np.float32)
            r = np.random.random() * 2 - 1
            loss = agent.wm.train_step(s, a, ns, r)
        print(f"Trained {agent.wm._train_steps} steps, "
              f"state_loss={agent.wm._state_losses[-1]:.4f}, "
              f"reward_loss={agent.wm._reward_losses[-1]:.4f}")

        # Plan
        action, plan = agent.decide(s)
        print(f"Plan: action={action}, efe={plan.get('efe', 'N/A')}")
        if 'top_3' in plan:
            for t in plan['top_3']:
                print(f"  action={t['action']}: r_pred={t['predicted_reward']}, "
                      f"uncertainty={t['uncertainty']}, efe={t['efe']}")

        stats = agent.get_stats()
        print(f"Stats: wm_steps={stats['world_model']['train_steps']}, "
              f"plans={stats['planner']['plan_count']}")

    print("\n[WorldModel] Test passed!")

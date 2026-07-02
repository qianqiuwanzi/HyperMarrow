"""
Perception Channels — 感知通道 (Screen, Voice, Conversation).

Feeds raw observations into WorkingMemory for context-aware decision making.
All external dependencies are optional — channels degrade gracefully.
"""
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from .config import get_data_dir

DATA_DIR = get_data_dir()
CONVERSATION_FILE = DATA_DIR / "conversation_history.json"


def _make_id() -> str:
    return str(uuid.uuid4())[:8]


def _now() -> str:
    return datetime.now().isoformat()


# ── Optional dependency detection ────────────────────────────────────────────
_HAS_PIL = False
_HAS_TESSERACT = False
_HAS_PYAUTOGUI = False
_HAS_PYGETWINDOW = False
_HAS_SPEECH_RECOG = False

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    pass

try:
    import pytesseract
    _HAS_TESSERACT = True
except ImportError:
    pass

try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except ImportError:
    pass

try:
    import pygetwindow
    _HAS_PYGETWINDOW = True
except ImportError:
    pass

try:
    import speech_recognition
    _HAS_SPEECH_RECOG = True
except ImportError:
    pass


# ── Observation ──────────────────────────────────────────────────────────────

@dataclass
class Observation:
    """统一感知数据记录。"""
    channel: str          # "screen" | "voice" | "conversation"
    content: str          # 提取的文本内容
    timestamp: str = ""
    metadata: dict = field(default_factory=dict)
    confidence: float = 1.0
    observation_id: str = ""

    def __post_init__(self):
        if not self.observation_id:
            self.observation_id = _make_id()
        if not self.timestamp:
            self.timestamp = _now()


# ── ScreenMonitor ────────────────────────────────────────────────────────────

class ScreenMonitor:
    """
    屏幕监控通道 — 捕获屏幕内容和活动窗口信息。

    通过截图 + OCR 提取屏幕文本，采集活动窗口标题。
    可选依赖缺失时自动降级为仅窗口标题捕获。
    """

    def __init__(self, ocr_lang: str = "chi_sim+eng",
                 capture_interval_sec: float = 5.0):
        self.ocr_lang = ocr_lang
        self.capture_interval_sec = capture_interval_sec
        self._last_capture = 0.0
        self._capture_count = 0
        self._success_count = 0
        self._ocr_available = _HAS_PIL and _HAS_TESSERACT and _HAS_PYAUTOGUI
        self._window_available = _HAS_PYGETWINDOW

    def run_once(self) -> Optional[Observation]:
        """执行一次屏幕捕获。"""
        import time
        now_ts = time.time()
        if now_ts - self._last_capture < self.capture_interval_sec:
            return None

        self._last_capture = now_ts
        self._capture_count += 1

        try:
            content_parts = []

            # Try OCR
            text = self.capture_screenshot_text()
            if text:
                content_parts.append(text)

            # Try window title
            title = self.get_active_window_title()
            if title:
                content_parts.append(f"[Window: {title}]")

            if not content_parts:
                return None

            self._success_count += 1
            return Observation(
                channel="screen",
                content=" | ".join(content_parts),
                metadata={
                    "ocr_available": self._ocr_available,
                    "window_available": self._window_available,
                },
                confidence=0.8 if self._ocr_available else 0.5,
            )
        except Exception as e:
            print(f"[ScreenMonitor] Capture failed: {e}")
            return None

    def get_active_window_title(self) -> Optional[str]:
        """获取当前活动窗口标题。"""
        if not self._window_available:
            return None
        try:
            win = pygetwindow.getActiveWindow()
            if win and win.title:
                return win.title
        except Exception as e:
            print(f"[ScreenMonitor] pygetwindow failed: {e}")
        return None

    def capture_screenshot_text(self, region: tuple = None) -> Optional[str]:
        """截图后 OCR，返回提取文本。"""
        if not self._ocr_available:
            return None
        try:
            img = pyautogui.screenshot(region=region)
            text = pytesseract.image_to_string(img, lang=self.ocr_lang)
            return text.strip() if text.strip() else None
        except Exception:
            return None

    def get_stats(self) -> dict:
        return {
            "captures": self._capture_count,
            "successes": self._success_count,
            "ocr_available": self._ocr_available,
            "window_available": self._window_available,
            "last_capture_sec": self._last_capture,
        }


# ── VoiceMonitor ─────────────────────────────────────────────────────────────

class VoiceMonitor:
    """
    语音输入通道 — 音频录制和转录。

    支持文件输入（已有音频文件）和麦克风实时录制。
    依赖 speech_recognition; 缺失时所有方法返回 None。
    """

    def __init__(self, sample_rate: int = 16000,
                 silence_timeout_sec: float = 2.0):
        self.sample_rate = sample_rate
        self.silence_timeout_sec = silence_timeout_sec
        self._stt_available = _HAS_SPEECH_RECOG
        self._transcribe_count = 0
        self._success_count = 0

    def transcribe_file(self, audio_path: str) -> Optional[Observation]:
        """转录已有音频文件。"""
        if not self._stt_available or not os.path.exists(audio_path):
            return None

        self._transcribe_count += 1
        try:
            recognizer = speech_recognition.Recognizer()
            with speech_recognition.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="zh-CN")
            if text:
                self._success_count += 1
                return Observation(
                    channel="voice",
                    content=text,
                    metadata={
                        "source": "file",
                        "audio_path": audio_path,
                        "engine": "google",
                    },
                    confidence=0.85,
                )
        except Exception as e:
            print(f"[VoiceMonitor] Transcription failed: {e}")
        return None

    def listen_once(self, timeout_sec: float = 5.0) -> Optional[Observation]:
        """录制一段音频并转录（麦克风）。"""
        if not self._stt_available:
            return None

        self._transcribe_count += 1
        try:
            recognizer = speech_recognition.Recognizer()
            with speech_recognition.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = recognizer.listen(source, timeout=timeout_sec,
                                          phrase_time_limit=timeout_sec)
            text = recognizer.recognize_google(audio, language="zh-CN")
            if text:
                self._success_count += 1
                return Observation(
                    channel="voice",
                    content=text,
                    metadata={
                        "source": "microphone",
                        "duration_sec": timeout_sec,
                        "engine": "google",
                    },
                    confidence=0.8,
                )
        except speech_recognition.WaitTimeoutError:
            pass
        except Exception as e:
            print(f"[VoiceMonitor] Listen failed: {e}")
        return None

    def get_stats(self) -> dict:
        return {
            "transcriptions": self._transcribe_count,
            "successes": self._success_count,
            "stt_available": self._stt_available,
        }


# ── ConversationTracker ──────────────────────────────────────────────────────

class ConversationTracker:
    """
    对话流追踪 — 跟踪对话轮次、说话者角色和话题变迁。

    维护当前对话的轮次历史，自动检测话题转换。
    与 WorkingMemoryDB 配合更新当前对话上下文。
    """

    def __init__(self, max_turns: int = 50,
                 topic_change_threshold: float = 0.4):
        self.max_turns = max_turns
        self.topic_change_threshold = topic_change_threshold
        self.turns = []
        self.current_topic = None
        self.topic_history = []
        self._turn_index = 0

    def add_turn(self, speaker: str, content: str,
                 role: str = "user", metadata: dict = None) -> dict:
        """
        添加一轮对话。

        Args:
            speaker: 说话者标识
            content: 说话内容（文本）
            role: "user" | "assistant" | "system"
            metadata: 附加元数据

        Returns:
            当前轮次记录
        """
        self._turn_index += 1
        turn = {
            "turn_index": self._turn_index,
            "speaker": speaker,
            "role": role,
            "content": content,
            "topic": self.current_topic,
            "timestamp": _now(),
            "metadata": metadata or {},
        }
        self.turns.append(turn)

        # Trim to max_turns
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

        # Detect topic change
        if self.detect_topic_change():
            new_topic = self._infer_topic(content)
            if new_topic and new_topic != self.current_topic:
                if self.current_topic:
                    self.topic_history.append({
                        "topic": self.current_topic,
                        "start_turn": self._turn_index - len(self.turns),
                        "end_turn": self._turn_index,
                    })
                self.current_topic = new_topic
                turn["topic"] = new_topic
                print(f"[Conversation] Topic changed: {new_topic}")

        return turn

    def get_conversation_history(self, n_last: int = None) -> list:
        """获取最近 N 轮对话历史。"""
        if n_last is None:
            return self.turns[:]
        return self.turns[-n_last:]

    def get_current_topic(self) -> Optional[str]:
        """返回当前话题。"""
        return self.current_topic

    def detect_topic_change(self) -> bool:
        """
        检测话题是否发生显著变化。
        基于最新内容的词与最近 5 轮内容的词重叠率。
        """
        if len(self.turns) < 3:
            return self.current_topic is None

        recent = self.turns[-5:]
        recent_words = set()
        for t in recent[:-1]:
            recent_words.update(self._tokenize(t["content"]))

        latest_words = set(self._tokenize(recent[-1]["content"]))
        if not latest_words:
            return False

        overlap = len(latest_words & recent_words) / len(latest_words)
        return overlap < self.topic_change_threshold

    def _infer_topic(self, content: str) -> str:
        """从内容推断话题标签（基于关键词）。"""
        keywords = {
            "video_generation": ["视频", "video", "素材", "download", "P2b"],
            "error_handling": ["error", "错误", "fix", "bug", "修复", "fail"],
            "memory_management": ["memory", "记忆", "remember", "learn"],
            "code_review": ["code", "review", "代码", "检视", "review"],
            "decision_making": ["decision", "决策", "action", "choose"],
        }
        lc = content.lower()
        best_topic = "general"
        best_score = 0
        for topic, kws in keywords.items():
            score = sum(1 for kw in kws if kw in lc)
            if score > best_score:
                best_score = score
                best_topic = topic
        return best_topic

    def _tokenize(self, text: str) -> set:
        """简单分词。"""
        import re
        return set(re.findall(r'\w+', text.lower()))

    def get_active_context_update(self) -> dict:
        """返回应注入 WorkingMemory 的上下文更新。"""
        update = {}
        if self.current_topic:
            update["conversation_topic"] = self.current_topic
        update["turn_count"] = self._turn_index
        if self.turns:
            last = self.turns[-1]
            update["last_speaker"] = last["speaker"]
            update["last_role"] = last["role"]
        return update

    def get_stats(self) -> dict:
        return {
            "total_turns": self._turn_index,
            "current_topic": self.current_topic,
            "topic_changes": len(self.topic_history),
            "speakers": list(set(t["speaker"] for t in self.turns)),
        }


# ── AttentionGate ────────────────────────────────────────────────────────────

class AttentionGate:
    """
    注意力门控 — 基于当前目标选择性过滤感知输入。

    模拟前额叶皮层的选择性注意功能：
    - 与当前目标相关的输入获得高分数
    - 低相关性输入被过滤或降权
    - 支持多目标同时关注
    """

    def __init__(self, relevance_threshold: float = 0.15):
        self.threshold = relevance_threshold
        self._current_goals: list = []    # [(goal_text, weight), ...]
        self._filtered_count = 0
        self._passed_count = 0

    def set_goals(self, goals: list):
        """
        设置当前注意力目标。

        Args:
            goals: [(goal_text, weight), ...] 或 [goal_text, ...]
        """
        self._current_goals = []
        for g in goals:
            if isinstance(g, tuple):
                self._current_goals.append(g)
            else:
                self._current_goals.append((str(g), 1.0))

    def add_goal(self, goal: str, weight: float = 1.0):
        """添加一个注意力目标。"""
        self._current_goals.append((goal, weight))

    def score(self, content: str) -> float:
        """
        计算输入内容与当前目标的相关性分数 [0, 1]。

        使用词重叠率 + 目标权重加权。
        """
        if not self._current_goals:
            return 1.0  # No goals set → pass everything

        content_words = set(content.lower().split())
        if not content_words:
            return 0.5  # Empty content → moderate score

        max_score = 0.0
        for goal_text, weight in self._current_goals:
            goal_words = set(goal_text.lower().split())
            if not goal_words:
                continue
            overlap = len(content_words & goal_words) / len(goal_words)
            score = overlap * weight
            max_score = max(max_score, score)

        return max_score

    def filter(self, observation: 'Observation') -> bool:
        """
        判断一个 Observation 是否应通过注意力门控。

        Returns:
            True = 通过, False = 过滤掉
        """
        score = self.score(observation.content)
        observation.metadata["attention_score"] = round(score, 4)

        if score < self.threshold:
            self._filtered_count += 1
            return False

        self._passed_count += 1
        observation.confidence = min(1.0, observation.confidence * (0.5 + 0.5 * score))
        return True

    def get_stats(self) -> dict:
        return {
            "goals": [(g, w) for g, w in self._current_goals],
            "threshold": self.threshold,
            "passed": self._passed_count,
            "filtered": self._filtered_count,
            "pass_rate": round(self._passed_count / max(1, self._passed_count + self._filtered_count), 3),
        }


# ── PerceptionOrchestrator ───────────────────────────────────────────────────

class PerceptionOrchestrator:
    """
    感知通道协调器 — 统一管理所有感知通道。

    提供 observe_all() 统一调度，将 Observation 推送至 WorkingMemory。
    """

    def __init__(self, working_memory=None):
        self.screen = ScreenMonitor()
        self.voice = VoiceMonitor()
        self.conversation = ConversationTracker()
        self.attention = AttentionGate()
        self.wm = working_memory
        self._observations = []

    def observe_all(self) -> list:
        """运行所有非阻塞通道一次，通过注意力门控过滤，返回 Observation 列表。"""
        new_obs = []

        screen_obs = self.screen.run_once()
        if screen_obs:
            new_obs.append(screen_obs)

        # Voice listening is blocking — skip in observe_all, use explicit call
        conv_ctx = self.conversation.get_active_context_update()
        if conv_ctx:
            # Push conversation context as an observation
            new_obs.append(Observation(
                channel="conversation",
                content=f"topic={self.conversation.current_topic or 'general'}, "
                        f"turns={conv_ctx.get('turn_count', 0)}",
                metadata=conv_ctx,
                confidence=0.9,
            ))

        # Apply attention gate filter
        filtered = [obs for obs in new_obs if self.attention.filter(obs)]
        self._observations.extend(filtered)
        return filtered

    def inject_to_working_memory(self, obs: Observation):
        """将 Observation 注入 WorkingMemory 的 recent_items。"""
        if self.wm is None:
            return
        self.wm.update_context(
            **{f"perception_{obs.channel}": obs.content[:100]}
        )

    def get_channel_stats(self) -> dict:
        return {
            "screen": self.screen.get_stats(),
            "voice": self.voice.get_stats(),
            "conversation": self.conversation.get_stats(),
            "total_observations": len(self._observations),
        }


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("  Perception Channels Test")
    print("=" * 60)

    orch = PerceptionOrchestrator()

    # Screen
    print(f"\n[Screen] OCR available: {orch.screen._ocr_available}")
    print(f"[Screen] Window available: {orch.screen._window_available}")
    obs = orch.screen.run_once()
    if obs:
        print(f"[Screen] Observation: {obs.content[:80]}...")
    else:
        print("[Screen] No observation (deps missing or rate-limited)")

    # Voice
    print(f"\n[Voice] STT available: {orch.voice._stt_available}")

    # Conversation
    orch.conversation.add_turn("user", "开始 P2b 视频素材下载任务")
    orch.conversation.add_turn("assistant", "好的，正在下载素材")
    orch.conversation.add_turn("user", "下载卡住了，报 timeout 错误")
    print(f"\n[Conversation] Topic: {orch.conversation.current_topic}")
    print(f"[Conversation] Turns: {orch.conversation._turn_index}")
    print(f"[Conversation] Topic changes: {orch.conversation.topic_history}")

    # Observe all
    new = orch.observe_all()
    print(f"\n[Orchestrator] New observations: {len(new)}")
    stats = orch.get_channel_stats()
    print(f"[Orchestrator] Stats: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    print("\n[Perception] Test passed!")

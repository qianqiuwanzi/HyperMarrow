"""
Token Counter — OpenClaw memory system

Provides tiktoken-based token counting with graceful fallback to
character-based estimation (×0.25 for Chinese, ×0.4 for English).

Usage:
    from memory_core.token_counter import count_tokens, truncate_to_tokens
"""

import re

# ── Token counter backend selection ──────────────────────────────────────────
_counter_backend = None  # "tiktoken" | "regex"

def _init_backend():
    global _counter_backend
    if _counter_backend is not None:
        return

    try:
        import tiktoken
        _counter_backend = "tiktoken"
        return
    except ImportError:
        pass

    try:
        import regex
        _counter_backend = "regex"
        return
    except ImportError:
        _counter_backend = "char"
        return


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """
    Count tokens in text using best available backend.

    Backends (in priority order):
      1. tiktoken (cl100k_base)  — most accurate for English/code
      2. character estimation      — fast fallback: Chinese ×0.25, English ×0.4

    Args:
        text: Input string
        model: tiktoken model name (ignored for char fallback)

    Returns:
        Estimated token count (int)
    """
    if not text:
        return 0

    _init_backend()

    if _counter_backend == "tiktoken":
        try:
            enc = tiktoken.get_encoding(model)
            return len(enc.encode(text))
        except Exception:
            return _char_count(text)

    return _char_count(text)


def _char_count(text: str) -> int:
    """
    Character-based token estimation.
    Chinese characters ≈ 1 token each (0.25 chars/token)
    English words ≈ 0.4 chars/token
    Mixed: weighted average
    """
    if not text:
        return 0

    # Count Chinese characters (CJK Unified Ideographs + fullwidth)
    chinese = re.findall(r'[\u4e00-\u9fff\uff00-\uffef]', text)
    n_chinese = len(chinese)

    # Count ASCII/English words
    english = re.findall(r'[a-zA-Z]+', text)
    n_english = len(english)
    n_ascii_other = len(re.findall(r'[a-zA-Z0-9.,!?;:\s]', text)) - sum(len(w) for w in english)

    # Token estimate
    tokens = n_chinese * 1.0 + n_english * 0.4 + n_ascii_other * 0.25
    return max(1, round(tokens))


def truncate_to_tokens(text: str, max_tokens: int, model: str = "cl100k_base") -> str:
    """
    Truncate text to fit within max_tokens.

    Strategy: binary search the longest prefix that fits within the budget,
    using the character-based estimator for speed.

    Args:
        text: Input text
        max_tokens: Maximum tokens allowed
        model: tiktoken model (for future use)

    Returns:
        Truncated text (may be slightly under or over due to estimator error)
    """
    if max_tokens <= 0:
        return ""
    if not text:
        return ""

    current_tokens = count_tokens(text)
    if current_tokens <= max_tokens:
        return text

    # Binary search for the right truncation point
    lo, hi = 0, len(text)
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if count_tokens(text[:mid]) <= max_tokens:
            lo = mid
        else:
            hi = mid

    return text[:lo]


# ── Convenience: count multiple blocks and return budget remaining ─────────────
def token_budget(texts: list[str], max_tokens: int) -> dict:
    """
    Count tokens across multiple text blocks and return which fit within budget.

    Args:
        texts: List of text strings
        max_tokens: Budget cap

    Returns:
        {
            "total": int,
            "items": [{"text": str, "tokens": int, "fits": bool}],
            "remaining": int,
        }
    """
    items = []
    used = 0
    for text in texts:
        t = count_tokens(text)
        fits = (used + t) <= max_tokens
        items.append({"tokens": t, "fits": fits})
        if fits:
            used += t

    return {
        "total": used,
        "max": max_tokens,
        "remaining": max_tokens - used,
        "items": items,
    }

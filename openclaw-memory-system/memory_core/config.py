"""
Configuration management for OpenClaw Memory System.

Loads from config.yaml (if present), with environment variable overrides.
Backward-compatible with hardcoded defaults when config.yaml is absent.

Environment variable overrides:
  HYPERMARROW_SERVER_PORT → server.port
  HYPERMARROW_DATA_DIR    → paths.data
  HYPERMARROW_WORKSPACE   → paths.workspace / get_workspace()
  HF_ENDPOINT             → huggingface.mirror_url (if mirror enabled)
"""

from pathlib import Path
import os
import sys

__version__ = "2.1.1"

# ── Internal cache ────────────────────────────────────────────────────────
_config = None
_config_loaded = False


def _find_config() -> Path | None:
    """Find config.yaml by walking up from this file's location."""
    candidate = Path(__file__).parent.parent.parent / "config.yaml"  # HyperMarrow/
    if candidate.exists():
        return candidate
    # Fallback: search workspace root
    ws = _detect_workspace()
    candidate = ws / "HyperMarrow" / "config.yaml"
    if candidate.exists():
        return candidate
    candidate = ws / "config.yaml"
    if candidate.exists():
        return candidate
    return None


def _load_yaml_config() -> dict:
    """Load config.yaml if available, otherwise return empty dict."""
    path = _find_config()
    if path is None:
        return {}
    try:
        # Use yaml if available, else simple parsing
        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            return _parse_yaml_simple(path)
    except Exception:
        return {}


def _parse_yaml_simple(path: Path) -> dict:
    """Minimal YAML parser for flat/simple structures (fallback)."""
    result = {}
    current_section = result
    sections = [result]
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            # Check indent level for section header
            if not stripped.startswith('-') and ':' in stripped:
                key, _, val = stripped.partition(':')
                key = key.strip().strip('"').strip("'")
                val = val.strip()

                # Section header (no value, or nested)
                if not val:
                    continue  # skip bare keys for simple parser

                # Remove trailing comment
                if '#' in val:
                    val = val[:val.index('#')].strip()

                # Parse value
                if val.lower() == 'true':
                    val = True
                elif val.lower() == 'false':
                    val = False
                elif val.lower() == 'null' or val == '~':
                    val = None
                elif val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                else:
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            pass

                current_section[key] = val
    return result


def _apply_env_overrides(config: dict) -> dict:
    """Apply HYPERMARROW_* environment variable overrides."""
    env_map = {
        "HYPERMARROW_SERVER_PORT": ("server", "port", int),
        "HYPERMARROW_DATA_DIR":    ("paths", "data", str),
        "HYPERMARROW_WORKSPACE":   ("paths", "workspace", str),
        "HYPERMARROW_API_TOKEN":   ("server", "api_token", str),
    }
    for env_var, (section, key, cast) in env_map.items():
        val = os.environ.get(env_var)
        if val is not None:
            config.setdefault(section, {})[key] = cast(val)
    return config


def get_config() -> dict:
    """Return the full configuration dict. Loads once and caches."""
    global _config, _config_loaded
    if not _config_loaded:
        _config = _load_yaml_config()
        _config = _apply_env_overrides(_config)
        _config_loaded = True
    return _config


def reload_config():
    """Force reload config from disk (useful for testing)."""
    global _config, _config_loaded
    _config = None
    _config_loaded = False
    return get_config()


# ── Path Resolution (backward compatible) ────────────────────────────────


def _detect_workspace() -> Path:
    """Auto-detect workspace root from this file's location."""
    # memory_core/config.py → memory_core/ → openclaw-memory-system/ → HyperMarrow/ → workspace/
    return Path(__file__).parent.parent.parent.parent


def get_workspace() -> Path:
    """
    Get workspace root directory.
    Priority: env var → config.yaml → auto-detect
    """
    if "OPENCLAW_WORKSPACE" in os.environ:
        return Path(os.environ["OPENCLAW_WORKSPACE"])
    cfg = get_config()
    ws = cfg.get("paths", {}).get("workspace")
    if ws:
        return Path(ws)
    return _detect_workspace()


def get_memory_dir() -> Path:
    """Get memory directory path (workspace/memory)."""
    return get_workspace() / "memory"


def get_cache_dir() -> Path:
    """Get cache directory path. Prefer APPDATA (user-writable), fallback to workspace."""
    import platform
    appdata = os.environ.get('APPDATA', '')
    if appdata:
        p = Path(appdata) / 'hypermarrow' / 'cache'
        p.mkdir(parents=True, exist_ok=True)
        return p
    return get_workspace() / ".cache"


def get_hf_cache_dir() -> Path:
    """Get HuggingFace cache directory."""
    cfg = get_config()
    hf = cfg.get("paths", {}).get("hf_cache")
    if hf:
        return Path(hf)
    return get_cache_dir() / "huggingface"


def get_data_dir() -> Path:
    """
    Get the canonical data directory.
    Priority: HYPERMARROW_DATA_DIR env → config.yaml paths.data → default
    """
    cfg = get_config()
    data = cfg.get("paths", {}).get("data")
    if data:
        data_dir = Path(data)
    else:
        data_dir = get_workspace() / "HyperMarrow" / "openclaw-memory-system" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# ── HuggingFace Setup ────────────────────────────────────────────────────


def setup_hf_mirror():
    """Setup HuggingFace mirror (config-driven)."""
    cfg = get_config()
    hf_cfg = cfg.get("huggingface", {})

    if hf_cfg.get("mirror_enabled", True):
        mirror_url = hf_cfg.get("mirror_url", "https://hf-mirror.com")
        os.environ['HF_ENDPOINT'] = mirror_url
        os.environ['HF_HUB_ENDPOINT'] = mirror_url
    else:
        # Ensure no mirror is set
        os.environ.pop('HF_ENDPOINT', None)
        os.environ.pop('HF_HUB_ENDPOINT', None)

    # Set cache paths
    hf_cache = get_hf_cache_dir()
    os.environ['HUGGINGFACE_HUB_CACHE'] = str(hf_cache / 'hub')
    os.environ['HF_HOME'] = str(hf_cache)
    hf_cache.mkdir(parents=True, exist_ok=True)

    # Offline mode: skip HF network validation if model cache exists (faster startup)
    from sys import stderr as _stderr
    if (hf_cache / 'hub').exists():
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['HF_HUB_OFFLINE'] = '1'
        print('[Config] HF offline mode enabled (model cache found)', file=_stderr)
    else:
        print('[Config] HF online mode (first run, model will be downloaded)', file=_stderr)

    enabled = "enabled" if hf_cfg.get("mirror_enabled", True) else "disabled"
    from sys import stderr
    print(f"[Config] HF mirror {enabled}: {hf_cfg.get('mirror_url', 'https://hf-mirror.com')}", file=stderr)
    print(f"[Config] HF cache: {hf_cache}", file=stderr)


# ── Convenience accessors ────────────────────────────────────────────────


def get_server_config() -> dict:
    """Return server section of config."""
    return get_config().get("server", {})


def get_agent_config() -> dict:
    """Return agents section of config."""
    return get_config().get("agents", {})


def get_learning_config() -> dict:
    """Return learning section of config."""
    return get_config().get("learning", {})


def get_features() -> dict:
    """Return features section of config."""
    return get_config().get("features", {})


def get_license_config() -> dict:
    """Return license section of config."""
    return get_config().get("license", {})


def is_feature_enabled(feature: str) -> bool:
    """Check if a specific feature is enabled."""
    return get_features().get(feature, True)

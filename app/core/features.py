"""Feature flag management module with request-time dynamic YAML reload."""

from pathlib import Path
from typing import Any
import yaml
from app.core.logging import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
FEATURES_CONFIG_PATH = PROJECT_ROOT / "config" / "features.yaml"

_cached_features: dict[str, Any] = {}
_last_mtime: float = 0.0


def load_feature_flags(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load feature flags from config/features.yaml.
    Uses mtime caching to allow dynamic updates at request-time with near-zero overhead.
    """
    global _cached_features, _last_mtime
    path = config_path or FEATURES_CONFIG_PATH

    if not path.exists():
        return {}

    try:
        current_mtime = path.stat().st_mtime
        if current_mtime != _last_mtime or config_path is not None:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if config_path is None:
                    _cached_features = data
                    _last_mtime = current_mtime
                return data
        return _cached_features
    except Exception as e:
        logger.warning(f"Error loading feature flags from {path}: {e}")
        return _cached_features


def is_feature_enabled(feature_name: str, config_path: Path | None = None) -> bool:
    """
    Check if a specific feature flag is enabled.
    Example: is_feature_enabled("llm_refinement") checks `llm_refinement.enabled`.
    """
    features = load_feature_flags(config_path)
    feature_config = features.get(feature_name, {})
    if isinstance(feature_config, dict):
        return bool(feature_config.get("enabled", False))
    return bool(feature_config)

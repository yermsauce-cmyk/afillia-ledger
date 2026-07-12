"""
Shared config + env loader for all Afillia.ledger scripts.

Loads config.yaml from the project root and merges .env values.
Safe to import from any script — no side effects.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
ENV_PATH = PROJECT_ROOT / ".env"


def _load_env_file(path: Path) -> None:
    """Minimal .env loader — avoids requiring python-dotenv."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Don't clobber real env vars
        os.environ.setdefault(key, value)


def load_config() -> Dict[str, Any]:
    """Load config.yaml + .env, return merged dict."""
    _load_env_file(ENV_PATH)

    if yaml is None:
        print(
            "ERROR: PyYAML not installed. Run: pip3 install pyyaml",
            file=sys.stderr,
        )
        sys.exit(1)

    if not CONFIG_PATH.exists():
        print(f"ERROR: config.yaml not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Resolve env-var references like "${GROQ_API_KEY}"
    _resolve_env_refs(cfg)
    return cfg


def _resolve_env_refs(node: Any) -> None:
    """Walk the config tree and replace ${VAR} strings with os.environ values."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                node[k] = os.environ.get(v[2:-1], "")
            else:
                _resolve_env_refs(v)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                node[i] = os.environ.get(v[2:-1], "")
            else:
                _resolve_env_refs(v)


def project_path(*parts: str) -> Path:
    """Resolve a path relative to the project root."""
    return PROJECT_ROOT.joinpath(*parts)


if __name__ == "__main__":
    cfg = load_config()
    print(f"Loaded config from {CONFIG_PATH}")
    print(f"LLM provider: {cfg.get('llm', {}).get('provider')}")
    print(f"Sources: {len(cfg.get('sources', {}).get('guidelines', []))} guidelines, "
          f"{len(cfg.get('sources', {}).get('reddit', []))} reddit feeds")

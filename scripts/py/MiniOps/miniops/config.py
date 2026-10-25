"""Configuration loader for MiniOps."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.yaml"


def _env_override(value: Any, env_var: str) -> Any:
    env_val = os.environ.get(env_var)
    if env_val is not None:
        if isinstance(value, bool):
            return env_val.lower() in ("true", "1", "yes")
        if isinstance(value, int):
            return int(env_val)
        if isinstance(value, float):
            return float(env_val)
        if isinstance(value, list):
            return [x.strip() for x in env_val.split(",")]
        return env_val
    return value


def load_config(path: str | Path | None = None) -> dict:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # Environment variable overrides
    if "targets" in cfg:
        for target in cfg["targets"].get("mysql", []):
            target["password"] = _env_override(
                target.get("password", ""), "MYSQL_ROOT_PASSWORD"
            )
        for target in cfg["targets"].get("redis", []):
            target["password"] = _env_override(
                target.get("password", ""), "REDIS_PASSWORD"
            )

    alerting = cfg.get("alerting", {})
    for ch in alerting.get("channels", []):
        if ch.get("type") == "webhook":
            ch["url"] = _env_override(ch.get("url", ""), "WEBHOOK_URL")
        elif ch.get("type") == "email":
            ch["smtp_host"] = _env_override(ch.get("smtp_host", ""), "SMTP_HOST")
            ch["smtp_port"] = _env_override(ch.get("smtp_port", 465), "SMTP_PORT")
            ch["username"] = _env_override(ch.get("username", ""), "SMTP_USERNAME")
            ch["password"] = _env_override(ch.get("password", ""), "SMTP_PASSWORD")

    backup = cfg.get("backup", {})
    if "mysql" in backup:
        backup["mysql"]["password"] = _env_override(
            backup["mysql"].get("password", ""), "MYSQL_ROOT_PASSWORD"
        )

    return cfg

"""YAML config loader with env: ref resolution for socialgraph."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ConfigError(Exception):
    """Raised when a config file is missing, malformed, or references a missing env var."""


class LLMConfig(BaseModel):
    enabled: bool = True
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"
    api_key: str = ""
    temperature: float = 0.0
    cache: bool = True


class ScrapeConfig(BaseModel):
    throttle_seconds: float = 5.0
    jitter: float = 2.0
    headed: bool = True


class PlatformConfig(BaseModel):
    enabled: bool = True
    profile_dir: Path
    scrape: ScrapeConfig = Field(default_factory=ScrapeConfig)


class PlatformsConfig(BaseModel):
    linkedin: PlatformConfig
    x: PlatformConfig


class StorageConfig(BaseModel):
    data_dir: Path
    gzip_raw: bool = True


class WebConfig(BaseModel):
    bind: str = "127.0.0.1"
    api_port: int = 8000
    ui_port: int = 3000


class Config(BaseModel):
    """Top-level project config loaded from config.yml."""

    llm: LLMConfig
    platforms: PlatformsConfig
    storage: StorageConfig
    web: WebConfig = Field(default_factory=WebConfig)


def resolve_env_refs(value: str, env: dict[str, str] | None = None) -> str:
    """Resolve a single env: ref to its environment value.

    Plain strings (no `env:` prefix) are returned unchanged. Missing env vars
    raise ConfigError so misconfiguration fails fast at load time.
    """
    if not isinstance(value, str) or not value.startswith("env:"):
        return value
    key = value[len("env:"):]
    source = env if env is not None else os.environ
    if key not in source or source[key] == "":
        raise ConfigError(f"env:{key} referenced but not set")
    return source[key]


def _walk_resolve(node: Any, env: dict[str, str] | None) -> Any:
    if isinstance(node, dict):
        return {k: _walk_resolve(v, env) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk_resolve(v, env) for v in node]
    if isinstance(node, str):
        return resolve_env_refs(node, env=env)
    return node


def load_config(path: Path, env: dict[str, str] | None = None) -> Config:
    """Load and validate config.yml, resolving env: refs along the way."""
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ConfigError("config root must be a mapping")
    resolved = _walk_resolve(raw, env)
    try:
        return Config.model_validate(resolved)
    except Exception as exc:
        raise ConfigError(str(exc)) from exc

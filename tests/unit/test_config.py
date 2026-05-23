from pathlib import Path

import pytest

from socialgraph.config import (
    Config,
    ConfigError,
    load_config,
    resolve_env_refs,
)


def test_resolve_env_refs_plain_value():
    assert resolve_env_refs("hello", env={}) == "hello"


def test_resolve_env_refs_substitutes_env(monkeypatch):
    monkeypatch.setenv("FOO", "bar")
    assert resolve_env_refs("env:FOO", env=None) == "bar"


def test_resolve_env_refs_missing_env_raises(monkeypatch):
    monkeypatch.delenv("MISSING", raising=False)
    with pytest.raises(ConfigError, match="MISSING"):
        resolve_env_refs("env:MISSING", env=None)


def test_load_config_minimal(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FAKE_KEY", "sk-test")
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(
        """
llm:
  enabled: true
  provider: anthropic
  model: claude-sonnet-4-6
  api_key: env:FAKE_KEY
  temperature: 0
  cache: true
platforms:
  linkedin:
    enabled: true
    profile_dir: ./data/profiles/linkedin
  x:
    enabled: true
    profile_dir: ./data/profiles/x
storage:
  data_dir: ./data
  gzip_raw: true
"""
    )
    cfg = load_config(cfg_path)
    assert isinstance(cfg, Config)
    assert cfg.llm.enabled is True
    assert cfg.llm.api_key == "sk-test"
    assert cfg.platforms.linkedin.enabled is True
    assert cfg.storage.data_dir == Path("./data")


def test_load_config_missing_env_var_fails_fast(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("NOPE", raising=False)
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(
        """
llm:
  enabled: true
  provider: anthropic
  model: x
  api_key: env:NOPE
  temperature: 0
  cache: true
platforms:
  linkedin: {enabled: false, profile_dir: ./d}
  x: {enabled: false, profile_dir: ./d}
storage:
  data_dir: ./data
  gzip_raw: true
"""
    )
    with pytest.raises(ConfigError, match="NOPE"):
        load_config(cfg_path)

"""Tests for the init wizard."""

from unittest.mock import patch

import pytest

from modelmux.init_wizard import (
    PROVIDER_INFO,
    PROVIDERS,
    _generate_toml,
    detect_clis,
)


class TestProviderInfo:
    """Verify provider metadata consistency."""

    def test_all_providers_have_info(self):
        for p in PROVIDERS:
            assert p in PROVIDER_INFO, f"{p} missing from PROVIDER_INFO"

    def test_provider_info_has_desc(self):
        for p, info in PROVIDER_INFO.items():
            assert "desc" in info
            assert "install" in info

    def test_dashscope_in_providers(self):
        assert "dashscope" in PROVIDERS

    def test_dashscope_has_env_key(self):
        assert PROVIDER_INFO["dashscope"].get("env_key") == "DASHSCOPE_CODING_API_KEY"
        assert PROVIDER_INFO["dashscope"].get("binary") is None


class TestDetectClis:
    """Test CLI/API detection."""

    def test_detects_available_binary(self):
        with patch("modelmux.init_wizard.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/codex"
            with patch.dict("os.environ", {}, clear=True):
                result = detect_clis()
            assert result["codex"] is True

    def test_detects_missing_binary(self):
        with patch("modelmux.init_wizard.shutil.which", return_value=None):
            with patch.dict("os.environ", {}, clear=True):
                result = detect_clis()
            assert result["codex"] is False
            assert result["gemini"] is False
            assert result["claude"] is False
            assert result["ollama"] is False

    def test_detects_dashscope_by_env(self):
        with patch("modelmux.init_wizard.shutil.which", return_value=None):
            with patch.dict(
                "os.environ", {"DASHSCOPE_CODING_API_KEY": "sk-test"}, clear=True
            ):
                result = detect_clis()
            assert result["dashscope"] is True

    def test_dashscope_missing_without_env(self):
        with patch("modelmux.init_wizard.shutil.which", return_value=None):
            with patch.dict("os.environ", {}, clear=True):
                result = detect_clis()
            assert result["dashscope"] is False


class TestGenerateToml:
    """Test TOML config generation."""

    def test_basic_config(self):
        toml = _generate_toml("codex", [])
        assert 'default_provider = "codex"' in toml
        assert "[routing]" in toml

    def test_with_routing_rules(self):
        rules = [{"provider": "gemini", "keywords": ["frontend", "CSS"]}]
        toml = _generate_toml("codex", rules)
        assert '[[routing.rules]]' in toml
        assert 'provider = "gemini"' in toml
        assert '"frontend"' in toml
        assert '"CSS"' in toml

    def test_with_profiles(self):
        profiles = [
            {
                "name": "budget",
                "description": "Use cheaper models",
                "providers": {
                    "codex": {"model": "gpt-4.1-mini"},
                },
            }
        ]
        toml = _generate_toml("codex", [], profiles)
        assert "[profiles.budget]" in toml
        assert 'description = "Use cheaper models"' in toml
        assert "[profiles.budget.providers.codex]" in toml
        assert 'model = "gpt-4.1-mini"' in toml

    def test_without_profiles_shows_example(self):
        toml = _generate_toml("codex", [])
        assert "# [profiles.budget]" in toml

    def test_with_profiles_no_example(self):
        profiles = [{"name": "test", "description": "", "providers": {}}]
        toml = _generate_toml("codex", [], profiles)
        assert "# [profiles.budget]" not in toml
        assert "[profiles.test]" in toml

    def test_multiple_profiles(self):
        profiles = [
            {"name": "fast", "description": "", "providers": {"codex": {"model": "gpt-4.1-mini"}}},
            {"name": "china", "description": "Chinese models", "providers": {"dashscope": {"model": "kimi-k2.5"}}},
        ]
        toml = _generate_toml("codex", [], profiles)
        assert "[profiles.fast]" in toml
        assert "[profiles.china]" in toml
        assert 'model = "kimi-k2.5"' in toml

    def test_profile_no_description(self):
        profiles = [{"name": "test", "description": "", "providers": {"codex": {"model": "m"}}}]
        toml = _generate_toml("codex", [], profiles)
        assert "[profiles.test]" in toml
        assert "description" not in toml.split("[profiles.test]")[1].split("\n")[1]

    def test_default_provider_gemini(self):
        toml = _generate_toml("gemini", [])
        assert 'default_provider = "gemini"' in toml

    def test_auto_exclude_caller(self):
        toml = _generate_toml("codex", [])
        assert "auto_exclude_caller = true" in toml

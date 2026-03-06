"""Security hardening tests."""

from __future__ import annotations

import pytest


class TestSandboxFallback:
    """Codex sandbox_map should default to read-only for unknown values."""

    def test_known_sandbox_values(self):
        from modelmux.adapters.codex import CodexAdapter

        adapter = CodexAdapter()
        for sandbox, expected in [
            ("read-only", "read-only"),
            ("write", "workspace-write"),
            ("full", "danger-full-access"),
        ]:
            cmd = adapter.build_command("test", "/tmp", sandbox=sandbox)
            idx = cmd.index("--sandbox") + 1
            assert cmd[idx] == expected

    def test_unknown_sandbox_defaults_to_readonly(self):
        from modelmux.adapters.codex import CodexAdapter

        adapter = CodexAdapter()
        cmd = adapter.build_command("test", "/tmp", sandbox="danger-full-access")
        idx = cmd.index("--sandbox") + 1
        assert cmd[idx] == "read-only"

    def test_empty_sandbox_defaults_to_readonly(self):
        from modelmux.adapters.codex import CodexAdapter

        adapter = CodexAdapter()
        cmd = adapter.build_command("test", "/tmp", sandbox="")
        idx = cmd.index("--sandbox") + 1
        assert cmd[idx] == "read-only"


class TestPushUrlValidation:
    """Push notification URL must be validated against SSRF."""

    def test_https_allowed(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("https://example.com/webhook") is True

    def test_http_allowed(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("http://example.com/webhook") is True

    def test_file_scheme_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("file:///etc/passwd") is False

    def test_ftp_scheme_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("ftp://example.com/file") is False

    def test_localhost_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("http://localhost/webhook") is False

    def test_loopback_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("http://127.0.0.1/webhook") is False

    def test_ipv6_loopback_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("http://[::1]/webhook") is False

    def test_link_local_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("http://169.254.169.254/latest/meta-data/") is False

    def test_private_10_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("http://10.0.0.1/webhook") is False

    def test_private_172_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("http://172.16.0.1/webhook") is False

    def test_private_192_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("http://192.168.1.1/webhook") is False

    def test_cloud_metadata_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("http://metadata.google.internal/v1/") is False

    def test_empty_url_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("") is False

    def test_no_host_blocked(self):
        from modelmux.a2a.http_server import _validate_push_url

        assert _validate_push_url("http://") is False

    def test_extract_push_config_rejects_ssrf(self):
        from modelmux.a2a.http_server import _extract_push_config

        params = {
            "pushNotification": {
                "url": "http://169.254.169.254/latest/meta-data/",
                "token": "secret",
            }
        }
        assert _extract_push_config(params) is None

    def test_extract_push_config_accepts_valid(self):
        from modelmux.a2a.http_server import _extract_push_config

        params = {
            "pushNotification": {
                "url": "https://hooks.slack.com/services/T0/B0/x",
                "token": "secret",
            }
        }
        config = _extract_push_config(params)
        assert config is not None
        assert config.url == "https://hooks.slack.com/services/T0/B0/x"


class TestExtraArgsSanitization:
    """extra_args values starting with '-' should be stripped."""

    def test_flag_injection_blocked(self):
        from modelmux.adapters.base import sanitize_extra_args

        result = sanitize_extra_args({"model": "--sandbox=danger-full-access"})
        assert result is None or "model" not in result

    def test_normal_values_pass(self):
        from modelmux.adapters.base import sanitize_extra_args

        result = sanitize_extra_args({"model": "gpt-4o", "profile": "default"})
        # "gpt-4o" does not start with "-" so it passes
        # but "default" also doesn't start with "-"
        # Wait - gpt-4o... does not start with "-" actually
        assert result is not None
        assert result["model"] == "gpt-4o"

    def test_none_passthrough(self):
        from modelmux.adapters.base import sanitize_extra_args

        assert sanitize_extra_args(None) is None

    def test_empty_dict(self):
        from modelmux.adapters.base import sanitize_extra_args

        assert sanitize_extra_args({}) is None or sanitize_extra_args({}) == {}

    def test_list_values_filtered(self):
        from modelmux.adapters.base import sanitize_extra_args

        result = sanitize_extra_args({"image": ["photo.png", "--exec=rm"]})
        assert result is not None
        assert result["image"] == ["photo.png"]

    def test_mixed_safe_and_unsafe(self):
        from modelmux.adapters.base import sanitize_extra_args

        result = sanitize_extra_args({
            "model": "llama3",
            "profile": "--dangerous",
            "reasoning_effort": "high",
        })
        assert result is not None
        assert "model" in result
        assert "profile" not in result
        assert "reasoning_effort" in result


class TestA2APolicyEnforcement:
    """A2A HTTP server should enforce the same policy as MCP path."""

    def test_check_provider_policy_allows_valid(self):
        from unittest.mock import patch

        from modelmux.a2a.http_server import A2AServer
        from modelmux.policy import Policy

        server = A2AServer(get_adapter=lambda x: None)
        with patch("modelmux.a2a.http_server.load_policy", return_value=Policy()):
            result = server._check_provider_policy({"reviewer": "codex", "author": "gemini"})
        assert result is None

    def test_check_provider_policy_blocks_denied(self):
        from unittest.mock import patch

        from modelmux.a2a.http_server import A2AServer
        from modelmux.policy import Policy

        server = A2AServer(get_adapter=lambda x: None)
        policy = Policy(blocked_providers=["codex"])
        with patch("modelmux.a2a.http_server.load_policy", return_value=policy):
            result = server._check_provider_policy({"reviewer": "codex"})
        assert result is not None
        assert "codex" in result

    def test_check_provider_policy_handles_spec_syntax(self):
        from unittest.mock import patch

        from modelmux.a2a.http_server import A2AServer
        from modelmux.policy import Policy

        server = A2AServer(get_adapter=lambda x: None)
        policy = Policy(blocked_providers=["dashscope"])
        with patch("modelmux.a2a.http_server.load_policy", return_value=policy):
            result = server._check_provider_policy({"reviewer": "dashscope/kimi-k2.5"})
        assert result is not None
        assert "dashscope" in result

    def test_check_provider_policy_none_map(self):
        from modelmux.a2a.http_server import A2AServer

        server = A2AServer(get_adapter=lambda x: None)
        assert server._check_provider_policy(None) is None

    def test_check_provider_policy_allowlist(self):
        from unittest.mock import patch

        from modelmux.a2a.http_server import A2AServer
        from modelmux.policy import Policy

        server = A2AServer(get_adapter=lambda x: None)
        policy = Policy(allowed_providers=["gemini"])
        with patch("modelmux.a2a.http_server.load_policy", return_value=policy):
            result = server._check_provider_policy({"reviewer": "codex"})
        assert result is not None
        assert "codex" in result


class TestGenericAdapterTemplateInjection:
    """GenericAdapter must not allow extra_args to override built-in keys."""

    def test_task_key_protected(self):
        from modelmux.adapters.generic import GenericAdapter

        adapter = GenericAdapter("test", "echo", ["{task}"])
        cmd = adapter.build_command(
            "real prompt", "/tmp",
            extra_args={"task": "INJECTED"},
        )
        assert "INJECTED" not in cmd
        assert "real prompt" in cmd

    def test_workdir_key_protected(self):
        from modelmux.adapters.generic import GenericAdapter

        adapter = GenericAdapter("test", "echo", ["{workdir}"])
        cmd = adapter.build_command(
            "prompt", "/safe/dir",
            extra_args={"workdir": "/evil/dir"},
        )
        assert "/evil/dir" not in cmd
        assert "/safe/dir" in cmd

    def test_sandbox_key_protected(self):
        from modelmux.adapters.generic import GenericAdapter

        adapter = GenericAdapter("test", "echo", ["{sandbox}"])
        cmd = adapter.build_command(
            "prompt", "/tmp", sandbox="read-only",
            extra_args={"sandbox": "danger-full-access"},
        )
        assert "danger-full-access" not in cmd
        assert "read-only" in cmd

    def test_session_id_key_protected(self):
        from modelmux.adapters.generic import GenericAdapter

        adapter = GenericAdapter("test", "echo", ["{session_id}"])
        cmd = adapter.build_command(
            "prompt", "/tmp", session_id="real-id",
            extra_args={"session_id": "hijacked-id"},
        )
        assert "hijacked-id" not in cmd
        assert "real-id" in cmd

    def test_custom_extra_args_still_work(self):
        from modelmux.adapters.generic import GenericAdapter

        adapter = GenericAdapter("test", "echo", ["{task}", "{model}"])
        cmd = adapter.build_command(
            "prompt", "/tmp",
            extra_args={"model": "llama3"},
        )
        assert "llama3" in cmd
        assert "prompt" in cmd


class TestConfigEnvBlocklist:
    """ProviderConfig.to_env_overrides must block dangerous env vars."""

    def test_path_blocked(self):
        from modelmux.config import ProviderConfig

        pc = ProviderConfig(extra_env={"PATH": "/evil/bin"})
        env = pc.to_env_overrides("codex")
        assert "PATH" not in env

    def test_ld_preload_blocked(self):
        from modelmux.config import ProviderConfig

        pc = ProviderConfig(extra_env={"LD_PRELOAD": "/evil/lib.so"})
        env = pc.to_env_overrides("gemini")
        assert "LD_PRELOAD" not in env

    def test_pythonpath_blocked(self):
        from modelmux.config import ProviderConfig

        pc = ProviderConfig(extra_env={"PYTHONPATH": "/evil/packages"})
        env = pc.to_env_overrides("claude")
        assert "PYTHONPATH" not in env

    def test_dyld_insert_blocked(self):
        from modelmux.config import ProviderConfig

        pc = ProviderConfig(extra_env={"DYLD_INSERT_LIBRARIES": "/evil/lib.dylib"})
        env = pc.to_env_overrides("dashscope")
        assert "DYLD_INSERT_LIBRARIES" not in env

    def test_home_blocked(self):
        from modelmux.config import ProviderConfig

        pc = ProviderConfig(extra_env={"HOME": "/tmp/evil"})
        env = pc.to_env_overrides("codex")
        assert "HOME" not in env

    def test_safe_env_passes(self):
        from modelmux.config import ProviderConfig

        pc = ProviderConfig(extra_env={"MY_CUSTOM_VAR": "value123"})
        env = pc.to_env_overrides("codex")
        assert env.get("MY_CUSTOM_VAR") == "value123"

    def test_case_insensitive_blocking(self):
        from modelmux.config import ProviderConfig

        pc = ProviderConfig(extra_env={"path": "/evil/bin"})
        env = pc.to_env_overrides("codex")
        assert "path" not in env

    def test_multiple_mixed(self):
        from modelmux.config import ProviderConfig

        pc = ProviderConfig(extra_env={
            "PATH": "/evil",
            "SAFE_VAR": "ok",
            "LD_LIBRARY_PATH": "/evil",
            "ANOTHER_SAFE": "fine",
        })
        env = pc.to_env_overrides("gemini")
        assert "PATH" not in env
        assert "LD_LIBRARY_PATH" not in env
        assert env.get("SAFE_VAR") == "ok"
        assert env.get("ANOTHER_SAFE") == "fine"


class TestDashScopeBaseUrlSsrf:
    """DashScope adapter must not accept base_url from extra_args."""

    @pytest.mark.asyncio
    async def test_extra_args_base_url_ignored(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        from modelmux.adapters.dashscope import DashScopeAdapter

        adapter = DashScopeAdapter()
        captured_urls = []

        async def fake_post(url, **kwargs):
            captured_urls.append(url)
            resp = MagicMock()
            resp.status_code = 200
            resp.json = MagicMock(return_value={
                "choices": [{"message": {"content": "test"}}],
                "model": "qwen3-coder-plus",
            })
            return resp

        mock_client = MagicMock()
        mock_client.post = fake_post

        with patch.object(adapter, "_get_api_key", return_value="sk-test"), \
             patch("modelmux.adapters.dashscope.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await adapter.run(
                prompt="test",
                extra_args={"base_url": "http://evil.com"},
            )

        assert len(captured_urls) == 1
        assert "evil.com" not in captured_urls[0]
        assert "coding.dashscope.aliyuncs.com" in captured_urls[0]

    @pytest.mark.asyncio
    async def test_env_override_base_url_accepted(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        from modelmux.adapters.dashscope import DashScopeAdapter

        adapter = DashScopeAdapter()
        captured_urls = []

        async def fake_post(url, **kwargs):
            captured_urls.append(url)
            resp = MagicMock()
            resp.status_code = 200
            resp.json = MagicMock(return_value={
                "choices": [{"message": {"content": "test"}}],
                "model": "qwen3-coder-plus",
            })
            return resp

        mock_client = MagicMock()
        mock_client.post = fake_post

        with patch.object(adapter, "_get_api_key", return_value="sk-test"), \
             patch("modelmux.adapters.dashscope.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await adapter.run(
                prompt="test",
                env_overrides={"DASHSCOPE_BASE_URL": "https://custom.api.com/v1"},
            )

        assert len(captured_urls) == 1
        assert "custom.api.com" in captured_urls[0]

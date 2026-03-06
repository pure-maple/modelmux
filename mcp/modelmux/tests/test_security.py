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

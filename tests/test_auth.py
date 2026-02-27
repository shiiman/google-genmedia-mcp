"""auth/ モジュールのユニットテスト."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from google_genmedia_mcp.auth.manager import AuthManager
from google_genmedia_mcp.core.errors import AuthError
from google_genmedia_mcp.core.models import GenMediaConfig


class TestAuthManager:
    """AuthManager のテスト."""

    def test_create_genai_client_api_key(self) -> None:
        """API Key 方式で genai クライアントが作成されることを検証."""
        config = GenMediaConfig()
        config.auth.method = "api_key"
        config.auth.api_key = "test-api-key"

        manager = AuthManager()
        with patch("google.genai.Client") as mock_client:
            manager.create_genai_client(config)
            mock_client.assert_called_once_with(api_key="test-api-key")

    def test_create_genai_client_no_api_key(self) -> None:
        """API Key が未設定の場合にエラーが発生することを検証."""
        config = GenMediaConfig()
        config.auth.method = "api_key"
        config.auth.api_key = ""

        manager = AuthManager()
        with pytest.raises(AuthError) as exc_info:
            manager.create_genai_client(config)
        assert exc_info.value.debug_code == "AUTH_NO_API_KEY"

    def test_create_genai_client_vertex_ai(self) -> None:
        """Vertex AI 方式で genai クライアントが作成されることを検証."""
        config = GenMediaConfig()
        config.auth.method = "vertex_ai"
        config.auth.vertex_ai.project = "my-project"
        config.auth.vertex_ai.location = "us-central1"

        manager = AuthManager()
        with patch("google.genai.Client") as mock_client:
            manager.create_genai_client(config)
            mock_client.assert_called_once_with(
                vertexai=True,
                project="my-project",
                location="us-central1",
            )

    def test_create_genai_client_no_project(self) -> None:
        """Vertex AI でプロジェクトが未設定の場合にエラーを検証."""
        config = GenMediaConfig()
        config.auth.method = "vertex_ai"
        config.auth.vertex_ai.project = ""

        manager = AuthManager()
        with pytest.raises(AuthError) as exc_info:
            manager.create_genai_client(config)
        assert exc_info.value.debug_code == "AUTH_NO_PROJECT"

    def test_create_genai_client_unknown_method(self) -> None:
        """未知の認証方式でエラーが発生することを検証."""
        config = GenMediaConfig()
        config.auth.method = "unknown"

        manager = AuthManager()
        with pytest.raises(AuthError) as exc_info:
            manager.create_genai_client(config)
        assert exc_info.value.debug_code == "AUTH_UNKNOWN_METHOD"

    def test_create_tts_client_api_key_returns_none(self) -> None:
        """API Key 方式では TTS クライアントが None を返すことを検証."""
        config = GenMediaConfig()
        config.auth.method = "api_key"

        manager = AuthManager()
        result = manager.create_tts_client(config)
        assert result is None

    def test_create_aiplatform_client_api_key_returns_none(self) -> None:
        """API Key 方式では AI Platform クライアントが None を返すことを検証."""
        config = GenMediaConfig()
        config.auth.method = "api_key"

        manager = AuthManager()
        result = manager.create_aiplatform_client(config)
        assert result is None


class TestGenMediaClient:
    """GenMediaClient のテスト."""

    def test_has_cloud_credentials_api_key(self) -> None:
        """API Key 方式では has_cloud_credentials が False を返すことを検証."""
        from google_genmedia_mcp.core.client import GenMediaClient
        config = GenMediaConfig()
        config.auth.method = "api_key"
        client = GenMediaClient(config)
        assert client.has_cloud_credentials is False

    def test_has_cloud_credentials_vertex_ai(self) -> None:
        """Vertex AI 方式では has_cloud_credentials が True を返すことを検証."""
        from google_genmedia_mcp.core.client import GenMediaClient
        config = GenMediaConfig()
        config.auth.method = "vertex_ai"
        client = GenMediaClient(config)
        assert client.has_cloud_credentials is True

    def test_has_cloud_credentials_oauth(self) -> None:
        """OAuth 方式では has_cloud_credentials が True を返すことを検証."""
        from google_genmedia_mcp.core.client import GenMediaClient
        config = GenMediaConfig()
        config.auth.method = "oauth"
        client = GenMediaClient(config)
        assert client.has_cloud_credentials is True

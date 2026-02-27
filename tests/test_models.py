"""core/models.py のユニットテスト."""

from __future__ import annotations

from google_genmedia_mcp.core.models import (
    AuthConfig,
    GeneratedImage,
    GenerationResult,
    GenMediaConfig,
    ModelCategory,
    ModelEntry,
)


class TestGenMediaConfig:
    """GenMediaConfig のテスト."""

    def test_default_values(self) -> None:
        """デフォルト値が正しく設定されることを検証."""
        config = GenMediaConfig()
        assert config.auth.method == "api_key"
        assert config.auth.api_key == ""
        assert config.output.directory == ".google-genmedia-mcp/output"
        assert config.gcs.enabled is False
        assert config.server.transport == "stdio"
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 8000
        assert config.server.log_level == "INFO"

    def test_model_defaults(self) -> None:
        """モデルのデフォルト値を検証."""
        config = GenMediaConfig()
        assert config.models.imagen.default == "imagen-4.0-fast-generate-001"
        assert config.models.gemini.default == "gemini-3.1-flash-image-preview"
        assert config.models.veo.default == "veo-3.1-generate-preview"
        assert config.models.lyria.default == "lyria-002"

    def test_chirp_defaults(self) -> None:
        """Chirp のデフォルト値を検証."""
        config = GenMediaConfig()
        assert config.chirp.default_voice == "Kore"
        assert config.chirp.default_language == "ja-JP"

    def test_veo_polling_defaults(self) -> None:
        """Veo ポーリングのデフォルト値を検証."""
        config = GenMediaConfig()
        assert config.veo.poll_interval == 15
        assert config.veo.poll_timeout == 600


class TestAuthConfig:
    """AuthConfig のテスト."""

    def test_api_key_alias(self) -> None:
        """apiKey エイリアスで api_key が設定されることを検証."""
        config = AuthConfig.model_validate({"method": "api_key", "apiKey": "test-key"})
        assert config.api_key == "test-key"

    def test_vertex_ai_alias(self) -> None:
        """vertexAi エイリアスで vertex_ai が設定されることを検証."""
        config = AuthConfig.model_validate({
            "method": "vertex_ai",
            "vertexAi": {"project": "my-project", "location": "asia-northeast1"},
        })
        assert config.vertex_ai.project == "my-project"
        assert config.vertex_ai.location == "asia-northeast1"


class TestModelCategory:
    """ModelCategory のテスト."""

    def test_aliases(self) -> None:
        """エイリアスが正しく設定されることを検証."""
        entry = ModelEntry(id="imagen-4.0-generate-001", aliases=["Imagen 4", "imagen-4.0"])
        assert "Imagen 4" in entry.aliases
        assert "imagen-4.0" in entry.aliases

    def test_allow_unregistered_alias(self) -> None:
        """allowUnregistered エイリアスが機能することを検証."""
        category = ModelCategory.model_validate({
            "default": "gemini-2.5-flash",
            "allowUnregistered": True,
        })
        assert category.allow_unregistered is True


class TestGenerationResult:
    """GenerationResult のテスト."""

    def test_empty_result(self) -> None:
        """空の生成結果を検証."""
        result = GenerationResult()
        assert result.images == []
        assert result.videos == []
        assert result.audios == []
        assert result.text is None
        assert result.model == ""

    def test_image_result(self) -> None:
        """画像生成結果を検証."""
        image = GeneratedImage(
            file_path="/tmp/test.png",
            mime_type="image/png",
            model="imagen-4.0-generate-001",
        )
        result = GenerationResult(images=[image], model="imagen-4.0-generate-001")
        assert len(result.images) == 1
        assert result.images[0].file_path == "/tmp/test.png"

    def test_model_dump(self) -> None:
        """model_dump() が正しく動作することを検証."""
        result = GenerationResult(model="test-model")
        dumped = result.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["model"] == "test-model"

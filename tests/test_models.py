"""core/models.py のユニットテスト."""

from __future__ import annotations

import pytest

from google_genmedia_mcp.core.errors import ModelNotFoundError
from google_genmedia_mcp.core.models import (
    AuthConfig,
    GeneratedImage,
    GenerationResult,
    GenMediaConfig,
    ModelEntry,
    ToolsConfig,
)


class TestGenMediaConfig:
    """GenMediaConfig のテスト."""

    def test_default_values(self) -> None:
        """デフォルト値が正しく設定されることを検証."""
        config = GenMediaConfig()
        assert config.auth.method == "vertex_ai"
        assert config.auth.api_key == ""
        assert config.output.directory == ".google-genmedia-mcp/output"
        assert config.gcs.enabled is False
        assert config.server.transport == "stdio"
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 8000
        assert config.server.log_level == "INFO"
        assert config.prompt.prefix == ""
        assert config.prompt.separator == "\n"

    def test_model_defaults(self) -> None:
        """defaultModel のデフォルト値を検証."""
        config = GenMediaConfig()
        assert config.tools.generate_image.default_model == "Nano Banana 2"
        assert config.tools.edit_image.default_model == "Imagen 4"
        assert config.tools.generate_video.default_model == "Veo 3.1"
        assert config.tools.generate_video_from_image.default_model == "Veo 3.1"
        assert config.tools.generate_music.default_model == "Lyria 2"

    def test_model_list_defaults(self) -> None:
        """models リストがデフォルトで設定されることを検証."""
        config = GenMediaConfig()
        assert len(config.tools.generate_image.models) == 6  # Imagen 3 + Gemini 3
        assert len(config.tools.edit_image.models) == 3  # Imagen のみ
        assert len(config.tools.generate_video.models) == 5
        assert len(config.tools.generate_video_from_image.models) == 5
        assert len(config.tools.generate_music.models) == 1
        # generateImage は allowUnregistered=True がデフォルト
        assert config.tools.generate_image.allow_unregistered is True

    def test_chirp_defaults(self) -> None:
        """Chirp のデフォルト値を検証."""
        config = GenMediaConfig()
        assert config.tools.generate_speech.default_voice == "Kore"
        assert config.tools.generate_speech.default_language == "ja-JP"
        assert len(config.tools.generate_speech.voices) == 8

    def test_veo_polling_defaults(self) -> None:
        """Veo ポーリングのデフォルト値を検証."""
        config = GenMediaConfig()
        assert config.tools.generate_video.polling.poll_interval == 15
        assert config.tools.generate_video.polling.poll_timeout == 600
        assert config.tools.generate_video_from_image.polling.poll_interval == 15
        assert config.tools.generate_video_from_image.polling.poll_timeout == 600


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


class TestModelEntry:
    """ModelEntry のテスト."""

    def test_aliases(self) -> None:
        """エイリアスが正しく設定されることを検証."""
        entry = ModelEntry(id="imagen-4.0-generate-001", aliases=["Imagen 4", "imagen-4.0"])
        assert "Imagen 4" in entry.aliases
        assert "imagen-4.0" in entry.aliases


class TestResolveModel:
    """ツール設定の resolve_model() のテスト."""

    def test_resolve_none_returns_default(self) -> None:
        """model=None でデフォルトモデルが解決されることを検証."""
        config = GenMediaConfig()
        resolved = config.tools.generate_image.resolve_model(None)
        assert resolved == "gemini-3.1-flash-image-preview"

    def test_resolve_by_alias(self) -> None:
        """エイリアスからモデルを解決できることを検証."""
        config = GenMediaConfig()
        assert config.tools.generate_image.resolve_model("Imagen 4 Fast") == "imagen-4.0-fast-generate-001"
        assert config.tools.generate_image.resolve_model("Nano Banana") == "gemini-2.5-flash-image"

    def test_resolve_by_id(self) -> None:
        """モデル ID で直接解決できることを検証."""
        config = GenMediaConfig()
        assert config.tools.generate_image.resolve_model("imagen-4.0-generate-001") == "imagen-4.0-generate-001"

    def test_resolve_model_not_found_raises_error(self) -> None:
        """未知のモデル名で ModelNotFoundError が発生することを検証."""
        config = GenMediaConfig()
        # generateVideo は allow_unregistered=False
        with pytest.raises(ModelNotFoundError) as exc_info:
            config.tools.generate_video.resolve_model("nonexistent-model")
        assert "nonexistent-model" in exc_info.value.user_message

    def test_resolve_allow_unregistered(self) -> None:
        """allow_unregistered=True の場合は未知モデルもそのまま返すことを検証."""
        config = GenMediaConfig()
        # generateImage は allow_unregistered=True
        result = config.tools.generate_image.resolve_model("custom-model-v1")
        assert result == "custom-model-v1"

    def test_resolve_error_hint_includes_default(self) -> None:
        """エラーの hint にデフォルトモデル名が含まれることを検証."""
        config = GenMediaConfig()
        with pytest.raises(ModelNotFoundError) as exc_info:
            config.tools.generate_video.resolve_model("bad-model")
        assert "Veo 3.1" in exc_info.value.hint

    def test_veo_resolve_none(self) -> None:
        """Veo の model=None でデフォルトが返ることを検証."""
        config = GenMediaConfig()
        assert config.tools.generate_video.resolve_model(None) == "veo-3.1-generate-preview"

    def test_lyria_resolve_by_alias(self) -> None:
        """Lyria のエイリアス解決を検証."""
        config = GenMediaConfig()
        assert config.tools.generate_music.resolve_model("Lyria 2") == "lyria-002"
        assert config.tools.generate_music.resolve_model("lyria2") == "lyria-002"

    def test_edit_image_resolve(self) -> None:
        """editImage の resolve_model を検証."""
        config = GenMediaConfig()
        # デフォルト: "Imagen 4" → "imagen-4.0-generate-001"
        assert config.tools.edit_image.resolve_model(None) == "imagen-4.0-generate-001"
        assert config.tools.edit_image.resolve_model("Imagen 4 Fast") == "imagen-4.0-fast-generate-001"

    def test_custom_models_list(self) -> None:
        """カスタム models リストで解決できることを検証."""
        from google_genmedia_mcp.core.models import GenerateImageToolConfig

        cfg = GenerateImageToolConfig(
            defaultModel="My Model",
            models=[ModelEntry(id="custom-v1", aliases=["My Model"])],
        )
        assert cfg.resolve_model(None) == "custom-v1"
        assert cfg.resolve_model("My Model") == "custom-v1"


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


class TestPromptConfig:
    """PromptConfig のテスト."""

    def test_default_values(self) -> None:
        """デフォルト値が正しく設定されることを検証."""
        config = GenMediaConfig()
        assert config.prompt.prefix == ""
        assert config.prompt.separator == "\n"

    def test_custom_prefix(self) -> None:
        """カスタム prefix を設定できることを検証."""
        config = GenMediaConfig.model_validate({
            "prompt": {"prefix": "日本語で出力。"}
        })
        assert config.prompt.prefix == "日本語で出力。"
        assert config.prompt.separator == "\n"

    def test_custom_separator(self) -> None:
        """カスタム separator を設定できることを検証."""
        config = GenMediaConfig.model_validate({
            "prompt": {"prefix": "test", "separator": " "}
        })
        assert config.prompt.prefix == "test"
        assert config.prompt.separator == " "


class TestToolsConfig:
    """ToolsConfig のテスト."""

    def test_default_values(self) -> None:
        """tools セクションのデフォルト値を検証."""
        config = GenMediaConfig()
        assert config.tools.generate_image.aspect_ratio == "16:9"
        assert config.tools.generate_image.number_of_images == 1
        assert config.tools.generate_image.output_mime_type == "image/png"
        assert config.tools.generate_image.default_model == "Nano Banana 2"
        assert config.tools.edit_image.edit_mode == "inpaint_insertion"
        assert config.tools.edit_image.number_of_images == 1
        assert config.tools.generate_video.aspect_ratio == "16:9"
        assert config.tools.generate_video.duration_seconds == 5
        assert config.tools.generate_video.number_of_videos == 1
        assert config.tools.generate_video_from_image.aspect_ratio == "16:9"
        assert config.tools.generate_video_from_image.duration_seconds == 5
        assert config.tools.generate_speech.voice is None
        assert config.tools.generate_speech.language is None
        assert config.tools.generate_speech.audio_encoding == "mp3"

    def test_models_in_each_tool(self) -> None:
        """各ツールにモデル定義が含まれることを検証."""
        config = GenMediaConfig()
        assert len(config.tools.generate_image.models) == 6
        assert len(config.tools.edit_image.models) == 3  # Imagen のみ
        assert len(config.tools.generate_video.models) == 5
        assert len(config.tools.generate_video_from_image.models) == 5
        assert len(config.tools.generate_music.models) == 1

    def test_yaml_alias_with_default_model(self) -> None:
        """camelCase エイリアスで defaultModel・パラメータを設定できることを検証."""
        tc = ToolsConfig.model_validate({
            "generateImage": {
                "defaultModel": "Imagen 4 Fast",
                "aspectRatio": "1:1",
                "numberOfImages": 4,
            },
            "generateVideo": {"durationSeconds": 8},
            "generateSpeech": {
                "voice": "Puck",
                "language": "en-US",
                "audioEncoding": "ogg_opus",
            },
            "generateMusic": {"defaultModel": "lyria-002"},
        })
        assert tc.generate_image.default_model == "Imagen 4 Fast"
        assert tc.generate_image.aspect_ratio == "1:1"
        assert tc.generate_image.number_of_images == 4
        assert tc.generate_video.duration_seconds == 8
        assert tc.generate_speech.voice == "Puck"
        assert tc.generate_speech.language == "en-US"
        assert tc.generate_speech.audio_encoding == "ogg_opus"
        assert tc.generate_music.default_model == "lyria-002"

    def test_partial_override(self) -> None:
        """一部のみ上書きした場合、他はデフォルト値が維持されることを検証."""
        tc = ToolsConfig.model_validate({
            "generateImage": {"aspectRatio": "9:16"},
        })
        assert tc.generate_image.aspect_ratio == "9:16"
        # 上書きしていないフィールドはデフォルト値
        assert tc.generate_image.default_model == "Nano Banana 2"
        assert tc.generate_image.number_of_images == 1
        assert tc.generate_image.output_mime_type == "image/png"
        # モデルリストもデフォルト値が維持される
        assert len(tc.generate_image.models) == 6
        # 上書きしていないツールもデフォルト値
        assert tc.generate_video.aspect_ratio == "16:9"

    def test_chirp_settings_in_generate_speech(self) -> None:
        """generateSpeech に Chirp 設定を camelCase で設定できることを検証."""
        tc = ToolsConfig.model_validate({
            "generateSpeech": {
                "defaultVoice": "Puck",
                "defaultLanguage": "en-US",
                "voices": [
                    {"name": "Puck", "gender": "male"},
                    {"name": "Kore", "gender": "female"},
                ],
            },
        })
        assert tc.generate_speech.default_voice == "Puck"
        assert tc.generate_speech.default_language == "en-US"
        assert len(tc.generate_speech.voices) == 2

    def test_veo_polling_in_generate_video(self) -> None:
        """generateVideo にポーリング設定を設定できることを検証."""
        tc = ToolsConfig.model_validate({
            "generateVideo": {
                "polling": {
                    "pollInterval": 30,
                    "pollTimeout": 1200,
                },
            },
        })
        assert tc.generate_video.polling.poll_interval == 30
        assert tc.generate_video.polling.poll_timeout == 1200

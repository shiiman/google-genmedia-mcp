"""サービスレイヤーのユニットテスト."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from google_genmedia_mcp.core.errors import (
    GenerationError,
    ModelNotFoundError,
    UnsupportedAuthMethodError,
)
from google_genmedia_mcp.core.models import (
    GenMediaConfig,
    get_veo_constraints,
)
from google_genmedia_mcp.services.avtool import AvToolService
from google_genmedia_mcp.services.chirp import ChirpService
from google_genmedia_mcp.services.gemini_image import GeminiImageService
from google_genmedia_mcp.services.imagen import ImagenService
from google_genmedia_mcp.services.lyria import LyriaService
from google_genmedia_mcp.services.veo import VeoService


def _make_config(
    *,
    auth_method: str = "vertex_ai",
    project: str = "test-project",
) -> GenMediaConfig:
    """テスト用設定を生成する."""
    import yaml

    raw = f"""
auth:
  method: "{auth_method}"
  vertexAi:
    project: "{project}"
    location: "us-central1"
output:
  directory: "/tmp/genmedia-test"
tools:
  generateImage:
    defaultModel: "Imagen 4 Fast"
    allowUnregistered: true
    models:
      - id: "imagen-4.0-fast-generate-001"
        aliases: ["Imagen 4 Fast", "imagen-4.0-fast"]
      - id: "imagen-4.0-generate-001"
        aliases: ["Imagen 4", "imagen-4.0"]
      - id: "gemini-2.5-flash-preview-image-generation"
        aliases: ["Nano Banana", "gemini-2.5-flash-image"]
  editImage:
    defaultModel: "Imagen 4 Fast"
    models:
      - id: "imagen-4.0-fast-generate-001"
        aliases: ["Imagen 4 Fast", "imagen-4.0-fast"]
      - id: "imagen-4.0-generate-001"
        aliases: ["Imagen 4", "imagen-4.0"]
  generateVideo:
    defaultModel: "Veo 3"
    models:
      - id: "veo-3.0-generate-preview"
        aliases: ["Veo 3", "veo-3.0"]
      - id: "veo-2.0-generate-001"
        aliases: ["Veo 2", "veo-2.0"]
    polling:
      pollInterval: 15
      pollTimeout: 600
  generateVideoFromImage:
    defaultModel: "Veo 3"
    models:
      - id: "veo-3.0-generate-preview"
        aliases: ["Veo 3", "veo-3.0"]
      - id: "veo-2.0-generate-001"
        aliases: ["Veo 2", "veo-2.0"]
    polling:
      pollInterval: 15
      pollTimeout: 600
  generateSpeech:
    defaultVoice: "Kore"
    defaultLanguage: "ja-JP"
  generateMusic:
    defaultModel: "Lyria 2"
    models:
      - id: "lyria-002"
        aliases: ["Lyria 2", "lyria2"]
"""
    return GenMediaConfig.model_validate(yaml.safe_load(raw))


def _make_storage_mock(tmp_path: Path) -> MagicMock:
    """StorageService のモックを作成する."""
    mock = MagicMock()
    mock.save_image.return_value = str(tmp_path / "test_image.png")
    mock.save_audio.return_value = str(tmp_path / "test_audio.mp3")
    mock.save_video_from_gcs.return_value = str(tmp_path / "test_video.mp4")
    mock.save_video_from_gcs_or_bytes.return_value = str(tmp_path / "test_video.mp4")
    return mock


# ===== ImagenService =====


class TestImagenServiceResolveModel:
    """ImagenService.resolve_model() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.client_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.service = ImagenService(self.client_mock, self.config, self.storage_mock)

    def test_resolve_none_returns_default(self) -> None:
        """None 指定でデフォルトモデルが返ることを検証."""
        assert self.service.resolve_model(None) == "imagen-4.0-fast-generate-001"

    def test_resolve_by_id(self) -> None:
        """モデル ID で正解 ID が返ることを検証."""
        assert self.service.resolve_model("imagen-4.0-generate-001") == "imagen-4.0-generate-001"

    def test_resolve_by_alias(self) -> None:
        """エイリアスで正解 ID が返ることを検証."""
        assert self.service.resolve_model("Imagen 4 Fast") == "imagen-4.0-fast-generate-001"
        assert self.service.resolve_model("imagen-4.0-fast") == "imagen-4.0-fast-generate-001"

    def test_resolve_unknown_allowed(self) -> None:
        """allowUnregistered=True のため未知モデルもそのまま返ることを検証."""
        result = self.service.resolve_model("unknown-model-xyz")
        assert result == "unknown-model-xyz"

    def test_resolve_unknown_raises_when_disallowed(self) -> None:
        """allowUnregistered=False の場合に ModelNotFoundError が発生することを検証."""
        config = _make_config()
        config.tools.generate_image.allow_unregistered = False
        service = ImagenService(self.client_mock, config, self.storage_mock)
        with pytest.raises(ModelNotFoundError):
            service.resolve_model("unknown-model-xyz")


class TestImagenServiceGenerate:
    """ImagenService.generate() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.client_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.storage_mock.save_image.return_value = "/tmp/test.png"
        self.service = ImagenService(self.client_mock, self.config, self.storage_mock)

    def test_generate_calls_api(self) -> None:
        """generate_images API が呼ばれることを検証."""
        # レスポンスをモック
        mock_img = MagicMock()
        mock_img.image.image_bytes = b"fake-image-bytes"
        mock_response = MagicMock()
        mock_response.generated_images = [mock_img]
        self.client_mock.genai.models.generate_images.return_value = mock_response

        result = self.service.generate(prompt="テスト画像", number_of_images=1)

        self.client_mock.genai.models.generate_images.assert_called_once()
        assert len(result.images) == 1
        assert result.images[0].file_path == "/tmp/test.png"

    def test_generate_with_negative_prompt(self) -> None:
        """ネガティブプロンプト付きで config に含まれることを検証."""
        mock_img = MagicMock()
        mock_img.image.image_bytes = b"fake-bytes"
        mock_response = MagicMock()
        mock_response.generated_images = [mock_img]
        self.client_mock.genai.models.generate_images.return_value = mock_response

        self.service.generate(prompt="テスト", negative_prompt="除外したい要素")

        call_kwargs = self.client_mock.genai.models.generate_images.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs.args[2] if len(call_kwargs.args) > 2 else call_kwargs.kwargs["config"]
        assert "negative_prompt" in config_arg

    def test_generate_api_error_raises_generation_error(self) -> None:
        """API エラー時に GenerationError が発生することを検証."""
        self.client_mock.genai.models.generate_images.side_effect = Exception("API error")

        with pytest.raises(GenerationError) as exc_info:
            self.service.generate(prompt="テスト")
        assert "IMAGEN_GENERATION_ERROR" in str(exc_info.value.debug_code)


# ===== GeminiImageService =====


class TestGeminiImageServiceResolveModel:
    """GeminiImageService.resolve_model() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.client_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.service = GeminiImageService(self.client_mock, self.config, self.storage_mock)

    def test_resolve_none_returns_default(self) -> None:
        """None で共有デフォルトモデルが返ることを検証."""
        # Imagen / Gemini 共通の generate_image 設定を使用
        assert self.service.resolve_model(None) == "imagen-4.0-fast-generate-001"

    def test_resolve_by_alias(self) -> None:
        """エイリアスで解決されることを検証."""
        assert self.service.resolve_model("Nano Banana") == "gemini-2.5-flash-preview-image-generation"

    def test_allow_unregistered_model(self) -> None:
        """allowUnregistered が True のとき未登録モデルが通ることを検証."""
        result = self.service.resolve_model("gemini-3.0-future-model")
        assert result == "gemini-3.0-future-model"

    def test_disallow_unregistered_model(self) -> None:
        """allowUnregistered が False のとき未登録モデルで ModelNotFoundError を検証."""
        config = _make_config()
        config.tools.generate_image.allow_unregistered = False
        service = GeminiImageService(self.client_mock, config, self.storage_mock)

        with pytest.raises(ModelNotFoundError):
            service.resolve_model("gemini-unknown-model")


class TestGeminiImageServiceGenerate:
    """GeminiImageService.generate() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.client_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.storage_mock.save_image.return_value = "/tmp/gemini_test.png"
        self.service = GeminiImageService(self.client_mock, self.config, self.storage_mock)

    def test_generate_image_from_text(self) -> None:
        """テキストから画像生成 API が呼ばれることを検証."""
        mock_part = MagicMock()
        mock_part.inline_data.data = b"image-data"
        mock_part.inline_data.mime_type = "image/png"
        mock_part.text = None

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        self.client_mock.genai.models.generate_content.return_value = mock_response

        result = self.service.generate(prompt="テスト画像")

        self.client_mock.genai.models.generate_content.assert_called_once()
        assert len(result.images) == 1

    def test_generate_api_error_raises(self) -> None:
        """API エラー時に GenerationError が発生することを検証."""
        self.client_mock.genai.models.generate_content.side_effect = Exception("API error")

        with pytest.raises(GenerationError) as exc_info:
            self.service.generate(prompt="テスト")
        assert "GEMINI_GENERATION_ERROR" in str(exc_info.value.debug_code)

    def test_generate_invalid_gcs_uri_raises(self) -> None:
        """無効な GCS URI で GenerationError が発生することを検証."""
        with pytest.raises(GenerationError) as exc_info:
            self.service.generate(
                prompt="テスト",
                reference_image_gcs_uri="/local/path/image.jpg",
            )
        assert "INVALID_GCS_URI" in str(exc_info.value.debug_code)

    def test_generate_text_response(self) -> None:
        """テキストレスポンスが含まれる場合も処理できることを検証."""
        mock_text_part = MagicMock()
        mock_text_part.inline_data = None
        mock_text_part.text = "生成されたテキスト"

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_text_part]
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        self.client_mock.genai.models.generate_content.return_value = mock_response

        result = self.service.generate(prompt="テスト")
        assert result.text == "生成されたテキスト"
        assert len(result.images) == 0


# ===== VeoService =====


class TestVeoServiceResolveModel:
    """VeoService.resolve_model() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.client_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.service = VeoService(self.client_mock, self.config, self.storage_mock)

    def test_resolve_none_returns_default(self) -> None:
        assert self.service.resolve_model(None) == "veo-3.0-generate-preview"

    def test_resolve_by_alias(self) -> None:
        assert self.service.resolve_model("Veo 2") == "veo-2.0-generate-001"

    def test_resolve_unknown_raises(self) -> None:
        with pytest.raises(ModelNotFoundError):
            self.service.resolve_model("veo-unknown")

    def test_resolve_model_i2v_uses_separate_config(self) -> None:
        """I2V 用 resolve_model が generateVideoFromImage 設定を使うことを検証."""
        assert self.service.resolve_model_i2v(None) == "veo-3.0-generate-preview"
        assert self.service.resolve_model_i2v("Veo 2") == "veo-2.0-generate-001"


class TestVeoServiceGenerate:
    """VeoService.generate_from_text() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.config.tools.generate_video.polling.poll_interval = 1
        self.config.tools.generate_video.polling.poll_timeout = 5
        self.client_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.storage_mock.save_video_from_gcs_or_bytes.return_value = "/tmp/video.mp4"
        self.service = VeoService(self.client_mock, self.config, self.storage_mock)

    def test_generate_from_text(self) -> None:
        """テキストから動画生成の API フローを検証."""
        mock_video = MagicMock()
        mock_video.video.uri = "gs://bucket/video.mp4"
        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response.generated_videos = [mock_video]
        self.client_mock.genai.models.generate_videos.return_value = mock_operation

        result = self.service.generate_from_text(prompt="テスト動画")

        self.client_mock.genai.models.generate_videos.assert_called_once()
        assert len(result.videos) == 1

    def test_generate_api_error_raises(self) -> None:
        """API エラー時に GenerationError が発生することを検証."""
        self.client_mock.genai.models.generate_videos.side_effect = Exception("API error")

        with pytest.raises(GenerationError):
            self.service.generate_from_text(prompt="テスト")

    def test_poll_timeout(self) -> None:
        """ポーリングタイムアウト時に GenerationError が発生することを検証."""
        mock_operation = MagicMock()
        mock_operation.done = False  # 常に未完了
        self.client_mock.genai.models.generate_videos.return_value = mock_operation
        self.client_mock.genai.operations.get.return_value = mock_operation

        with pytest.raises(GenerationError) as exc_info:
            self.service.generate_from_text(prompt="タイムアウトテスト")
        assert "VEO_TIMEOUT" in str(exc_info.value.debug_code)

    def test_generate_from_image_invalid_gcs_uri(self) -> None:
        """無効な GCS URI で GenerationError が発生することを検証."""
        with pytest.raises(GenerationError) as exc_info:
            self.service.generate_from_image(
                prompt="テスト", image_gcs_uri="/local/path/image.jpg"
            )
        assert "INVALID_GCS_URI" in str(exc_info.value.debug_code)

    def test_generate_from_image_valid_gcs_uri(self) -> None:
        """有効な GCS URI でバリデーションを通過することを検証."""
        mock_video = MagicMock()
        mock_video.video.uri = "gs://bucket/output.mp4"
        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response.generated_videos = [mock_video]
        self.client_mock.genai.models.generate_videos.return_value = mock_operation

        result = self.service.generate_from_image(
            prompt="テスト", image_gcs_uri="gs://bucket/image.jpg"
        )
        assert len(result.videos) == 1


class TestVeoServiceValidateParams:
    """VeoService._validate_params() のモデル固有制約テスト."""

    def test_unknown_model_allows_any_params(self) -> None:
        """未知モデル（constraints=None）では最低限のバリデーションのみ."""
        # constraints=None でも duration_seconds >= 1, number_of_videos >= 1 は必要
        VeoService._validate_params("unknown-model", None, "16:9", 10, 5)

    def test_unknown_model_rejects_zero_videos(self) -> None:
        """未知モデルでも number_of_videos < 1 はエラー."""
        with pytest.raises(GenerationError) as exc_info:
            VeoService._validate_params("unknown-model", None, "16:9", 8, 0)
        assert "INVALID_PARAMETER" in str(exc_info.value.debug_code)

    def test_unknown_model_rejects_zero_duration(self) -> None:
        """未知モデルでも duration_seconds < 1 はエラー."""
        with pytest.raises(GenerationError) as exc_info:
            VeoService._validate_params("unknown-model", None, "16:9", 0)
        assert "INVALID_PARAMETER" in str(exc_info.value.debug_code)

    def test_veo2_invalid_aspect_ratio(self) -> None:
        """Veo 2 で不正なアスペクト比がエラーになることを検証."""
        constraints = get_veo_constraints("veo-2.0-generate-001")
        with pytest.raises(GenerationError) as exc_info:
            VeoService._validate_params("veo-2.0-generate-001", constraints, "4:3", 8)
        assert "INVALID_PARAMETER" in str(exc_info.value.debug_code)
        assert "アスペクト比" in str(exc_info.value)

    def test_veo3_invalid_aspect_ratio(self) -> None:
        """Veo 3 では 9:16 がサポートされないことを検証."""
        constraints = get_veo_constraints("veo-3.0-generate-preview")
        with pytest.raises(GenerationError):
            VeoService._validate_params("veo-3.0-generate-preview", constraints, "9:16", 8)

    def test_veo31_allows_both_aspect_ratios(self) -> None:
        """Veo 3.1 は 16:9 と 9:16 の両方を許可することを検証."""
        constraints = get_veo_constraints("veo-3.1-generate-preview")
        VeoService._validate_params("veo-3.1-generate-preview", constraints, "16:9", 8)
        VeoService._validate_params("veo-3.1-generate-preview", constraints, "9:16", 8)

    def test_veo2_invalid_duration(self) -> None:
        """Veo 2 で不正な duration がエラーになることを検証."""
        constraints = get_veo_constraints("veo-2.0-generate-001")
        with pytest.raises(GenerationError) as exc_info:
            VeoService._validate_params("veo-2.0-generate-001", constraints, "16:9", 4)
        assert "動画長" in str(exc_info.value)

    def test_veo3_invalid_duration(self) -> None:
        """Veo 3 で不正な duration（5 秒）がエラーになることを検証."""
        constraints = get_veo_constraints("veo-3.0-generate-preview")
        with pytest.raises(GenerationError):
            VeoService._validate_params("veo-3.0-generate-preview", constraints, "16:9", 5)

    def test_veo2_exceeds_max_videos(self) -> None:
        """Veo 2 で max_videos を超えるとエラーになることを検証."""
        constraints = get_veo_constraints("veo-2.0-generate-001")
        with pytest.raises(GenerationError) as exc_info:
            VeoService._validate_params("veo-2.0-generate-001", constraints, "16:9", 8, 5)
        assert "最大" in str(exc_info.value)

    def test_veo3_exceeds_max_videos(self) -> None:
        """Veo 3 で max_videos(2) を超えるとエラーになることを検証."""
        constraints = get_veo_constraints("veo-3.0-generate-preview")
        with pytest.raises(GenerationError):
            VeoService._validate_params("veo-3.0-generate-preview", constraints, "16:9", 8, 3)

    def test_veo2_valid_params(self) -> None:
        """Veo 2 の有効なパラメータが通ることを検証."""
        constraints = get_veo_constraints("veo-2.0-generate-001")
        VeoService._validate_params("veo-2.0-generate-001", constraints, "16:9", 8, 4)
        VeoService._validate_params("veo-2.0-generate-001", constraints, "9:16", 5, 1)


class TestVeoServiceBuildConfig:
    """VeoService._build_config() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.client_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.service = VeoService(self.client_mock, self.config, self.storage_mock)

    def test_veo2_no_generate_audio(self) -> None:
        """Veo 2（supports_audio=False）では generate_audio が含まれないことを検証."""
        constraints = get_veo_constraints("veo-2.0-generate-001")
        result = self.service._build_config(
            aspect_ratio="16:9",
            duration_seconds=8,
            constraints=constraints,
            generate_audio=None,
        )
        assert "generate_audio" not in result

    def test_veo2_ignores_explicit_generate_audio_true(self) -> None:
        """Veo 2 で generate_audio=True を指定しても含まれないことを検証."""
        constraints = get_veo_constraints("veo-2.0-generate-001")
        result = self.service._build_config(
            aspect_ratio="16:9",
            duration_seconds=8,
            constraints=constraints,
            generate_audio=True,
        )
        assert "generate_audio" not in result

    def test_veo2_ignores_explicit_generate_audio_false(self) -> None:
        """Veo 2 で generate_audio=False を指定しても含まれないことを検証."""
        constraints = get_veo_constraints("veo-2.0-generate-001")
        result = self.service._build_config(
            aspect_ratio="16:9",
            duration_seconds=8,
            constraints=constraints,
            generate_audio=False,
        )
        assert "generate_audio" not in result

    def test_veo3_defaults_generate_audio_true(self) -> None:
        """Veo 3（supports_audio=True）でデフォルト generate_audio=True になることを検証."""
        constraints = get_veo_constraints("veo-3.0-generate-preview")
        result = self.service._build_config(
            aspect_ratio="16:9",
            duration_seconds=8,
            constraints=constraints,
        )
        assert result["generate_audio"] is True

    def test_veo3_explicit_generate_audio_false(self) -> None:
        """Veo 3 で generate_audio=False を明示指定できることを検証."""
        constraints = get_veo_constraints("veo-3.0-generate-preview")
        result = self.service._build_config(
            aspect_ratio="16:9",
            duration_seconds=8,
            constraints=constraints,
            generate_audio=False,
        )
        assert result["generate_audio"] is False

    def test_unknown_model_explicit_generate_audio(self) -> None:
        """未知モデル（constraints=None）で明示指定した generate_audio が含まれることを検証."""
        result = self.service._build_config(
            aspect_ratio="16:9",
            duration_seconds=8,
            constraints=None,
            generate_audio=True,
        )
        assert result["generate_audio"] is True

    def test_unknown_model_no_generate_audio(self) -> None:
        """未知モデル（constraints=None）で generate_audio=None のとき含まれないことを検証."""
        result = self.service._build_config(
            aspect_ratio="16:9",
            duration_seconds=8,
            constraints=None,
        )
        assert "generate_audio" not in result

    def test_number_of_videos_included(self) -> None:
        """number_of_videos が config に含まれることを検証."""
        result = self.service._build_config(
            aspect_ratio="16:9",
            duration_seconds=8,
            constraints=None,
            number_of_videos=3,
        )
        assert result["number_of_videos"] == 3

    def test_number_of_videos_none_excluded(self) -> None:
        """number_of_videos=None のとき config に含まれないことを検証."""
        result = self.service._build_config(
            aspect_ratio="16:9",
            duration_seconds=8,
            constraints=None,
        )
        assert "number_of_videos" not in result


class TestVeoServiceBuildOutputGcsUri:
    """VeoService._build_output_gcs_uri() のテスト."""

    def test_gcs_disabled(self) -> None:
        """GCS 無効時に None を返すことを検証."""
        config = _make_config()
        service = VeoService(MagicMock(), config, MagicMock())
        assert service._build_output_gcs_uri() is None

    def test_gcs_enabled_no_bucket(self) -> None:
        """GCS 有効でもバケット未設定なら None を返すことを検証."""
        config = _make_config()
        config.gcs.enabled = True
        config.gcs.bucket = ""
        service = VeoService(MagicMock(), config, MagicMock())
        assert service._build_output_gcs_uri() is None

    def test_gcs_enabled_with_bucket(self) -> None:
        """GCS 有効 + バケット設定済みで URI を返すことを検証."""
        config = _make_config()
        config.gcs.enabled = True
        config.gcs.bucket = "my-bucket"
        service = VeoService(MagicMock(), config, MagicMock())
        assert service._build_output_gcs_uri() == "gs://my-bucket/veo_outputs/"

    def test_gcs_uri_included_in_build_config(self) -> None:
        """GCS 有効時に _build_config の結果に output_gcs_uri が含まれることを検証."""
        config = _make_config()
        config.gcs.enabled = True
        config.gcs.bucket = "test-bucket"
        service = VeoService(MagicMock(), config, MagicMock())
        result = service._build_config(
            aspect_ratio="16:9",
            duration_seconds=8,
            constraints=None,
        )
        assert result["output_gcs_uri"] == "gs://test-bucket/veo_outputs/"


# ===== LyriaService =====


class TestLyriaServiceResolveModel:
    """LyriaService.resolve_model() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.client_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.service = LyriaService(self.client_mock, self.config, self.storage_mock)

    def test_resolve_none_returns_default(self) -> None:
        assert self.service.resolve_model(None) == "lyria-002"

    def test_resolve_by_alias(self) -> None:
        assert self.service.resolve_model("Lyria 2") == "lyria-002"
        assert self.service.resolve_model("lyria2") == "lyria-002"

    def test_resolve_unknown_raises(self) -> None:
        with pytest.raises(ModelNotFoundError):
            self.service.resolve_model("lyria-unknown")


class TestLyriaServiceGenerateMusic:
    """LyriaService.generate_music() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.client_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.storage_mock.save_audio.return_value = "/tmp/music.wav"
        self.service = LyriaService(self.client_mock, self.config, self.storage_mock)

    def test_api_key_raises_unsupported(self) -> None:
        """API Key 方式で UnsupportedAuthMethodError が発生することを検証."""
        self.client_mock.has_cloud_credentials = False

        with pytest.raises(UnsupportedAuthMethodError):
            self.service.generate_music(prompt="テスト音楽")

    def test_cloud_credentials_allowed(self) -> None:
        """クラウド認証あり・aiplatform None で AuthError が発生することを検証."""
        from google_genmedia_mcp.core.errors import AuthError

        self.client_mock.has_cloud_credentials = True
        self.client_mock.aiplatform = None

        with pytest.raises(AuthError):
            self.service.generate_music(prompt="テスト音楽")


# ===== ChirpService =====


class TestChirpServiceSynthesize:
    """ChirpService.synthesize() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.client_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.storage_mock.save_audio.return_value = "/tmp/speech.mp3"
        self.service = ChirpService(self.client_mock, self.config, self.storage_mock)

    def test_api_key_raises_unsupported(self) -> None:
        """API Key 方式で UnsupportedAuthMethodError が発生することを検証."""
        self.client_mock.has_cloud_credentials = False

        with pytest.raises(UnsupportedAuthMethodError):
            self.service.synthesize(text="こんにちは")

    def test_cloud_credentials_tts_none_raises(self) -> None:
        """クラウド認証あり・TTS クライアント None で AuthError が発生することを検証."""
        from google_genmedia_mcp.core.errors import AuthError

        self.client_mock.has_cloud_credentials = True
        self.client_mock.tts = None

        with pytest.raises(AuthError):
            self.service.synthesize(text="こんにちは")


# ===== AvToolService =====


class TestAvToolServiceCombine:
    """AvToolService.combine() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.service = AvToolService(self.config)

    def test_ffmpeg_not_found_raises(self) -> None:
        """ffmpeg が見つからない場合に GenMediaError が発生することを検証."""
        from google_genmedia_mcp.core.errors import GenMediaError

        with patch("shutil.which", return_value=None), pytest.raises(GenMediaError) as exc_info:
            self.service.combine(video_path="/tmp/v.mp4", audio_path="/tmp/a.mp3")
        assert "FFMPEG_NOT_FOUND" in str(exc_info.value.debug_code)

    def test_video_not_found_raises(self, tmp_path: Path) -> None:
        """動画ファイルが見つからない場合に GenMediaError が発生することを検証."""
        from google_genmedia_mcp.core.errors import GenMediaError

        audio_file = tmp_path / "audio.mp3"
        audio_file.write_bytes(b"fake-audio")

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), pytest.raises(GenMediaError) as exc_info:
            self.service.combine(
                video_path="/nonexistent/video.mp4",
                audio_path=str(audio_file),
            )
        assert "VIDEO_FILE_NOT_FOUND" in str(exc_info.value.debug_code)

    def test_audio_not_found_raises(self, tmp_path: Path) -> None:
        """音声ファイルが見つからない場合に GenMediaError が発生することを検証."""
        from google_genmedia_mcp.core.errors import GenMediaError

        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"fake-video")

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), pytest.raises(GenMediaError) as exc_info:
            self.service.combine(
                video_path=str(video_file),
                audio_path="/nonexistent/audio.mp3",
            )
        assert "AUDIO_FILE_NOT_FOUND" in str(exc_info.value.debug_code)

    def test_combine_success(self, tmp_path: Path) -> None:
        """正常合成時に出力パスが返ることを検証."""
        video_file = tmp_path / "video.mp4"
        audio_file = tmp_path / "audio.mp3"
        output_file = tmp_path / "combined.mp4"
        video_file.write_bytes(b"fake-video")
        audio_file.write_bytes(b"fake-audio")

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = self.service.combine(
                video_path=str(video_file),
                audio_path=str(audio_file),
                output_path=str(output_file),
            )

        assert result["output_path"] == str(output_file)
        assert result["video_path"] == str(video_file)
        assert result["audio_path"] == str(audio_file)

    def test_ffmpeg_error_raises(self, tmp_path: Path) -> None:
        """ffmpeg がエラーを返した場合に GenMediaError が発生することを検証."""
        import subprocess

        from google_genmedia_mcp.core.errors import GenMediaError

        video_file = tmp_path / "video.mp4"
        audio_file = tmp_path / "audio.mp3"
        video_file.write_bytes(b"fake-video")
        audio_file.write_bytes(b"fake-audio")

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1, cmd="ffmpeg", stderr="ffmpeg error"
            )
            with pytest.raises(GenMediaError) as exc_info:
                self.service.combine(
                    video_path=str(video_file),
                    audio_path=str(audio_file),
                )
        assert "FFMPEG_ERROR" in str(exc_info.value.debug_code)

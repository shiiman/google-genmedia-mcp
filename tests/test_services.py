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
models:
  imagen:
    default: "imagen-4.0-fast-generate-001"
    available:
      - id: "imagen-4.0-fast-generate-001"
        aliases: ["Imagen 4 Fast", "imagen-4.0-fast"]
      - id: "imagen-4.0-generate-001"
        aliases: ["Imagen 4", "imagen-4.0"]
  gemini:
    default: "gemini-2.5-flash-preview-image-generation"
    allowUnregistered: true
    available:
      - id: "gemini-2.5-flash-preview-image-generation"
        aliases: ["gemini-2.5-flash-image", "Nano Banana"]
  veo:
    default: "veo-3.0-generate-preview"
    available:
      - id: "veo-3.0-generate-preview"
        aliases: ["Veo 3", "veo-3.0"]
      - id: "veo-2.0-generate-001"
        aliases: ["Veo 2", "veo-2.0"]
  lyria:
    default: "lyria-002"
    available:
      - id: "lyria-002"
        aliases: ["Lyria 2", "lyria2"]
chirp:
  defaultVoice: "Kore"
  defaultLanguage: "ja-JP"
veo:
  pollInterval: 15
  pollTimeout: 600
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

    def test_resolve_unknown_raises(self) -> None:
        """存在しないモデル名で ModelNotFoundError が発生することを検証."""
        with pytest.raises(ModelNotFoundError):
            self.service.resolve_model("unknown-model-xyz")


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
        """None でデフォルトモデルが返ることを検証."""
        assert self.service.resolve_model(None) == "gemini-2.5-flash-preview-image-generation"

    def test_resolve_by_alias(self) -> None:
        """エイリアスで解決されることを検証."""
        assert self.service.resolve_model("Nano Banana") == "gemini-2.5-flash-preview-image-generation"

    def test_allow_unregistered_model(self) -> None:
        """allowUnregistered が True のとき未登録モデルが通ることを検証."""
        result = self.service.resolve_model("gemini-3.0-future-model")
        assert result == "gemini-3.0-future-model"

    def test_disallow_unregistered_model(self) -> None:
        """allowUnregistered が False のとき未登録モデルで ModelNotFoundError を検証."""
        # allowUnregistered を False にした設定を作成
        config = _make_config()
        config.models.gemini.allow_unregistered = False
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


class TestVeoServiceGenerate:
    """VeoService.generate_from_text() のテスト."""

    def setup_method(self) -> None:
        self.config = _make_config()
        self.config.veo.poll_interval = 1
        self.config.veo.poll_timeout = 5
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

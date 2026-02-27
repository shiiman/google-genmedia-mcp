"""MCP ツール関数のユニットテスト."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from google_genmedia_mcp.core.errors import GenMediaError
from google_genmedia_mcp.core.models import (
    GeneratedAudio,
    GeneratedImage,
    GeneratedVideo,
    GenerationResult,
    GenMediaConfig,
)


def _make_imagen_result(file_path: str = "/tmp/test.png") -> GenerationResult:
    """テスト用 Imagen 結果を生成する."""
    return GenerationResult(
        images=[
            GeneratedImage(
                file_path=file_path,
                mime_type="image/png",
                model="imagen-4.0-fast-generate-001",
            )
        ],
        model="imagen-4.0-fast-generate-001",
    )


def _make_gemini_result(file_path: str = "/tmp/gemini.png") -> GenerationResult:
    """テスト用 Gemini 結果を生成する."""
    return GenerationResult(
        images=[
            GeneratedImage(
                file_path=file_path,
                mime_type="image/png",
                model="gemini-2.5-flash-preview-image-generation",
            )
        ],
        model="gemini-2.5-flash-preview-image-generation",
    )


def _make_video_result(file_path: str = "/tmp/video.mp4") -> GenerationResult:
    """テスト用動画結果を生成する."""
    return GenerationResult(
        videos=[
            GeneratedVideo(
                file_path=file_path,
                model="veo-3.0-generate-preview",
                duration_seconds=5.0,
            )
        ],
        model="veo-3.0-generate-preview",
    )


def _make_audio_result(file_path: str = "/tmp/audio.mp3") -> GenerationResult:
    """テスト用音声結果を生成する."""
    return GenerationResult(
        audios=[
            GeneratedAudio(
                file_path=file_path,
                audio_encoding="mp3",
                model="ja-JP-Chirp3-HD-Kore",
            )
        ],
        model="ja-JP-Chirp3-HD-Kore",
    )


def _make_service_mock() -> MagicMock:
    """GenMediaService のモックを作成する."""
    mock = MagicMock()
    mock.config = GenMediaConfig()
    mock.config.models.gemini.available = []  # _is_gemini_model のエイリアス判定用
    return mock


# ===== generate_image ツール =====


class TestGenerateImageTool:
    """generate_image ツールのテスト."""

    def test_gemini_default_case(self) -> None:
        """model=None（デフォルト）で Gemini API が使われることを検証."""
        service_mock = _make_service_mock()
        service_mock.gemini_image.generate.return_value = _make_gemini_result()

        with patch(
            "google_genmedia_mcp.mcp.tools.image.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.image import generate_image

            result = generate_image(prompt="テスト画像")

        service_mock.gemini_image.generate.assert_called_once()
        assert "images" in result

    def test_imagen_explicit_model(self) -> None:
        """Imagen モデルを明示指定した場合に Imagen API が使われることを検証."""
        service_mock = _make_service_mock()
        service_mock.imagen.generate.return_value = _make_imagen_result()

        with patch(
            "google_genmedia_mcp.mcp.tools.image.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.image import generate_image

            result = generate_image(prompt="テスト画像", model="imagen-4.0-fast-generate-001")

        service_mock.imagen.generate.assert_called_once()
        assert "images" in result
        assert result["images"][0]["file_path"] == "/tmp/test.png"

    def test_gemini_model_prefix(self) -> None:
        """gemini- プレフィックスのモデルで Gemini API が使われることを検証."""
        service_mock = _make_service_mock()
        service_mock.gemini_image.generate.return_value = _make_gemini_result()

        with patch(
            "google_genmedia_mcp.mcp.tools.image.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.image import generate_image

            result = generate_image(
                prompt="テスト画像",
                model="gemini-2.5-flash-preview-image-generation",
            )

        service_mock.gemini_image.generate.assert_called_once()
        assert "images" in result

    def test_reference_image_uses_gemini(self) -> None:
        """reference_image 指定時に Gemini API が使われることを検証."""
        service_mock = _make_service_mock()
        service_mock.gemini_image.generate.return_value = _make_gemini_result()

        with patch(
            "google_genmedia_mcp.mcp.tools.image.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.image import generate_image

            result = generate_image(
                prompt="テスト画像",
                reference_image="gs://bucket/input.png",
            )

        service_mock.gemini_image.generate.assert_called_once()
        assert "images" in result

    def test_gen_media_error_returns_error_dict(self) -> None:
        """GenMediaError 時にエラー辞書が返ることを検証."""
        service_mock = _make_service_mock()
        service_mock.gemini_image.generate.side_effect = GenMediaError(
            "テストエラー", "TEST_ERROR", hint="ヒント"
        )

        with patch(
            "google_genmedia_mcp.mcp.tools.image.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.image import generate_image

            result = generate_image(prompt="エラーテスト")

        assert "error" in result
        assert result["code"] == "TEST_ERROR"
        assert result["hint"] == "ヒント"

    def test_unexpected_error_returns_internal_error(self) -> None:
        """予期しないエラー時に INTERNAL_ERROR が返ることを検証."""
        service_mock = _make_service_mock()
        service_mock.gemini_image.generate.side_effect = RuntimeError("予期しないエラー")

        with patch(
            "google_genmedia_mcp.mcp.tools.image.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.image import generate_image

            result = generate_image(prompt="エラーテスト")

        assert "error" in result
        assert result["code"] == "INTERNAL_ERROR"


# ===== generate_video ツール =====


class TestGenerateVideoTool:
    """generate_video ツールのテスト."""

    def test_normal_case(self) -> None:
        """正常系の動画生成を検証."""
        service_mock = _make_service_mock()
        service_mock.veo.generate_from_text.return_value = _make_video_result()

        with patch(
            "google_genmedia_mcp.mcp.tools.veo.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.veo import generate_video

            result = generate_video(prompt="テスト動画")

        service_mock.veo.generate_from_text.assert_called_once()
        assert "videos" in result

    def test_gen_media_error(self) -> None:
        """GenMediaError 時にエラー辞書が返ることを検証."""
        service_mock = _make_service_mock()
        service_mock.veo.generate_from_text.side_effect = GenMediaError(
            "動画エラー", "VEO_ERROR"
        )

        with patch(
            "google_genmedia_mcp.mcp.tools.veo.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.veo import generate_video

            result = generate_video(prompt="エラーテスト")

        assert "error" in result
        assert result["code"] == "VEO_ERROR"


# ===== generate_video_from_image ツール =====


class TestGenerateVideoFromImageTool:
    """generate_video_from_image ツールのテスト."""

    def test_normal_case(self) -> None:
        """正常系の動画生成（画像入力）を検証."""
        service_mock = _make_service_mock()
        service_mock.veo.generate_from_image.return_value = _make_video_result()

        with patch(
            "google_genmedia_mcp.mcp.tools.veo.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.veo import generate_video_from_image

            result = generate_video_from_image(
                prompt="テスト", image_gcs_uri="gs://bucket/image.jpg"
            )

        service_mock.veo.generate_from_image.assert_called_once()
        assert "videos" in result


# ===== generate_speech ツール =====


class TestGenerateSpeechTool:
    """generate_speech ツールのテスト."""

    def test_normal_case(self) -> None:
        """正常系の音声生成を検証."""
        service_mock = _make_service_mock()
        service_mock.chirp.synthesize.return_value = _make_audio_result()

        with patch(
            "google_genmedia_mcp.mcp.tools.chirp.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.chirp import generate_speech

            result = generate_speech(text="こんにちは")

        service_mock.chirp.synthesize.assert_called_once()
        assert "audios" in result

    def test_gen_media_error(self) -> None:
        """GenMediaError 時にエラー辞書が返ることを検証."""
        from google_genmedia_mcp.core.errors import UnsupportedAuthMethodError

        service_mock = _make_service_mock()
        service_mock.chirp.synthesize.side_effect = UnsupportedAuthMethodError(
            "API Key 方式は非対応", "AUTH_NOT_SUPPORTED", hint="Vertex AI を使用してください"
        )

        with patch(
            "google_genmedia_mcp.mcp.tools.chirp.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.chirp import generate_speech

            result = generate_speech(text="テスト")

        assert "error" in result
        assert result["code"] == "AUTH_NOT_SUPPORTED"


# ===== generate_music ツール =====


class TestGenerateMusicTool:
    """generate_music ツールのテスト."""

    def test_normal_case(self) -> None:
        """正常系の音楽生成を検証."""
        wav_result = GenerationResult(
            audios=[
                GeneratedAudio(
                    file_path="/tmp/music.wav",
                    audio_encoding="wav",
                    model="lyria-002",
                    duration_seconds=30.0,
                )
            ],
            model="lyria-002",
        )
        service_mock = _make_service_mock()
        service_mock.lyria.generate_music.return_value = wav_result

        with patch(
            "google_genmedia_mcp.mcp.tools.lyria.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.lyria import generate_music

            result = generate_music(prompt="ジャズ風ピアノ")

        service_mock.lyria.generate_music.assert_called_once()
        assert "audios" in result


# ===== combine_audio_video ツール =====


class TestCombineAudioVideoTool:
    """combine_audio_video ツールのテスト."""

    def test_normal_case(self) -> None:
        """正常系の合成を検証."""
        service_mock = _make_service_mock()
        service_mock.avtool.combine.return_value = {
            "output_path": "/tmp/combined.mp4",
            "video_path": "/tmp/video.mp4",
            "audio_path": "/tmp/audio.mp3",
        }

        with patch(
            "google_genmedia_mcp.mcp.tools.avtool.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.avtool import combine_audio_video

            result = combine_audio_video(
                video_path="/tmp/video.mp4",
                audio_path="/tmp/audio.mp3",
            )

        service_mock.avtool.combine.assert_called_once()
        assert result["output_path"] == "/tmp/combined.mp4"

    def test_gen_media_error(self) -> None:
        """GenMediaError 時にエラー辞書が返ることを検証."""
        service_mock = _make_service_mock()
        service_mock.avtool.combine.side_effect = GenMediaError(
            "ffmpeg エラー", "FFMPEG_ERROR"
        )

        with patch(
            "google_genmedia_mcp.mcp.tools.avtool.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.avtool import combine_audio_video

            result = combine_audio_video(
                video_path="/tmp/video.mp4",
                audio_path="/tmp/audio.mp3",
            )

        assert "error" in result
        assert result["code"] == "FFMPEG_ERROR"


# ===== _is_gemini_model ヘルパー =====


class TestIsGeminiModel:
    """image.py の _is_gemini_model 関数のテスト."""

    def setup_method(self) -> None:
        from google_genmedia_mcp.mcp.tools.image import _is_gemini_model

        self._is_gemini_model = _is_gemini_model
        self.config = GenMediaConfig()

    def test_none_returns_false(self) -> None:
        assert self._is_gemini_model(None, self.config) is False

    def test_gemini_prefix_returns_true(self) -> None:
        assert self._is_gemini_model("gemini-2.5-flash-image", self.config) is True

    def test_gemini_space_prefix_returns_true(self) -> None:
        assert self._is_gemini_model("gemini something", self.config) is True

    def test_imagen_model_returns_false(self) -> None:
        assert self._is_gemini_model("imagen-4.0-generate-001", self.config) is False

    def test_alias_in_config_returns_true(self) -> None:
        from google_genmedia_mcp.core.models import ModelCategory, ModelEntry

        config = GenMediaConfig()
        config.models.gemini = ModelCategory(
            default="gemini-flash",
            available=[ModelEntry(id="gemini-flash", aliases=["Nano Banana"])],
        )
        assert self._is_gemini_model("Nano Banana", config) is True


# ===== _is_imagen_model ヘルパー =====


class TestIsImagenModel:
    """image.py の _is_imagen_model 関数のテスト."""

    def setup_method(self) -> None:
        from google_genmedia_mcp.mcp.tools.image import _is_imagen_model

        self._is_imagen_model = _is_imagen_model
        self.config = GenMediaConfig()

    def test_none_returns_false(self) -> None:
        assert self._is_imagen_model(None, self.config) is False

    def test_imagen_prefix_returns_true(self) -> None:
        assert self._is_imagen_model("imagen-4.0-generate-001", self.config) is True

    def test_gemini_model_returns_false(self) -> None:
        assert self._is_imagen_model("gemini-2.5-flash-image", self.config) is False

    def test_alias_in_config_returns_true(self) -> None:
        from google_genmedia_mcp.core.models import ModelCategory, ModelEntry

        config = GenMediaConfig()
        config.models.imagen = ModelCategory(
            default="imagen-4.0-fast",
            available=[ModelEntry(id="imagen-4.0-fast", aliases=["Imagen 4 Fast"])],
        )
        assert self._is_imagen_model("Imagen 4 Fast", config) is True

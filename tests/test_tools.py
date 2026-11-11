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
                model="veo-3.1-generate-001",
                duration_seconds=5.0,
            )
        ],
        model="veo-3.1-generate-001",
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

    def test_local_reference_uses_gemini(self) -> None:
        """ローカル reference_image 指定時に Gemini に渡されることを検証."""
        service_mock = _make_service_mock()
        service_mock.gemini_image.generate.return_value = _make_gemini_result()

        with patch(
            "google_genmedia_mcp.mcp.tools.image.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.image import generate_image

            result = generate_image(prompt="編集して", reference_image="/tmp/in.png")

        call_args = service_mock.gemini_image.generate.call_args
        assert call_args.kwargs["reference_image"] == "/tmp/in.png"
        assert "images" in result

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


# ===== apply_prompt_prefix ユーティリティ =====


class TestApplyPromptPrefix:
    """apply_prompt_prefix ユーティリティのテスト."""

    def test_with_prefix(self) -> None:
        """prefix 設定時にプロンプトが変換されることを検証."""
        service_mock = _make_service_mock()
        service_mock.config = GenMediaConfig.model_validate({
            "prompt": {"prefix": "日本語で出力。"}
        })
        with patch(
            "google_genmedia_mcp.mcp.tools._utils.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools._utils import apply_prompt_prefix

            result = apply_prompt_prefix("テスト画像")

        assert result == "日本語で出力。\nテスト画像"

    def test_without_prefix(self) -> None:
        """prefix 未設定時はそのまま返すことを検証."""
        service_mock = _make_service_mock()
        with patch(
            "google_genmedia_mcp.mcp.tools._utils.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools._utils import apply_prompt_prefix

            result = apply_prompt_prefix("テスト画像")

        assert result == "テスト画像"

    def test_custom_separator(self) -> None:
        """カスタム separator が使用されることを検証."""
        service_mock = _make_service_mock()
        service_mock.config = GenMediaConfig.model_validate({
            "prompt": {"prefix": "Prefix", "separator": " | "}
        })
        with patch(
            "google_genmedia_mcp.mcp.tools._utils.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools._utils import apply_prompt_prefix

            result = apply_prompt_prefix("test prompt")

        assert result == "Prefix | test prompt"


# ===== prompt prefix の MCP ツール統合テスト =====


class TestPromptPrefixIntegration:
    """prompt prefix が各ツールに適用されることを検証する統合テスト."""

    def test_prefix_applied_to_generate_image(self) -> None:
        """generate_image に promptPrefix が適用されることを検証."""
        service_mock = _make_service_mock()
        service_mock.config = GenMediaConfig.model_validate({
            "prompt": {"prefix": "日本語で出力。"}
        })
        service_mock.gemini_image.generate.return_value = _make_gemini_result()

        with patch(
            "google_genmedia_mcp.mcp.tools._utils.get_service",
            return_value=service_mock,
        ), patch(
            "google_genmedia_mcp.mcp.tools.image.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.image import generate_image

            generate_image(prompt="テスト画像")

        call_args = service_mock.gemini_image.generate.call_args
        assert call_args.kwargs["prompt"] == "日本語で出力。\nテスト画像"

    def test_prefix_applied_to_generate_video(self) -> None:
        """generate_video に promptPrefix が適用されることを検証."""
        service_mock = _make_service_mock()
        service_mock.config = GenMediaConfig.model_validate({
            "prompt": {"prefix": "日本語で出力。"}
        })
        service_mock.veo.generate_from_text.return_value = _make_video_result()

        with patch(
            "google_genmedia_mcp.mcp.tools._utils.get_service",
            return_value=service_mock,
        ), patch(
            "google_genmedia_mcp.mcp.tools.veo.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.veo import generate_video

            generate_video(prompt="テスト動画")

        call_args = service_mock.veo.generate_from_text.call_args
        assert call_args.kwargs["prompt"] == "日本語で出力。\nテスト動画"

    def test_empty_prefix_no_change(self) -> None:
        """prefix が空の場合は prompt が変更されないことを検証."""
        service_mock = _make_service_mock()
        service_mock.gemini_image.generate.return_value = _make_gemini_result()

        with patch(
            "google_genmedia_mcp.mcp.tools._utils.get_service",
            return_value=service_mock,
        ), patch(
            "google_genmedia_mcp.mcp.tools.image.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.image import generate_image

            generate_image(prompt="テスト画像")

        call_args = service_mock.gemini_image.generate.call_args
        assert call_args.kwargs["prompt"] == "テスト画像"



# ===== generate_video_omni ツール =====


class TestGenerateVideoOmniTool:
    """generate_video_omni ツールのテスト."""

    def _call(self, service_mock: MagicMock, **kwargs: object) -> dict:  # type: ignore[type-arg]
        with patch(
            "google_genmedia_mcp.mcp.tools._utils.get_service",
            return_value=service_mock,
        ), patch(
            "google_genmedia_mcp.mcp.tools.omni.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.omni import generate_video_omni

            return generate_video_omni(**kwargs)  # type: ignore[arg-type,no-any-return]

    def test_success_passes_all_arguments(self) -> None:
        """全引数がサービスへ渡され、結果が辞書で返ることを検証."""
        service_mock = _make_service_mock()
        service_mock.omni.generate.return_value = _make_video_result()

        result = self._call(
            service_mock,
            prompt="夕焼けの海",
            task="reference_to_video",
            model="Omni",
            images=["gs://b/a.png"],
            videos=None,
            resolution="720p",
            aspect_ratio="9:16",
            duration_seconds=5,
            sample_count=2,
            temperature=0.7,
            top_p=0.9,
        )

        kwargs = service_mock.omni.generate.call_args.kwargs
        assert kwargs["prompt"] == "夕焼けの海"
        assert kwargs["task"] == "reference_to_video"
        assert kwargs["images"] == ["gs://b/a.png"]
        assert kwargs["resolution"] == "720p"
        assert kwargs["aspect_ratio"] == "9:16"
        assert kwargs["duration_seconds"] == 5
        assert kwargs["sample_count"] == 2
        assert kwargs["temperature"] == 0.7
        assert kwargs["top_p"] == 0.9
        assert result["videos"][0]["file_path"] == "/tmp/video.mp4"

    def test_prefix_applied_to_prompt(self) -> None:
        """prompt.prefix が prompt に適用されることを検証."""
        service_mock = _make_service_mock()
        service_mock.config = GenMediaConfig.model_validate({"prompt": {"prefix": "日本語で出力。"}})
        service_mock.omni.generate.return_value = _make_video_result()

        self._call(service_mock, prompt="テスト動画")

        assert service_mock.omni.generate.call_args.kwargs["prompt"] == "日本語で出力。\nテスト動画"

    def test_prefix_not_applied_without_prompt(self) -> None:
        """prompt 省略（upscale 等）では prefix を付与しないことを検証."""
        service_mock = _make_service_mock()
        service_mock.config = GenMediaConfig.model_validate({"prompt": {"prefix": "日本語で出力。"}})
        service_mock.omni.generate.return_value = _make_video_result()

        self._call(service_mock, task="upscale", videos=["gs://b/v.mp4"])

        assert service_mock.omni.generate.call_args.kwargs["prompt"] is None

    def test_genmedia_error_returns_error_dict(self) -> None:
        """GenMediaError が error 辞書に変換されることを検証."""
        service_mock = _make_service_mock()
        service_mock.omni.generate.side_effect = GenMediaError("失敗", "OMNI_API_ERROR", "確認して")

        result = self._call(service_mock, prompt="p")

        assert result == {"error": "失敗", "code": "OMNI_API_ERROR", "hint": "確認して"}

    def test_unexpected_error_hides_details(self) -> None:
        """予期しない例外は内部エラーとして詳細を隠すことを検証."""
        service_mock = _make_service_mock()
        service_mock.omni.generate.side_effect = RuntimeError("secret detail")

        result = self._call(service_mock, prompt="p")

        assert result == {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}


class TestServerInfoOmni:
    """server_info に Omni が反映されることのテスト."""

    def _info(self, *, has_cloud: bool) -> dict:  # type: ignore[type-arg]
        service_mock = _make_service_mock()
        service_mock.has_cloud_credentials = has_cloud
        with patch(
            "google_genmedia_mcp.mcp.tools.server_info.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.server_info import server_info

            return server_info()  # type: ignore[no-any-return]

    def test_omni_listed_with_models(self) -> None:
        info = self._info(has_cloud=True)
        assert "generate_video_omni" in info["available_tools"]
        assert info["unavailable_tools"] == []
        omni = info["tools_models"]["generate_video_omni"]
        assert omni["default_model"] == "Omni"
        assert omni["models"][0]["id"] == "gemini-omni-1.2-flash"

    def test_omni_unavailable_with_api_key(self) -> None:
        info = self._info(has_cloud=False)
        assert "generate_video_omni" in info["unavailable_tools"]

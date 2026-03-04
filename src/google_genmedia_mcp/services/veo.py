"""Veo 動画生成サービスモジュール.

Veo モデルを使用したテキスト/画像から動画への生成を提供する。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ..core.client import GenMediaClient
from ..core.errors import GenerationError
from ..core.models import (
    GeneratedVideo,
    GenerationResult,
    GenMediaConfig,
    VeoModelConstraints,
    VeoPollingConfig,
    get_veo_constraints,
)
from .storage import StorageService

logger = logging.getLogger(__name__)


class VeoService:
    """Veo 動画生成サービス."""

    def __init__(
        self,
        client: GenMediaClient,
        config: GenMediaConfig,
        storage: StorageService,
    ) -> None:
        self._client = client
        self._config = config
        self._storage = storage

    def resolve_model(self, model: str | None) -> str:
        """テキストから動画生成用のモデルを解決する."""
        return self._config.tools.generate_video.resolve_model(model)

    def resolve_model_i2v(self, model: str | None) -> str:
        """画像から動画生成用のモデルを解決する."""
        return self._config.tools.generate_video_from_image.resolve_model(model)

    def generate_from_text(
        self,
        prompt: str,
        model: str | None = None,
        aspect_ratio: str = "16:9",
        duration_seconds: int = 8,
        number_of_videos: int = 1,
        generate_audio: bool | None = None,
    ) -> GenerationResult:
        """テキストから動画を生成する.

        Args:
            prompt: 生成プロンプト
            model: モデル名またはエイリアス
            aspect_ratio: アスペクト比（16:9 / 9:16）
            duration_seconds: 動画の長さ（秒）
            number_of_videos: 生成本数
            generate_audio: 音声付き動画を生成するか（Veo 3+ のみ）

        Returns:
            生成結果
        """
        resolved_model = self.resolve_model(model)
        constraints = get_veo_constraints(resolved_model)
        self._validate_params(resolved_model, constraints, aspect_ratio, duration_seconds, number_of_videos)
        polling_cfg = self._config.tools.generate_video.polling
        logger.info(f"Veo でテキストから動画生成を開始します (model={resolved_model})")

        try:
            config_dict = self._build_config(
                aspect_ratio=aspect_ratio,
                duration_seconds=duration_seconds,
                number_of_videos=number_of_videos,
                generate_audio=generate_audio,
                constraints=constraints,
            )
            operation = self._client.genai.models.generate_videos(
                model=resolved_model,
                prompt=prompt,
                config=config_dict,
            )
            operation = self._poll_operation(operation, polling_cfg)
        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(
                f"Veo 動画生成に失敗しました: {e!s}",
                "VEO_GENERATION_ERROR",
            ) from e

        return self._build_result(operation, resolved_model, duration_seconds)

    def generate_from_image(
        self,
        prompt: str,
        image_gcs_uri: str,
        model: str | None = None,
        aspect_ratio: str = "16:9",
        duration_seconds: int = 8,
        generate_audio: bool | None = None,
    ) -> GenerationResult:
        """画像から動画を生成する.

        Args:
            prompt: 生成プロンプト
            image_gcs_uri: 参照画像の GCS URI
            model: モデル名またはエイリアス
            aspect_ratio: アスペクト比
            duration_seconds: 動画の長さ（秒）
            generate_audio: 音声付き動画を生成するか（Veo 3+ のみ）

        Returns:
            生成結果
        """
        from google.genai import types

        if not image_gcs_uri.startswith("gs://"):
            raise GenerationError(
                f"無効な GCS URI です: {image_gcs_uri}",
                "INVALID_GCS_URI",
                hint="gs://bucket/path/image.jpg 形式で指定してください",
            )
        resolved_model = self.resolve_model_i2v(model)
        constraints = get_veo_constraints(resolved_model)
        self._validate_params(resolved_model, constraints, aspect_ratio, duration_seconds)
        polling_cfg = self._config.tools.generate_video_from_image.polling
        logger.info(f"Veo で画像から動画生成を開始します (model={resolved_model})")

        try:
            config_dict = self._build_config(
                aspect_ratio=aspect_ratio,
                duration_seconds=duration_seconds,
                generate_audio=generate_audio,
                constraints=constraints,
            )
            # GCS URI から MIME タイプを推定
            mime_type = "image/png" if image_gcs_uri.lower().endswith(".png") else "image/jpeg"
            operation = self._client.genai.models.generate_videos(
                model=resolved_model,
                prompt=prompt,
                image=types.Image(gcs_uri=image_gcs_uri, mime_type=mime_type),
                config=config_dict,
            )
            operation = self._poll_operation(operation, polling_cfg)
        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(
                f"Veo 動画生成（画像入力）に失敗しました: {e!s}",
                "VEO_I2V_ERROR",
            ) from e

        return self._build_result(operation, resolved_model, duration_seconds, prefix="veo_i2v")

    @staticmethod
    def _validate_params(
        model_id: str,
        constraints: VeoModelConstraints | None,
        aspect_ratio: str,
        duration_seconds: int,
        number_of_videos: int = 1,
    ) -> None:
        """モデル固有の制約に基づいてパラメータを検証する."""
        # 制約の有無に関わらず最低限のバリデーション
        if number_of_videos < 1:
            raise GenerationError(
                f"number_of_videos は 1 以上で指定してください: {number_of_videos}",
                "INVALID_PARAMETER",
            )
        if duration_seconds < 1:
            raise GenerationError(
                f"duration_seconds は 1 以上で指定してください: {duration_seconds}",
                "INVALID_PARAMETER",
            )

        if constraints is None:
            return

        if aspect_ratio not in constraints.valid_aspect_ratios:
            raise GenerationError(
                f"モデル {model_id} では無効なアスペクト比です: {aspect_ratio}",
                "INVALID_PARAMETER",
                hint=f"利用可能なアスペクト比: {constraints.valid_aspect_ratios}",
            )
        if duration_seconds not in constraints.valid_durations:
            raise GenerationError(
                f"モデル {model_id} では無効な動画長です: {duration_seconds}秒",
                "INVALID_PARAMETER",
                hint=f"利用可能な動画長（秒）: {constraints.valid_durations}",
            )
        if number_of_videos > constraints.max_videos:
            raise GenerationError(
                f"モデル {model_id} では最大 {constraints.max_videos} 本まで生成可能です: {number_of_videos}",
                "INVALID_PARAMETER",
            )

    def _build_config(
        self,
        aspect_ratio: str,
        duration_seconds: int,
        constraints: VeoModelConstraints | None,
        number_of_videos: int | None = None,
        generate_audio: bool | None = None,
    ) -> dict[str, Any]:
        """Veo API 用の config dict を構築する."""
        config_dict: dict[str, Any] = {
            "aspect_ratio": aspect_ratio,
            "duration_seconds": duration_seconds,
        }
        if number_of_videos is not None:
            config_dict["number_of_videos"] = number_of_videos

        # generate_audio の解決: 音声非対応モデルには送らない
        if constraints and not constraints.supports_audio:
            if generate_audio:
                logger.warning("このモデルは音声生成をサポートしていません。generate_audio を無視します")
            # supports_audio=False のモデルには generate_audio を一切送らない
        elif generate_audio is not None:
            config_dict["generate_audio"] = generate_audio
        elif constraints and constraints.supports_audio:
            # Veo 3+ のデフォルト: True
            config_dict["generate_audio"] = True

        # GCS 出力先
        output_gcs_uri = self._build_output_gcs_uri()
        if output_gcs_uri:
            config_dict["output_gcs_uri"] = output_gcs_uri

        return config_dict

    def _build_output_gcs_uri(self) -> str | None:
        """GCS 出力先 URI を構築する."""
        gcs = self._config.gcs
        if not gcs.enabled or not gcs.bucket:
            return None
        return f"gs://{gcs.bucket}/veo_outputs/"

    def _poll_operation(self, operation: Any, polling: VeoPollingConfig | None = None) -> Any:
        """操作が完了するまでポーリングする."""
        polling = polling if polling is not None else self._config.tools.generate_video.polling
        interval = polling.poll_interval
        timeout = polling.poll_timeout
        elapsed = 0

        while not operation.done:
            if elapsed >= timeout:
                raise GenerationError(
                    f"Veo 動画生成がタイムアウトしました ({timeout} 秒)",
                    "VEO_TIMEOUT",
                    hint="config.yaml の tools.generateVideo.polling.pollTimeout を増やすか、短い動画を生成してください",
                )
            logger.debug(f"Veo 操作をポーリング中... (経過: {elapsed}秒)")
            time.sleep(interval)
            elapsed += interval
            operation = self._client.genai.operations.get(operation)

        return operation

    def _build_result(
        self,
        operation: Any,
        model: str,
        duration_seconds: int,
        prefix: str = "veo",
    ) -> GenerationResult:
        """操作結果から GenerationResult を構築する."""
        videos = []
        for video in operation.response.generated_videos:
            gcs_uri = getattr(video.video, "uri", None)
            video_bytes = getattr(video.video, "video_bytes", None)
            path = self._storage.save_video_from_gcs_or_bytes(gcs_uri, video_bytes, prefix)
            videos.append(
                GeneratedVideo(
                    file_path=path,
                    model=model,
                    duration_seconds=float(duration_seconds),
                )
            )
        logger.info(f"Veo で {len(videos)} 本の動画を生成しました")
        return GenerationResult(videos=videos, model=model)

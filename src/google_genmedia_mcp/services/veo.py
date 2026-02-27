"""Veo 動画生成サービスモジュール.

Veo モデルを使用したテキスト/画像から動画への生成を提供する。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ..core.client import GenMediaClient
from ..core.errors import GenerationError
from ..core.models import GeneratedVideo, GenerationResult, GenMediaConfig, VeoPollingConfig
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
        duration_seconds: int = 5,
        number_of_videos: int = 1,
    ) -> GenerationResult:
        """テキストから動画を生成する.

        Args:
            prompt: 生成プロンプト
            model: モデル名またはエイリアス
            aspect_ratio: アスペクト比（16:9 / 9:16）
            duration_seconds: 動画の長さ（秒）
            number_of_videos: 生成本数

        Returns:
            生成結果
        """
        self._validate_params(aspect_ratio, duration_seconds)
        resolved_model = self.resolve_model(model)
        polling_cfg = self._config.tools.generate_video.polling
        logger.info(f"Veo でテキストから動画生成を開始します (model={resolved_model})")

        try:
            operation = self._client.genai.models.generate_videos(
                model=resolved_model,
                prompt=prompt,
                config={
                    "aspect_ratio": aspect_ratio,
                    "duration_seconds": duration_seconds,
                    "number_of_videos": number_of_videos,
                },
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
        duration_seconds: int = 5,
    ) -> GenerationResult:
        """画像から動画を生成する.

        Args:
            prompt: 生成プロンプト
            image_gcs_uri: 参照画像の GCS URI
            model: モデル名またはエイリアス
            aspect_ratio: アスペクト比
            duration_seconds: 動画の長さ（秒）

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
        self._validate_params(aspect_ratio, duration_seconds)
        resolved_model = self.resolve_model_i2v(model)
        polling_cfg = self._config.tools.generate_video_from_image.polling
        logger.info(f"Veo で画像から動画生成を開始します (model={resolved_model})")

        try:
            operation = self._client.genai.models.generate_videos(
                model=resolved_model,
                prompt=prompt,
                image=types.Image(gcs_uri=image_gcs_uri),
                config={
                    "aspect_ratio": aspect_ratio,
                    "duration_seconds": duration_seconds,
                },
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
    def _validate_params(aspect_ratio: str, duration_seconds: int) -> None:
        """パラメータを検証する."""
        valid_aspect_ratios = {"16:9", "9:16"}
        if aspect_ratio not in valid_aspect_ratios:
            raise GenerationError(
                f"無効なアスペクト比です: {aspect_ratio}",
                "INVALID_PARAMETER",
                hint=f"利用可能なアスペクト比: {sorted(valid_aspect_ratios)}",
            )
        if not 5 <= duration_seconds <= 8:
            raise GenerationError(
                f"duration_seconds は 5〜8 の範囲で指定してください: {duration_seconds}",
                "INVALID_PARAMETER",
            )

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

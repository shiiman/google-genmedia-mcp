"""Gemini 画像生成サービスモジュール.

Gemini モデルを使用した画像生成・編集を提供する。
"""

from __future__ import annotations

import logging
from typing import Any

from ..core.client import GenMediaClient
from ..core.errors import GenerationError
from ..core.models import GeneratedImage, GenerationResult, GenMediaConfig
from .storage import StorageService

logger = logging.getLogger(__name__)


class GeminiImageService:
    """Gemini 画像生成サービス."""

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
        """モデル名またはエイリアスを正式モデル ID に解決する.

        allowUnregistered が True の場合は未登録モデルも許可する。
        """
        return self._config.tools.generate_image.resolve_model(model, "Gemini 画像モデル")

    def _get_genai_client(self, model_id: str) -> Any:
        """config の global フラグに基づいて genai クライアントを返す."""
        tool_cfg = self._config.tools.generate_image
        if tool_cfg.is_global_model(model_id):
            return self._client.genai_global
        return self._client.genai

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        reference_image_gcs_uri: str | None = None,
        aspect_ratio: str | None = None,
    ) -> GenerationResult:
        """Gemini を使用して画像を生成・編集する.

        Args:
            prompt: 生成プロンプト
            model: モデル名またはエイリアス
            reference_image_gcs_uri: 参照画像の GCS URI（編集時に使用）
            aspect_ratio: アスペクト比

        Returns:
            生成結果（画像とテキストを含む場合あり）
        """
        from google.genai import types

        if reference_image_gcs_uri and not reference_image_gcs_uri.startswith("gs://"):
            raise GenerationError(
                f"無効な GCS URI です: {reference_image_gcs_uri}",
                "INVALID_GCS_URI",
                hint="gs://bucket/path/image.jpg 形式で指定してください",
            )

        resolved_model = self.resolve_model(model)
        logger.info(f"Gemini で画像生成を開始します (model={resolved_model})")

        try:
            contents: list[object] = [prompt]
            if reference_image_gcs_uri:
                contents.append(
                    types.Part.from_uri(
                        file_uri=reference_image_gcs_uri, mime_type="image/jpeg"
                    )
                )

            config_params: dict[str, object] = {"response_modalities": ["IMAGE", "TEXT"]}
            if aspect_ratio:
                config_params["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)

            client = self._get_genai_client(resolved_model)
            response = client.models.generate_content(
                model=resolved_model,
                contents=contents,
                config=types.GenerateContentConfig(**config_params),  # type: ignore[arg-type]
            )
        except Exception as e:
            raise GenerationError(
                f"Gemini 画像生成に失敗しました: {e!s}",
                "GEMINI_GENERATION_ERROR",
            ) from e

        images = []
        text_parts = []

        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                if hasattr(part, "inline_data") and part.inline_data:
                    path = self._storage.save_image(
                        part.inline_data.data,
                        part.inline_data.mime_type,
                        "gemini",
                    )
                    images.append(
                        GeneratedImage(
                            file_path=path,
                            mime_type=part.inline_data.mime_type,
                            model=resolved_model,
                        )
                    )
                elif hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

        logger.info(f"Gemini で {len(images)} 枚の画像を生成しました")
        return GenerationResult(
            images=images,
            text="\n".join(text_parts) if text_parts else None,
            model=resolved_model,
        )

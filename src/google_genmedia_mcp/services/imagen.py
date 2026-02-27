"""Imagen 画像生成サービスモジュール.

Imagen モデルを使用したテキストから画像への生成を提供する。
"""

from __future__ import annotations

import logging
from typing import Any

from ..core.client import GenMediaClient
from ..core.errors import GenerationError
from ..core.models import GeneratedImage, GenerationResult, GenMediaConfig
from .storage import StorageService

logger = logging.getLogger(__name__)


class ImagenService:
    """Imagen 画像生成サービス."""

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
        """モデル名またはエイリアスを正式モデル ID に解決する."""
        return self._config.models.imagen.resolve(model, "Imagen モデル")

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        aspect_ratio: str = "1:1",
        number_of_images: int = 1,
        output_mime_type: str = "image/png",
        negative_prompt: str | None = None,
    ) -> GenerationResult:
        """テキストから画像を生成する.

        Args:
            prompt: 生成プロンプト
            model: モデル名またはエイリアス
            aspect_ratio: アスペクト比（1:1 / 16:9 / 9:16 / 4:3 / 3:4）
            number_of_images: 生成枚数（1-4）
            output_mime_type: 出力 MIME タイプ（image/png / image/jpeg）
            negative_prompt: ネガティブプロンプト

        Returns:
            生成結果
        """
        # 入力バリデーション
        if not 1 <= number_of_images <= 4:
            raise GenerationError(
                f"number_of_images は 1〜4 の範囲で指定してください: {number_of_images}",
                "INVALID_PARAMETER",
            )

        valid_aspect_ratios = {"1:1", "16:9", "9:16", "4:3", "3:4"}
        if aspect_ratio not in valid_aspect_ratios:
            raise GenerationError(
                f"無効なアスペクト比です: {aspect_ratio}",
                "INVALID_PARAMETER",
                hint=f"利用可能なアスペクト比: {sorted(valid_aspect_ratios)}",
            )

        valid_mime_types = {"image/png", "image/jpeg"}
        if output_mime_type not in valid_mime_types:
            raise GenerationError(
                f"無効な出力形式です: {output_mime_type}",
                "INVALID_PARAMETER",
                hint=f"利用可能な出力形式: {sorted(valid_mime_types)}",
            )

        resolved_model = self.resolve_model(model)
        logger.info(f"Imagen で画像生成を開始します (model={resolved_model})")

        try:
            config_dict: dict[str, Any] = {
                "number_of_images": number_of_images,
                "aspect_ratio": aspect_ratio,
                "output_mime_type": output_mime_type,
            }
            if negative_prompt:
                config_dict["negative_prompt"] = negative_prompt

            response = self._client.genai.models.generate_images(
                model=resolved_model,
                prompt=prompt,
                config=config_dict,
            )
        except Exception as e:
            raise GenerationError(
                f"Imagen 画像生成に失敗しました: {e!s}",
                "IMAGEN_GENERATION_ERROR",
            ) from e

        images = []
        for img in response.generated_images:
            image_bytes = img.image.image_bytes
            path = self._storage.save_image(image_bytes, output_mime_type, "imagen")
            images.append(
                GeneratedImage(
                    file_path=path,
                    mime_type=output_mime_type,
                    model=resolved_model,
                )
            )

        logger.info(f"Imagen で {len(images)} 枚の画像を生成しました")
        return GenerationResult(images=images, model=resolved_model)

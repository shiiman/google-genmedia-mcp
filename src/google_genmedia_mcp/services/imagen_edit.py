"""Imagen 画像編集サービスモジュール.

Imagen モデルを使用した画像編集（インペインティング、アウトペインティング等）を提供する。
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..core.client import GenMediaClient
from ..core.errors import GenerationError, GenMediaError
from ..core.models import GeneratedImage, GenerationResult, GenMediaConfig
from .storage import StorageService

logger = logging.getLogger(__name__)

# 編集モードのマッピング（API パラメータへの変換）
EDIT_MODE_MAP = {
    "inpaint_insertion": "EDIT_MODE_INPAINT_INSERTION",
    "inpaint_removal": "EDIT_MODE_INPAINT_REMOVAL",
    "outpaint": "EDIT_MODE_OUTPAINT",
    "background_replacement": "EDIT_MODE_BGSWAP",
}


class ImagenEditService:
    """Imagen 画像編集サービス."""

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
        """モデル名またはエイリアスを解決する."""
        return self._config.tools.edit_image.resolve_model(model)

    def edit(
        self,
        prompt: str,
        reference_image: str,
        edit_mode: str = "inpaint_insertion",
        mask_image: str | None = None,
        model: str | None = None,
        number_of_images: int = 1,
        negative_prompt: str | None = None,
    ) -> GenerationResult:
        """画像を編集する.

        Args:
            prompt: 編集内容の説明テキスト
            reference_image: 参照画像（GCS URI または ローカルパス）
            edit_mode: 編集モード（inpaint_insertion / inpaint_removal / outpaint / background_replacement）
            mask_image: マスク画像（inpaint 系で使用、GCS URI またはローカルパス）
            model: モデル名またはエイリアス
            number_of_images: 生成枚数
            negative_prompt: ネガティブプロンプト

        Returns:
            生成結果
        """
        from google.genai import types

        resolved_model = self.resolve_model(model)
        if edit_mode not in EDIT_MODE_MAP:
            raise GenerationError(
                f"無効な編集モードです: {edit_mode}",
                "INVALID_EDIT_MODE",
                hint=f"利用可能な編集モード: {list(EDIT_MODE_MAP.keys())}",
            )
        api_edit_mode = EDIT_MODE_MAP[edit_mode]
        logger.info(f"Imagen で画像編集を開始します (model={resolved_model}, mode={edit_mode})")

        try:
            ref_image = _load_image(reference_image)
            reference_images: list[types.RawReferenceImage | types.MaskReferenceImage] = [
                types.RawReferenceImage(
                    reference_id=0,
                    reference_image=ref_image,  # type: ignore[arg-type]
                )
            ]

            if mask_image:
                mask = _load_image(mask_image)
                reference_images.append(
                    types.MaskReferenceImage(
                        reference_id=1,
                        reference_image=mask,  # type: ignore[arg-type]
                        config=types.MaskReferenceConfig(
                            mask_mode="MASK_MODE_USER_PROVIDED"  # type: ignore[arg-type]
                        ),
                    )
                )

            edit_config = types.EditImageConfig(
                edit_mode=api_edit_mode,  # type: ignore[arg-type]
                number_of_images=number_of_images,
                negative_prompt=negative_prompt,
            )

            response = self._client.genai.models.edit_image(
                model=resolved_model,
                prompt=prompt,
                reference_images=reference_images,
                config=edit_config,
            )
        except GenMediaError:
            raise
        except Exception as e:
            raise GenerationError(
                f"Imagen 画像編集に失敗しました: {e!s}",
                "IMAGEN_EDIT_ERROR",
            ) from e

        images = []
        for img in response.generated_images:
            path = self._storage.save_image(img.image.image_bytes, "image/png", "imagen_edit")
            images.append(
                GeneratedImage(
                    file_path=path,
                    mime_type="image/png",
                    model=resolved_model,
                )
            )

        logger.info(f"Imagen で {len(images)} 枚の編集済み画像を生成しました")
        return GenerationResult(images=images, model=resolved_model)


def _validate_local_path(path_str: str) -> Path:
    """ローカルパスを検証してパストラバーサルを防ぐ.

    Raises:
        GenerationError: ファイルが存在しない、またはファイルでない場合
    """
    resolved = Path(path_str).resolve()
    if not resolved.exists():
        raise GenerationError(
            f"ファイルが見つかりません: {path_str}",
            "FILE_NOT_FOUND",
        )
    if not resolved.is_file():
        raise GenerationError(
            f"ファイルではありません: {path_str}",
            "NOT_A_FILE",
        )
    return resolved


def _load_image(path_or_uri: str) -> object:
    """パスまたは GCS URI から画像を読み込む.

    ローカルパスの場合は検証を実施する。
    """
    from google.genai.types import Image as GenAIImage

    if path_or_uri.startswith("gs://"):
        return GenAIImage(gcs_uri=path_or_uri)
    validated = _validate_local_path(path_or_uri)
    return GenAIImage.from_file(location=str(validated))

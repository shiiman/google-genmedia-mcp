"""画像生成 MCP ツールモジュール.

generate_image ツールを提供する（Imagen / Gemini を統合）。
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.errors import GenMediaError, ModelNotFoundError
from ...core.models import GenMediaConfig
from ..server import mcp
from ._utils import get_service

logger = logging.getLogger(__name__)


def _is_gemini_model(model: str | None, config: GenMediaConfig) -> bool:
    """モデルが Gemini 系かどうかを判定する.

    以下の条件のいずれかが真の場合に Gemini とみなす:
    - model が "gemini-" で始まる
    - Gemini モデルカテゴリの ID またはエイリアスと一致する
    """
    if model is None:
        return False
    # gemini- で始まる場合
    if model.lower().startswith("gemini-") or model.lower().startswith("gemini "):
        return True
    # Gemini モデルカテゴリのエントリと照合
    for entry in config.models.gemini.available:
        if entry.id == model or model in entry.aliases:
            return True
    return False


def _is_imagen_model(model: str | None, config: GenMediaConfig) -> bool:
    """モデルが Imagen 系かどうかを判定する.

    以下の条件のいずれかが真の場合に Imagen とみなす:
    - model が "imagen-" で始まる
    - Imagen モデルカテゴリの ID またはエイリアスと一致する
    """
    if model is None:
        return False
    # imagen- で始まる場合
    if model.lower().startswith("imagen-"):
        return True
    # Imagen モデルカテゴリのエントリと照合
    for entry in config.models.imagen.available:
        if entry.id == model or model in entry.aliases:
            return True
    return False


@mcp.tool()
def generate_image(
    prompt: str,
    model: str | None = None,
    aspect_ratio: str = "16:9",
    number_of_images: int = 1,
    negative_prompt: str | None = None,
    output_mime_type: str = "image/png",
    reference_image: str | None = None,
) -> dict[str, Any]:
    """テキストから画像を生成する。

    Imagen または Gemini モデルを使用して画像を生成する。

    モデル選択ロジック:
    - model が "imagen-" で始まる、または Imagen エイリアスの場合 → Imagen API を使用
    - それ以外（未指定含む）→ Gemini API を使用（デフォルト: Nano Banana 2）
    - reference_image を指定した場合 → Gemini の参照画像付き生成モードを使用

    Args:
        prompt: 生成する画像の説明テキスト
        model: 使用するモデル名またはエイリアス
                - Imagen: "imagen-4.0-fast-generate-001", "Imagen 4 Fast" 等
                - Gemini: "gemini-2.5-flash-preview-image-generation", "Nano Banana" 等
                - 省略時: Gemini デフォルトモデル (Nano Banana 2) を使用
        aspect_ratio: アスペクト比 (1:1 / 16:9 / 9:16 / 4:3 / 3:4)。デフォルト: 16:9
        number_of_images: 生成枚数（1〜4）。Gemini 使用時は無視される
        negative_prompt: 生成から除外したい要素の説明。Gemini 使用時は無視される
        output_mime_type: 出力形式 (image/png / image/jpeg)。Gemini 使用時は無視される
        reference_image: 参照画像（GCS URI: gs://bucket/file.png またはローカルパス）。
                         指定すると Gemini の参照画像付き生成モードを使用

    Returns:
        生成結果（images リストと model 名を含む辞書）
    """
    try:
        service = get_service()
        config = service.config
        use_imagen = _is_imagen_model(model, config)

        if use_imagen:
            result = service.imagen.generate(
                prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                number_of_images=number_of_images,
                output_mime_type=output_mime_type,
                negative_prompt=negative_prompt,
            )
        elif model is None or _is_gemini_model(model, config):
            # model 未指定、または Gemini 系モデルの場合
            result = service.gemini_image.generate(
                prompt=prompt,
                model=model,
                reference_image_gcs_uri=reference_image,
                aspect_ratio=aspect_ratio,
            )
        else:
            # どのカテゴリにも該当しないモデル名
            raise ModelNotFoundError(
                f"不明なモデルです: {model}",
                "MODEL_NOT_FOUND",
                hint="Imagen 系（例: 'Imagen 4 Fast'）または Gemini 系（例: 'Nano Banana 2'）のモデルを指定してください",
            )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("generate_image で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

"""画像生成 MCP ツールモジュール.

generate_image ツールを提供する（Imagen / Gemini を統合）。
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.errors import GenMediaError
from ..server import mcp
from ._utils import apply_prompt_prefix, get_service

logger = logging.getLogger(__name__)


@mcp.tool()
def generate_image(
    prompt: str,
    model: str | None = None,
    aspect_ratio: str | None = None,
    number_of_images: int | None = None,
    negative_prompt: str | None = None,
    output_mime_type: str | None = None,
    reference_image: str | None = None,
) -> dict[str, Any]:
    """テキストから画像を生成する。

    Imagen または Gemini モデルを使用して画像を生成する。

    モデル選択ロジック:
    - 解決後のモデル ID が "imagen-" で始まる場合 → Imagen API を使用
    - それ以外 → Gemini API を使用（デフォルト: Nano Banana 2）
    - reference_image を指定した場合 → Gemini の参照画像付き生成モードを使用

    Args:
        prompt: 生成する画像の説明テキスト
        model: 使用するモデル名またはエイリアス
                - Imagen: "imagen-4.0-fast-generate-001", "Imagen 4 Fast" 等
                - Gemini: "gemini-2.5-flash-preview-image-generation", "Nano Banana" 等
                - 省略時: config の defaultModel (Nano Banana 2) を使用
        aspect_ratio: アスペクト比 (1:1 / 16:9 / 9:16 / 4:3 / 3:4)。デフォルト: config 設定値 (16:9)
        number_of_images: 生成枚数（1〜4）。Gemini 使用時は無視される。デフォルト: config 設定値 (1)
        negative_prompt: 生成から除外したい要素の説明。Gemini 使用時は無視される
        output_mime_type: 出力形式 (image/png / image/jpeg)。Gemini 使用時は無視される。デフォルト: config 設定値 (image/png)
        reference_image: 参照画像（GCS URI: gs://bucket/file.png またはローカルパス）。
                         指定すると Gemini の参照画像付き生成モードを使用

    Returns:
        生成結果（images リストと model 名を含む辞書）
    """
    try:
        prompt = apply_prompt_prefix(prompt)
        service = get_service()
        tool_cfg = service.config.tools.generate_image

        # config のデフォルト値を適用（None のみフォールバック、falsy 値は維持）
        aspect_ratio = aspect_ratio if aspect_ratio is not None else tool_cfg.aspect_ratio
        number_of_images = number_of_images if number_of_images is not None else tool_cfg.number_of_images
        output_mime_type = output_mime_type if output_mime_type is not None else tool_cfg.output_mime_type

        # モデル解決（model=None → defaultModel → 解決）
        resolved_model = tool_cfg.resolve_model(model)

        # 解決後の ID プレフィックスでルーティング
        if resolved_model.lower().startswith("imagen-"):
            result = service.imagen.generate(
                prompt=prompt,
                model=resolved_model,
                aspect_ratio=aspect_ratio,
                number_of_images=number_of_images,
                output_mime_type=output_mime_type,
                negative_prompt=negative_prompt,
            )
        else:
            # Gemini（未登録モデル含む）
            result = service.gemini_image.generate(
                prompt=prompt,
                model=resolved_model,
                reference_image_gcs_uri=reference_image,
                aspect_ratio=aspect_ratio,
            )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("generate_image で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

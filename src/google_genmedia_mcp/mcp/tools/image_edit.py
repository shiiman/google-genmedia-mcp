"""画像編集 MCP ツールモジュール.

edit_image ツールを提供する。
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.errors import GenMediaError
from ..server import mcp
from ._utils import get_service

logger = logging.getLogger(__name__)


@mcp.tool()
def edit_image(
    prompt: str,
    reference_image: str,
    edit_mode: str = "inpaint_insertion",
    mask_image: str | None = None,
    model: str | None = None,
    number_of_images: int = 1,
    negative_prompt: str | None = None,
) -> dict[str, Any]:
    """Imagen モデルで画像を編集する（インペインティング、アウトペインティング等）。

    Args:
        prompt: 編集内容の説明テキスト
        reference_image: 参照画像（GCS URI: gs://bucket/file.png またはローカルパス）
        edit_mode: 編集モード
            - inpaint_insertion: マスク領域にオブジェクトを追加
            - inpaint_removal: マスク領域のオブジェクトを除去
            - outpaint: 画像の外側を拡張
            - background_replacement: 背景を置換
        mask_image: マスク画像（inpaint 系で必須、GCS URI またはローカルパス）
        model: 使用するモデル名またはエイリアス（省略時は imagen-4.0-generate-001）
        number_of_images: 生成枚数
        negative_prompt: 生成から除外したい要素の説明

    Returns:
        生成結果（編集済み画像ファイルパスを含む辞書）
    """
    try:
        result = get_service().imagen_edit.edit(
            prompt=prompt,
            reference_image=reference_image,
            edit_mode=edit_mode,
            mask_image=mask_image,
            model=model,
            number_of_images=number_of_images,
            negative_prompt=negative_prompt,
        )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("edit_image で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

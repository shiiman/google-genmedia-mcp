"""画像生成 MCP ツールモジュール.

generate_image ツールを提供する（Gemini による生成・参照画像編集）。
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
    reference_image: str | None = None,
) -> dict[str, Any]:
    """テキストから画像を生成する（Gemini）。

    reference_image を指定すると、その画像を入力にした編集（参照画像編集）を行う。

    Args:
        prompt: 生成・編集の指示テキスト
        model: 使用するモデル名またはエイリアス（省略時は config の defaultModel: Nano Banana 2）
        aspect_ratio: アスペクト比 (1:1 / 16:9 / 9:16 / 4:3 / 3:4)。デフォルト: config 設定値 (16:9)
        reference_image: 参照画像（GCS URI: gs://bucket/file.png またはローカルパス）。
                         指定すると参照画像をもとに編集する

    Returns:
        生成結果（images リストと model 名を含む辞書）
    """
    try:
        prompt = apply_prompt_prefix(prompt)
        service = get_service()
        tool_cfg = service.config.tools.generate_image

        aspect_ratio = aspect_ratio if aspect_ratio is not None else tool_cfg.aspect_ratio
        resolved_model = tool_cfg.resolve_model(model)

        result = service.gemini_image.generate(
            prompt=prompt,
            model=resolved_model,
            reference_image=reference_image,
            aspect_ratio=aspect_ratio,
        )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("generate_image で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

"""Lyria 音楽生成 MCP ツールモジュール.

generate_music ツールを提供する。
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.errors import GenMediaError
from ..server import mcp
from ._utils import apply_prompt_prefix, get_service

logger = logging.getLogger(__name__)


@mcp.tool()
def generate_music(
    prompt: str,
    model: str | None = None,
    negative_prompt: str | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Lyria モデルでテキストから音楽を生成する。

    注意:
    - この機能は Vertex AI または OAuth 認証方式でのみ利用可能です
    - 生成される音楽はインストゥルメンタルのみ（ボーカルなし）
    - 生成される音楽は 30 秒固定です

    Args:
        prompt: 生成する音楽の説明（例: "穏やかなピアノ曲、ジャズ風"）
        model: 使用するモデル名またはエイリアス（省略時はデフォルト lyria-002）
        negative_prompt: 生成から除外したい要素
        seed: 再現性用シード値（0〜2147483647）

    Returns:
        生成結果（30 秒の WAV ファイルパスを含む辞書）
    """
    try:
        prompt = apply_prompt_prefix(prompt)
        result = get_service().lyria.generate_music(
            prompt=prompt,
            model=model,
            negative_prompt=negative_prompt,
            seed=seed,
        )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("generate_music で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

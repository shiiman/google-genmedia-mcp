"""Veo MCP ツールモジュール.

generate_video と generate_video_from_image ツールを提供する。
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.errors import GenMediaError
from ..server import mcp
from ._utils import get_service

logger = logging.getLogger(__name__)


@mcp.tool()
def generate_video(
    prompt: str,
    model: str | None = None,
    aspect_ratio: str = "16:9",
    duration_seconds: int = 5,
    number_of_videos: int = 1,
) -> dict[str, Any]:
    """Veo モデルでテキストから動画を生成する。

    注意: 動画生成には数分かかる場合があります（ポーリングで完了を待機）。

    Args:
        prompt: 生成する動画の説明テキスト
        model: 使用するモデル名またはエイリアス（省略時はデフォルトモデル）
        aspect_ratio: アスペクト比 (16:9 / 9:16)
        duration_seconds: 動画の長さ（秒、5〜8）
        number_of_videos: 生成本数

    Returns:
        生成結果（動画ファイルパスを含む辞書）
    """
    try:
        result = get_service().veo.generate_from_text(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            number_of_videos=number_of_videos,
        )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("generate_video で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}


@mcp.tool()
def generate_video_from_image(
    prompt: str,
    image_gcs_uri: str,
    model: str | None = None,
    aspect_ratio: str = "16:9",
    duration_seconds: int = 5,
) -> dict[str, Any]:
    """Veo モデルで画像から動画を生成する（Image-to-Video）。

    注意: 動画生成には数分かかる場合があります（ポーリングで完了を待機）。

    Args:
        prompt: 動画の動きや内容を説明するテキスト
        image_gcs_uri: 参照画像の GCS URI (例: gs://bucket/image.jpg)
        model: 使用するモデル名またはエイリアス（省略時はデフォルトモデル）
        aspect_ratio: アスペクト比 (16:9 / 9:16)
        duration_seconds: 動画の長さ（秒）

    Returns:
        生成結果（動画ファイルパスを含む辞書）
    """
    try:
        result = get_service().veo.generate_from_image(
            prompt=prompt,
            image_gcs_uri=image_gcs_uri,
            model=model,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
        )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("generate_video_from_image で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

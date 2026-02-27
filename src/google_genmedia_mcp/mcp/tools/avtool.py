"""AV ツール MCP ツールモジュール.

combine_audio_video ツールを提供する。
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.errors import GenMediaError
from ..server import mcp
from ._utils import get_service

logger = logging.getLogger(__name__)


@mcp.tool()
def combine_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str | None = None,
) -> dict[str, Any]:
    """動画と音声を ffmpeg で合成する。

    前提: ffmpeg がシステムにインストールされている必要があります。
    インストール: macOS: brew install ffmpeg、Ubuntu: apt install ffmpeg

    Args:
        video_path: 動画ファイルのローカルパス
        audio_path: 音声ファイルのローカルパス
        output_path: 出力ファイルパス（省略時は出力ディレクトリに自動生成）

    Returns:
        {"output_path": ..., "video_path": ..., "audio_path": ...}
    """
    try:
        result = get_service().avtool.combine(
            video_path=video_path,
            audio_path=audio_path,
            output_path=output_path,
        )
        return result
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("combine_audio_video で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

"""Chirp TTS MCP ツールモジュール.

generate_speech ツールを提供する。
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.errors import GenMediaError
from ..server import mcp
from ._utils import get_service

logger = logging.getLogger(__name__)


@mcp.tool()
def generate_speech(
    text: str,
    voice: str | None = None,
    language: str | None = None,
    audio_encoding: str = "mp3",
) -> dict[str, Any]:
    """Chirp 3 HD でテキストを音声に変換する。

    注意: この機能は Vertex AI または OAuth 認証方式でのみ利用可能です。
    API Key 方式では利用できません。

    Args:
        text: 音声に変換するテキスト
        voice: ボイス名（Aoede, Kore, Leda, Zephyr, Puck, Charon, Fenrir, Orus）
               省略時は config のデフォルト（Kore）
        language: 言語コード（ja-JP, en-US 等）
                  省略時は config のデフォルト（ja-JP）
        audio_encoding: 出力フォーマット（mp3 / ogg_opus / pcm）

    Returns:
        生成結果（音声ファイルパスを含む辞書）
    """
    try:
        result = get_service().chirp.synthesize(
            text=text,
            voice=voice,
            language=language,
            audio_encoding=audio_encoding,
        )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("generate_speech で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

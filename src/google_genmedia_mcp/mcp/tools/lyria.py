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

    Lyria 3 Pro（デフォルト）:
    - 最大約 184 秒の楽曲を生成（プロンプトで秒数を指定可能）
    - ボーカル・歌詞対応（プロンプトに歌詞を含めると歌付き楽曲を生成）
    - [Verse], [Chorus], [Bridge] などのセクションタグで構成を制御可能
    - BPM やテンポはプロンプト内で自然言語で指定（例: "120 BPM"）
    - MP3 形式で出力
    - インストのみにしたい場合は "Instrumental only, no vocals" と指定

    Lyria 3 Clip:
    - 30 秒のクリップを生成
    - その他は Lyria 3 Pro と同じ機能

    Lyria 2:
    - 30 秒固定のインストゥルメンタル音楽を生成
    - negative_prompt と seed パラメータに対応
    - WAV 形式で出力

    注意:
    - Lyria 2 は Vertex AI または OAuth 認証方式でのみ利用可能です
    - Lyria 3 は API Key 方式でも利用可能です

    Args:
        prompt: 生成する音楽の説明。Lyria 3 では歌詞や [Verse]/[Chorus] タグも指定可能
        model: 使用するモデル名またはエイリアス（省略時はデフォルト Lyria 3 Pro）
        negative_prompt: 生成から除外したい要素（Lyria 2 のみ有効）
        seed: 再現性用シード値（0〜2147483647、Lyria 2 のみ有効）

    Returns:
        生成結果（音楽ファイルパス、歌詞テキスト等を含む辞書）
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

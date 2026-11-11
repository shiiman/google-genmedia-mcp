"""Omni MCP ツールモジュール.

generate_video_omni ツールを提供する（Gemini Omni / Vertex Interactions API）。
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.errors import GenMediaError
from ..server import mcp
from ._utils import apply_prompt_prefix, get_service

logger = logging.getLogger(__name__)


@mcp.tool()
def generate_video_omni(
    prompt: str | None = None,
    task: str | None = None,
    model: str | None = None,
    images: list[str] | None = None,
    videos: list[str] | None = None,
    resolution: str | None = None,
    aspect_ratio: str | None = None,
    duration_seconds: int | None = None,
    sample_count: int = 1,
    temperature: float | None = None,
    top_p: float | None = None,
) -> dict[str, Any]:
    """Gemini Omni で動画を生成・編集・延長・アップスケールする（音声付き）。

    Vertex AI または OAuth 認証が必要です（global エンドポイント専用）。
    テキストから動画、画像から動画、最初/最後のフレーム指定、動画編集に対応します。
    生成は同期的に完了を待つため、数十秒〜数分かかる場合があります。

    images の使われ方（task 省略時）: 1 枚 = 最初のフレーム、2 枚 = 最初と最後のフレーム（指定順）。
    被写体やスタイルの参照として使う場合は task=reference_to_video を指定してください。

    Args:
        prompt: 生成・編集・延長の指示テキスト。task=upscale では指定不可、それ以外は必須
        task: 明示タスク。extend（入力動画の続きを約 10 秒生成）/ upscale（1080p または 4k に高解像度化）/
            reference_to_video（images を被写体・スタイル参照として使用）。省略時は入力から自動判定。
            extend / upscale は videos をちょうど 1 本指定し、images・aspect_ratio・duration_seconds は指定不可
        model: 使用するモデル名またはエイリアス（省略時はデフォルトモデル: Omni）
        images: 入力画像（最大 10 枚）。ローカルパス（20MB まで）または gs:// URI
        videos: 入力動画（最大 3 本）。ローカルパス（20MB まで）または gs:// URI
        resolution: 出力解像度（360p / 720p / 1080p / 4k）。省略時はモデルの既定値
        aspect_ratio: アスペクト比（16:9 / 9:16）。省略時はモデルの既定値
        duration_seconds: 動画の長さ（3〜15 秒）。省略時はモデルの既定値
        sample_count: 生成本数（1〜3）。複数本は逐次生成するため時間と料金が本数分かかる
        temperature: サンプリング温度（0.0〜2.0）
        top_p: nucleus sampling の確率質量（0.0〜1.0）

    Returns:
        生成結果（動画ファイルパスを含む辞書。モデルがテキストを返した場合は text も含む）
    """
    try:
        if prompt is not None and prompt.strip():
            prompt = apply_prompt_prefix(prompt)

        result = get_service().omni.generate(
            prompt=prompt,
            task=task,
            model=model,
            images=images,
            videos=videos,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            sample_count=sample_count,
            temperature=temperature,
            top_p=top_p,
        )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("generate_video_omni で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

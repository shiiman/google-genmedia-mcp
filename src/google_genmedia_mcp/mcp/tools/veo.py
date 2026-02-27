"""Veo MCP ツールモジュール.

generate_video と generate_video_from_image ツールを提供する。
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.errors import GenMediaError
from ..server import mcp
from ._utils import apply_prompt_prefix, get_service

logger = logging.getLogger(__name__)


@mcp.tool()
def generate_video(
    prompt: str,
    model: str | None = None,
    aspect_ratio: str | None = None,
    duration_seconds: int | None = None,
    number_of_videos: int | None = None,
    generate_audio: bool | None = None,
) -> dict[str, Any]:
    """Veo モデルでテキストから動画を生成する。

    注意: 動画生成には数分かかる場合があります（ポーリングで完了を待機）。

    Args:
        prompt: 生成する動画の説明テキスト
        model: 使用するモデル名またはエイリアス（省略時はデフォルトモデル）
        aspect_ratio: アスペクト比。モデルにより対応値が異なる。デフォルト: config 設定値 (16:9)
        duration_seconds: 動画の長さ（秒）。モデルにより有効値が異なる。デフォルト: config 設定値 (8)
        number_of_videos: 生成本数。モデルにより上限が異なる。デフォルト: config 設定値 (1)
        generate_audio: 音声付き動画を生成するか（Veo 3+ のみ対応）。デフォルト: config 設定値 (Veo 3+ では自動的に True)

    Returns:
        生成結果（動画ファイルパスを含む辞書）
    """
    try:
        prompt = apply_prompt_prefix(prompt)
        tool_cfg = get_service().config.tools.generate_video

        # config のデフォルト値を適用（None のみフォールバック、falsy 値は維持）
        aspect_ratio = aspect_ratio if aspect_ratio is not None else tool_cfg.aspect_ratio
        duration_seconds = duration_seconds if duration_seconds is not None else tool_cfg.duration_seconds
        number_of_videos = number_of_videos if number_of_videos is not None else tool_cfg.number_of_videos
        generate_audio = generate_audio if generate_audio is not None else tool_cfg.generate_audio

        result = get_service().veo.generate_from_text(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            number_of_videos=number_of_videos,
            generate_audio=generate_audio,
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
    aspect_ratio: str | None = None,
    duration_seconds: int | None = None,
    generate_audio: bool | None = None,
) -> dict[str, Any]:
    """Veo モデルで画像から動画を生成する（Image-to-Video）。

    注意: 動画生成には数分かかる場合があります（ポーリングで完了を待機）。

    Args:
        prompt: 動画の動きや内容を説明するテキスト
        image_gcs_uri: 参照画像の GCS URI (例: gs://bucket/image.jpg)
        model: 使用するモデル名またはエイリアス（省略時はデフォルトモデル）
        aspect_ratio: アスペクト比。モデルにより対応値が異なる。デフォルト: config 設定値 (16:9)
        duration_seconds: 動画の長さ（秒）。モデルにより有効値が異なる。デフォルト: config 設定値 (8)
        generate_audio: 音声付き動画を生成するか（Veo 3+ のみ対応）。デフォルト: config 設定値 (Veo 3+ では自動的に True)

    Returns:
        生成結果（動画ファイルパスを含む辞書）
    """
    try:
        prompt = apply_prompt_prefix(prompt)
        tool_cfg = get_service().config.tools.generate_video_from_image

        # config のデフォルト値を適用（None のみフォールバック、falsy 値は維持）
        aspect_ratio = aspect_ratio if aspect_ratio is not None else tool_cfg.aspect_ratio
        duration_seconds = duration_seconds if duration_seconds is not None else tool_cfg.duration_seconds
        generate_audio = generate_audio if generate_audio is not None else tool_cfg.generate_audio

        result = get_service().veo.generate_from_image(
            prompt=prompt,
            image_gcs_uri=image_gcs_uri,
            model=model,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            generate_audio=generate_audio,
        )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("generate_video_from_image で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

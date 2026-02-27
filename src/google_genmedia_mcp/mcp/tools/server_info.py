"""サーバー情報 MCP ツールモジュール.

server_info ツールを提供する。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ...core.errors import GenMediaError
from ...utils.config import get_config_path
from ..server import mcp
from ._utils import get_service

logger = logging.getLogger(__name__)


@mcp.tool()
def server_info() -> dict[str, Any]:
    """MCP サーバーの情報と利用可能なツール・モデルの一覧を返す。

    Returns:
        サーバー情報（認証方式、GCS 可否、利用可能ツール、モデル一覧）
    """
    try:
        service = get_service()
        config = service.config
        has_cloud = service.has_cloud_credentials

        # 利用可能ツール
        phase1_tools = [
            "generate_image",
            "generate_video",
            "generate_video_from_image",
            "server_info",
        ]
        phase2_tools = [
            "edit_image",
            "generate_speech",
            "generate_music",
            "combine_audio_video",
        ]

        available_tools = phase1_tools.copy()
        available_tools.extend(phase2_tools)

        unavailable_tools = []
        if not has_cloud:
            # API Key 方式では Phase 2 の一部ツールが利用不可
            unavailable_tools = ["generate_speech", "generate_music"]

        # ツール別モデル・設定一覧
        speech_cfg = config.tools.generate_speech

        def _tool_models(cfg: object) -> dict[str, Any]:
            """ツール設定からモデル情報を抽出する."""
            return {
                "default_model": getattr(cfg, "default_model", None),
                "models": [
                    {"id": e.id, "aliases": e.aliases}
                    for e in getattr(cfg, "models", [])
                ],
            }

        tools_models: dict[str, Any] = {
            "generate_image": _tool_models(config.tools.generate_image),
            "edit_image": _tool_models(config.tools.edit_image),
            "generate_video": _tool_models(config.tools.generate_video),
            "generate_video_from_image": _tool_models(config.tools.generate_video_from_image),
            "generate_music": _tool_models(config.tools.generate_music),
        }

        # Chirp ボイス
        chirp_info: dict[str, Any] = {
            "default_voice": speech_cfg.default_voice,
            "default_language": speech_cfg.default_language,
            "voices": [
                {"name": v.name, "gender": v.gender}
                for v in speech_cfg.voices
            ],
        }

        # 設定ファイル診断情報
        config_path = get_config_path()
        config_diagnostics = {
            "config_file_path": str(config_path) if config_path else None,
            "config_file_found": config_path is not None and config_path.exists(),
            "home_directory": str(Path.home()),
        }

        return {
            "server": "google-genmedia-mcp",
            "version": "0.1.0",
            "config_diagnostics": config_diagnostics,
            "auth": {
                "method": config.auth.method,
                "has_cloud_credentials": has_cloud,
                "gcs_enabled": config.gcs.enabled and has_cloud,
            },
            "available_tools": available_tools,
            "unavailable_tools": unavailable_tools,
            "unavailable_reason": (
                "generate_speech と generate_music は Vertex AI または OAuth 認証方式が必要です"
                if unavailable_tools
                else None
            ),
            "tools_models": tools_models,
            "chirp": chirp_info,
        }
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("server_info で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}

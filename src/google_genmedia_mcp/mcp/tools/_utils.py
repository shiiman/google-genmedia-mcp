"""MCP ツールユーティリティ.

サービスシングルトンと共通ヘルパーを提供する。
"""

from __future__ import annotations

import logging

from ...services.service import GenMediaService

logger = logging.getLogger(__name__)

# グローバルサービスインスタンス
_service: GenMediaService | None = None


def get_service() -> GenMediaService:
    """グローバルサービスインスタンスを取得する（シングルトン）."""
    global _service
    if _service is None:
        _service = GenMediaService()
    return _service


def reset_service() -> None:
    """グローバルサービスインスタンスをリセットする（テスト用）."""
    global _service
    _service = None

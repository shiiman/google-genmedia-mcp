"""GenMedia クライアントラッパーモジュール.

AuthManager 経由で各 SDK クライアントを遅延初期化するラッパー。
"""

from __future__ import annotations

import logging
from typing import Any

from .models import GenMediaConfig

logger = logging.getLogger(__name__)


class GenMediaClient:
    """各 SDK クライアントを遅延初期化するラッパークラス.

    genai / TTS / AI Platform の各クライアントを必要時に初期化する。
    """

    def __init__(self, config: GenMediaConfig) -> None:
        self._config = config
        self._genai_client: Any | None = None
        self._tts_client: Any | None = None
        self._aiplatform_client: Any | None = None
        self._auth_manager_instance: Any | None = None

    @property
    def _auth_manager(self) -> Any:
        """AuthManager のシングルトン."""
        if self._auth_manager_instance is None:
            from ..auth.manager import AuthManager
            self._auth_manager_instance = AuthManager()
        return self._auth_manager_instance

    @property
    def genai(self) -> Any:
        """google-genai SDK クライアント（遅延初期化）."""
        if self._genai_client is None:
            self._genai_client = self._auth_manager.create_genai_client(self._config)
        return self._genai_client

    @property
    def tts(self) -> Any | None:
        """Cloud TTS クライアント（遅延初期化）.

        API Key 方式では None を返す。
        """
        if self._tts_client is None:
            self._tts_client = self._auth_manager.create_tts_client(self._config)
        return self._tts_client

    @property
    def aiplatform(self) -> Any | None:
        """AI Platform クライアント（遅延初期化）.

        API Key 方式では None を返す。
        """
        if self._aiplatform_client is None:
            self._aiplatform_client = self._auth_manager.create_aiplatform_client(self._config)
        return self._aiplatform_client

    @property
    def has_cloud_credentials(self) -> bool:
        """Vertex AI または OAuth 認証方式かどうか.

        Phase 2 ツール（Chirp/Lyria）の利用可否チェックに使用する。
        """
        return self._config.auth.method in ("vertex_ai", "oauth")

    @property
    def config(self) -> GenMediaConfig:
        """設定を返す."""
        return self._config

"""認証マネージャーモジュール.

3 つの認証方式（API Key / Vertex AI / OAuth）の切り替えを担う。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core.models import GenMediaConfig

logger = logging.getLogger(__name__)


class AuthManager:
    """認証方式の切り替えを管理するクラス.

    以下の 3 方式をサポートする:
    - api_key: Google AI Studio API Key
    - vertex_ai: Application Default Credentials
    - oauth: OAuth ブラウザ認証フロー
    """

    def create_genai_client(self, config: GenMediaConfig) -> Any:
        """google-genai SDK のクライアントを作成する.

        Phase 1 全ツール（Imagen / Gemini Image / Veo）で使用する。

        Raises:
            AuthError: 認証設定が不完全な場合
        """
        from google import genai

        from ..core.errors import AuthError

        match config.auth.method:
            case "api_key":
                if not config.auth.api_key:
                    raise AuthError(
                        "API Key が設定されていません",
                        "AUTH_NO_API_KEY",
                        hint="config.yaml の auth.apiKey を設定するか、GENMEDIA_API_KEY 環境変数を設定してください",
                    )
                logger.debug("API Key 方式で genai クライアントを作成します")
                return genai.Client(api_key=config.auth.api_key)

            case "vertex_ai":
                if not config.auth.vertex_ai.project:
                    raise AuthError(
                        "Vertex AI のプロジェクト ID が設定されていません",
                        "AUTH_NO_PROJECT",
                        hint="config.yaml の auth.vertexAi.project を設定してください",
                    )
                logger.debug(
                    f"Vertex AI 方式で genai クライアントを作成します "
                    f"(project={config.auth.vertex_ai.project})"
                )
                return genai.Client(
                    vertexai=True,
                    project=config.auth.vertex_ai.project,
                    location=config.auth.vertex_ai.location,
                )

            case "oauth":
                credentials = self._load_oauth_credentials(config)
                logger.debug("OAuth 方式で genai クライアントを作成します")
                return genai.Client(credentials=credentials)

            case _:
                from ..core.errors import AuthError
                raise AuthError(
                    f"未知の認証方式: {config.auth.method}",
                    "AUTH_UNKNOWN_METHOD",
                    hint="auth.method は api_key / vertex_ai / oauth のいずれかを設定してください",
                )

    def create_tts_client(self, config: GenMediaConfig) -> Any | None:
        """Cloud TTS クライアントを作成する.

        Chirp TTS で使用する。
        API Key 方式では None を返す（TTS は API Key 非対応）。
        """
        if config.auth.method == "api_key":
            logger.debug("API Key 方式では TTS クライアントを作成できません")
            return None

        try:
            from google.cloud import texttospeech
        except ImportError:
            logger.warning(
                "google-cloud-texttospeech がインストールされていません。"
                "uv sync を実行してください"
            )
            return None

        credentials = self._get_cloud_credentials(config)
        client_options = {"quota_project_id": config.auth.vertex_ai.project}
        logger.debug("TTS クライアントを作成します")
        return texttospeech.TextToSpeechClient(
            credentials=credentials,
            client_options=client_options,
        )

    def create_aiplatform_client(self, config: GenMediaConfig) -> Any | None:
        """AI Platform クライアントを作成する.

        Lyria 音楽生成で使用する。
        API Key 方式では None を返す（AI Platform は API Key 非対応）。
        """
        if config.auth.method == "api_key":
            logger.debug("API Key 方式では AI Platform クライアントを作成できません")
            return None

        try:
            from google.cloud import aiplatform_v1
        except ImportError:
            logger.warning(
                "google-cloud-aiplatform がインストールされていません。"
                "uv sync を実行してください"
            )
            return None

        credentials = self._get_cloud_credentials(config)
        location = config.auth.vertex_ai.location
        client_options = {
            "api_endpoint": f"{location}-aiplatform.googleapis.com",
            "quota_project_id": config.auth.vertex_ai.project,
        }
        logger.debug("AI Platform クライアントを作成します")
        return aiplatform_v1.PredictionServiceClient(
            credentials=credentials,
            client_options=client_options,
        )

    def _load_oauth_credentials(self, config: GenMediaConfig) -> Any:
        """OAuth トークンファイルから credentials を読み込む."""
        from .oauth import OAuthManager
        return OAuthManager(config).load_credentials()

    def _get_cloud_credentials(self, config: GenMediaConfig) -> Any:
        """Vertex AI または OAuth の credentials を返す."""
        if config.auth.method == "vertex_ai":
            import google.auth
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            return creds
        else:
            return self._load_oauth_credentials(config)

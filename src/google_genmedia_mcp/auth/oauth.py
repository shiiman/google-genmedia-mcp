"""OAuth ブラウザ認証フローモジュール.

google-auth-oauthlib を使用したブラウザ認証フローと
トークンの保存・読み込みを提供する。
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.models import GenMediaConfig

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
TOKEN_FILENAME = "oauth_token.json"


def get_token_path() -> Path:
    """OAuth トークンファイルのパスを返す."""
    from ..utils.config import get_config_dir
    return get_config_dir() / TOKEN_FILENAME


class OAuthManager:
    """OAuth 認証フローマネージャー."""

    def __init__(self, config: GenMediaConfig) -> None:
        self._config = config

    def login(self) -> None:
        """ブラウザ認証フローを実行してトークンを保存する.

        Raises:
            AuthError: OAuth クライアント設定が不完全な場合
        """
        from google_auth_oauthlib.flow import InstalledAppFlow

        from ..core.errors import AuthError

        client_id = self._config.auth.oauth.client_id
        client_secret = self._config.auth.oauth.client_secret

        if not client_id or not client_secret:
            raise AuthError(
                "OAuth クライアント ID とクライアントシークレットが設定されていません",
                "AUTH_OAUTH_NO_CLIENT",
                hint="config.yaml の auth.oauth.clientId と auth.oauth.clientSecret を設定してください",
            )

        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        credentials = flow.run_local_server(port=0)

        token_path = get_token_path()
        token_path.parent.mkdir(parents=True, exist_ok=True)
        _write_token_secure(token_path, credentials.to_json())
        logger.debug("OAuth トークンを保存しました")
        print("認証が完了しました。トークンを保存しました。")

    def load_credentials(self) -> object:
        """保存済みトークンから credentials を読み込む.

        Returns:
            google.oauth2.credentials.Credentials インスタンス

        Raises:
            AuthError: トークンファイルが存在しない場合
        """
        from google.oauth2.credentials import Credentials

        from ..core.errors import AuthError

        token_path = get_token_path()
        if not token_path.exists():
            raise AuthError(
                "OAuth トークンが見つかりません。`google-genmedia-mcp auth login` を実行してください",
                "AUTH_OAUTH_NO_TOKEN",
                hint="google-genmedia-mcp auth login を実行して認証してください",
            )

        credentials = Credentials.from_authorized_user_file(  # type: ignore[no-untyped-call]
            str(token_path), SCOPES
        )
        if credentials.expired and credentials.refresh_token:
            from google.auth.transport.requests import Request
            credentials.refresh(Request())
            _write_token_secure(token_path, credentials.to_json())
            logger.debug("OAuth トークンをリフレッシュしました")

        return credentials


def _write_token_secure(token_path: Path, content: str) -> None:
    """トークンファイルを安全なパーミッション（0600）で保存する."""
    fd = os.open(
        str(token_path),
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)

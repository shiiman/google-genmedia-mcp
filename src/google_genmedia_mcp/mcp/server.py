"""MCP サーバーエントリーポイント.

FastMCP を使用した google-genmedia-mcp サーバーの初期化・起動。
"""

from __future__ import annotations

import argparse
import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("google_genmedia_mcp.mcp")

# FastMCP サーバーインスタンス
mcp = FastMCP(
    "Google GenMedia MCP Server",
    instructions="Google の生成メディア API（Imagen, Gemini Image, Veo, Chirp, Lyria）を "
                 "提供する MCP サーバー。画像・動画・音声・音楽の生成が可能。",
)


def _register_tools() -> None:
    """全 MCP ツールをサーバーに登録する."""
    from .tools import (
        avtool,  # noqa: F401
        chirp,  # noqa: F401
        image,  # noqa: F401
        image_edit,  # noqa: F401
        lyria,  # noqa: F401
        server_info,  # noqa: F401
        veo,  # noqa: F401
    )


def main() -> None:
    """MCP サーバーを起動する."""
    parser = argparse.ArgumentParser(description="Google GenMedia MCP Server")
    subparsers = parser.add_subparsers(dest="command")

    # auth サブコマンド
    auth_parser = subparsers.add_parser("auth", help="認証コマンド")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command")
    auth_subparsers.add_parser("login", help="OAuth 認証を実行する")

    # サーバー起動オプション
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=None,
        help="トランスポート種別 (デフォルト: 設定値)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="サーバーホスト (SSE/HTTP 時)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="サーバーポート (SSE/HTTP 時)",
    )

    args = parser.parse_args()

    # auth コマンドの処理
    if args.command == "auth":
        if args.auth_command == "login":
            from ..auth.oauth import OAuthManager
            from ..utils.config import get_config
            config = get_config()
            OAuthManager(config).login()
        else:
            auth_parser.print_help()
        return

    # サーバー起動
    from ..utils.config import get_config
    config = get_config()

    # ログ設定
    logging.basicConfig(
        level=getattr(logging, config.server.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    transport = args.transport or config.server.transport
    host = args.host or config.server.host
    port = args.port or config.server.port

    # ツール登録
    _register_tools()

    logger.info(f"Google GenMedia MCP Server を起動します（トランスポート: {transport}）")

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        mcp.run(transport="sse", host=host, port=port)  # type: ignore[call-arg]
    else:
        mcp.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()

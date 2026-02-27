"""エラー階層定義モジュール.

google-genmedia-mcp で使用するエラークラスを提供する。
"""

from __future__ import annotations


class GenMediaError(Exception):
    """google-genmedia-mcp の基底エラークラス."""

    def __init__(
        self,
        message: str,
        code: str = "GENMEDIA_ERROR",
        hint: str = "",
    ) -> None:
        super().__init__(message)
        self.user_message = message
        self.debug_code = code
        self.hint = hint


class AuthError(GenMediaError):
    """認証エラー."""

    def __init__(self, message: str, code: str = "AUTH_ERROR", hint: str = "") -> None:
        super().__init__(message, code, hint)


class ConfigError(GenMediaError):
    """設定エラー."""

    def __init__(self, message: str, code: str = "CONFIG_ERROR", hint: str = "") -> None:
        super().__init__(message, code, hint)


class ModelNotFoundError(GenMediaError):
    """モデルが見つからないエラー."""

    def __init__(self, message: str, code: str = "MODEL_NOT_FOUND", hint: str = "") -> None:
        super().__init__(message, code, hint)


class GenerationError(GenMediaError):
    """生成エラー."""

    def __init__(self, message: str, code: str = "GENERATION_ERROR", hint: str = "") -> None:
        super().__init__(message, code, hint)


class StorageError(GenMediaError):
    """ストレージエラー."""

    def __init__(self, message: str, code: str = "STORAGE_ERROR", hint: str = "") -> None:
        super().__init__(message, code, hint)


class UnsupportedAuthMethodError(GenMediaError):
    """認証方式がサポートされていないエラー（API Key 方式で Phase 2 ツール使用時）."""

    def __init__(self, message: str, code: str = "AUTH_NOT_SUPPORTED", hint: str = "") -> None:
        super().__init__(message, code, hint)

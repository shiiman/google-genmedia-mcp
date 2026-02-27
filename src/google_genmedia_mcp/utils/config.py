"""config.yaml ローダーモジュール.

YAML 設定ファイルの読み込みと環境変数オーバーライドを提供する。

検索順:
1. GENMEDIA_CONFIG_PATH 環境変数
2. ~/.google-genmedia-mcp/config.yaml
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..core.errors import ConfigError
from ..core.models import GenMediaConfig

logger = logging.getLogger(__name__)

CONFIG_DIR_NAME = ".google-genmedia-mcp"


def get_config_dir() -> Path:
    """設定ディレクトリのパスを返す."""
    return Path.home() / CONFIG_DIR_NAME


def get_config_path() -> Path | None:
    """設定ファイルのパスを返す.

    GENMEDIA_CONFIG_PATH 環境変数が設定されている場合はそちらを優先する。
    未設定の場合は ~/.google-genmedia-mcp/config.yaml を確認する。
    """
    custom = os.getenv("GENMEDIA_CONFIG_PATH")
    if custom:
        path = Path(custom).expanduser()
        if not path.exists():
            raise ConfigError(
                f"GENMEDIA_CONFIG_PATH で指定されたファイルが見つかりません: {path}",
                "CONFIG_NOT_FOUND",
                hint="GENMEDIA_CONFIG_PATH 環境変数のパスを確認してください",
            )
        return path
    default = Path.home() / CONFIG_DIR_NAME / "config.yaml"
    return default if default.exists() else None


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """環境変数で設定をオーバーライドする.

    サポートされる環境変数:
    - GENMEDIA_API_KEY: API Key を上書き
    - GENMEDIA_PROJECT: Vertex AI プロジェクト ID を上書き
    - GENMEDIA_LOCATION: Vertex AI リージョンを上書き
    - GENMEDIA_OUTPUT_DIR: 出力ディレクトリを上書き
    """
    if api_key := os.getenv("GENMEDIA_API_KEY"):
        data.setdefault("auth", {})["apiKey"] = api_key

    if project := os.getenv("GENMEDIA_PROJECT"):
        data.setdefault("auth", {}).setdefault("vertexAi", {})["project"] = project

    if location := os.getenv("GENMEDIA_LOCATION"):
        data.setdefault("auth", {}).setdefault("vertexAi", {})["location"] = location

    if output_dir := os.getenv("GENMEDIA_OUTPUT_DIR"):
        data.setdefault("output", {})["directory"] = output_dir

    return data


@lru_cache(maxsize=1)
def get_config() -> GenMediaConfig:
    """設定のシングルトンインスタンスを取得する.

    設定ファイルが存在しない場合はデフォルト値を使用する。
    """
    path = get_config_path()
    if path is None or not path.exists():
        searched = os.getenv("GENMEDIA_CONFIG_PATH") or str(
            Path.home() / CONFIG_DIR_NAME / "config.yaml"
        )
        logger.warning(
            "設定ファイルが見つかりません。デフォルト値で起動します。"
            f" (検索パス: {searched}, HOME={Path.home()})"
        )
        data: dict[str, Any] = {}
    else:
        logger.info(f"設定ファイルを読み込みます: {path}")
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(
                f"設定ファイルの YAML パースに失敗しました: {path}",
                "CONFIG_PARSE_ERROR",
                hint="config.yaml の構文を確認してください",
            ) from e

    data = _apply_env_overrides(data)
    return GenMediaConfig.model_validate(data)


def reload_config() -> GenMediaConfig:
    """設定キャッシュをクリアして再読み込みする.

    テストや設定変更後の再読み込みに使用する。
    """
    get_config.cache_clear()
    return get_config()

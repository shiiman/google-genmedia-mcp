"""utils/config.py のユニットテスト."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from google_genmedia_mcp.core.models import GenMediaConfig
from google_genmedia_mcp.utils.config import get_config, reload_config


class TestGetConfig:
    """get_config() のテスト."""

    def setup_method(self) -> None:
        """各テスト前にキャッシュをクリア."""
        reload_config.cache_clear() if hasattr(reload_config, "cache_clear") else None
        get_config.cache_clear()

    def test_default_config_when_no_file(self) -> None:
        """設定ファイルがない場合はデフォルト値を返すことを検証."""
        with patch.dict(os.environ, {}, clear=False):
            env_backup = os.environ.pop("GENMEDIA_CONFIG_PATH", None)
            try:
                with patch("google_genmedia_mcp.utils.config.get_config_path", return_value=None):
                    config = get_config()
                    assert isinstance(config, GenMediaConfig)
                    assert config.auth.method == "api_key"
            finally:
                if env_backup is not None:
                    os.environ["GENMEDIA_CONFIG_PATH"] = env_backup

    def test_load_from_yaml_file(self) -> None:
        """YAML ファイルから設定を読み込むことを検証."""
        config_data = {
            "auth": {
                "method": "vertex_ai",
                "vertexAi": {
                    "project": "my-test-project",
                    "location": "us-east1",
                },
            },
            "output": {
                "directory": "/tmp/test-output",
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config_data, f)
            tmp_path = f.name

        try:
            get_config.cache_clear()
            with patch("google_genmedia_mcp.utils.config.get_config_path",
                       return_value=Path(tmp_path)):
                config = get_config()
                assert config.auth.method == "vertex_ai"
                assert config.auth.vertex_ai.project == "my-test-project"
                assert config.auth.vertex_ai.location == "us-east1"
                assert config.output.directory == "/tmp/test-output"
        finally:
            os.unlink(tmp_path)
            get_config.cache_clear()

    def test_env_override_api_key(self) -> None:
        """GENMEDIA_API_KEY 環境変数で API Key が上書きされることを検証."""
        get_config.cache_clear()
        with (
            patch.dict(os.environ, {"GENMEDIA_API_KEY": "env-test-key"}),
            patch("google_genmedia_mcp.utils.config.get_config_path", return_value=None),
        ):
            config = get_config()
            assert config.auth.api_key == "env-test-key"
        get_config.cache_clear()

    def test_singleton(self) -> None:
        """get_config() がシングルトンを返すことを検証."""
        with patch("google_genmedia_mcp.utils.config.get_config_path", return_value=None):
            config1 = get_config()
            config2 = get_config()
            assert config1 is config2

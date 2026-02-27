"""services/storage.py のユニットテスト."""

from __future__ import annotations

from pathlib import Path

import pytest

from google_genmedia_mcp.core.errors import StorageError
from google_genmedia_mcp.core.models import GenMediaConfig
from google_genmedia_mcp.services.storage import StorageService, _parse_gcs_uri


class TestStorageService:
    """StorageService のテスト."""

    def _make_config(self, output_dir: str, gcs_enabled: bool = False) -> GenMediaConfig:
        config = GenMediaConfig()
        config.output.directory = output_dir
        config.gcs.enabled = gcs_enabled
        return config

    def test_save_image_png(self, tmp_path: Path) -> None:
        """PNG 画像の保存を検証."""
        config = self._make_config(str(tmp_path))
        service = StorageService(config)
        path = service.save_image(b"fake-png-data", "image/png", "test")
        assert path.endswith(".png")
        assert Path(path).exists()
        assert Path(path).read_bytes() == b"fake-png-data"

    def test_save_image_jpeg(self, tmp_path: Path) -> None:
        """JPEG 画像の保存を検証."""
        config = self._make_config(str(tmp_path))
        service = StorageService(config)
        path = service.save_image(b"fake-jpeg-data", "image/jpeg", "test")
        assert path.endswith(".jpg")

    def test_save_audio_mp3(self, tmp_path: Path) -> None:
        """MP3 音声の保存を検証."""
        config = self._make_config(str(tmp_path))
        service = StorageService(config)
        path = service.save_audio(b"fake-mp3-data", "mp3", "test")
        assert path.endswith(".mp3")
        assert Path(path).exists()

    def test_save_audio_wav(self, tmp_path: Path) -> None:
        """WAV 音声の保存を検証."""
        config = self._make_config(str(tmp_path))
        service = StorageService(config)
        path = service.save_audio(b"fake-wav-data", "wav", "test")
        assert path.endswith(".wav")

    def test_save_video_from_gcs_disabled(self, tmp_path: Path) -> None:
        """GCS が無効な場合のエラーを検証."""
        config = self._make_config(str(tmp_path), gcs_enabled=False)
        service = StorageService(config)
        with pytest.raises(StorageError) as exc_info:
            service.save_video_from_gcs("gs://bucket/video.mp4")
        assert exc_info.value.debug_code == "GCS_DISABLED"


class TestParseGcsUri:
    """_parse_gcs_uri のテスト."""

    def test_valid_uri(self) -> None:
        """有効な GCS URI の解析を検証."""
        bucket, blob = _parse_gcs_uri("gs://my-bucket/path/to/file.mp4")
        assert bucket == "my-bucket"
        assert blob == "path/to/file.mp4"

    def test_bucket_only(self) -> None:
        """バケットのみの URI を検証."""
        bucket, blob = _parse_gcs_uri("gs://my-bucket")
        assert bucket == "my-bucket"
        assert blob == ""

    def test_invalid_uri(self) -> None:
        """無効な URI のエラーを検証."""
        with pytest.raises(StorageError) as exc_info:
            _parse_gcs_uri("https://storage.googleapis.com/bucket/file")
        assert exc_info.value.debug_code == "GCS_INVALID_URI"

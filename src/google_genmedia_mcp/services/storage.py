"""ストレージサービスモジュール.

生成されたメディアのローカル保存と GCS へのアクセスを提供する。
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path

from ..core.errors import StorageError
from ..core.models import GenMediaConfig

logger = logging.getLogger(__name__)


class StorageService:
    """メディアファイルのストレージサービス."""

    def __init__(self, config: GenMediaConfig) -> None:
        self._config = config
        self._output_dir = Path(config.output.directory).expanduser()

    def ensure_output_dir(self) -> Path:
        """出力ディレクトリを作成して返す."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        return self._output_dir

    def save_image(self, image_bytes: bytes, mime_type: str, prefix: str = "image") -> str:
        """画像をローカルに保存して絶対パスを返す.

        Args:
            image_bytes: 画像バイナリデータ
            mime_type: MIME タイプ（image/png / image/jpeg 等）
            prefix: ファイル名プレフィックス

        Returns:
            保存したファイルの絶対パス
        """
        ext = "jpg" if "jpeg" in mime_type else "png"
        filename = f"{prefix}_{_timestamp()}.{ext}"
        path = self.ensure_output_dir() / filename
        path.write_bytes(image_bytes)
        logger.debug(f"画像を保存しました: {path}")
        return str(path)

    def save_audio(self, audio_bytes: bytes, encoding: str, prefix: str = "audio") -> str:
        """音声をローカルに保存して絶対パスを返す.

        Args:
            audio_bytes: 音声バイナリデータ
            encoding: エンコーディング（mp3 / ogg_opus / pcm / wav）
            prefix: ファイル名プレフィックス

        Returns:
            保存したファイルの絶対パス
        """
        ext_map = {"mp3": "mp3", "ogg_opus": "ogg", "pcm": "pcm", "wav": "wav"}
        ext = ext_map.get(encoding, "audio")
        filename = f"{prefix}_{_timestamp()}.{ext}"
        path = self.ensure_output_dir() / filename
        path.write_bytes(audio_bytes)
        logger.debug(f"音声を保存しました: {path}")
        return str(path)

    def save_video_from_bytes(self, video_bytes: bytes, prefix: str = "video") -> str:
        """動画バイナリをローカルに保存して絶対パスを返す."""
        filename = f"{prefix}_{_timestamp()}.mp4"
        path = self.ensure_output_dir() / filename
        path.write_bytes(video_bytes)
        logger.debug(f"動画を保存しました: {path}")
        return str(path)

    def save_video_from_gcs(self, gcs_uri: str, prefix: str = "video") -> str:
        """GCS から動画をダウンロードしてローカルに保存する.

        Vertex AI 方式のみ使用可能。

        Args:
            gcs_uri: GCS URI (gs://bucket/path)
            prefix: ファイル名プレフィックス

        Returns:
            保存したファイルの絶対パス

        Raises:
            StorageError: GCS が無効または URI が不正な場合
        """
        if not self._config.gcs.enabled:
            raise StorageError(
                "GCS が無効です。GCS を使用するには config.yaml で gcs.enabled: true を設定してください",
                "GCS_DISABLED",
                hint="Vertex AI 方式で gcs.enabled: true と gcs.bucket を設定してください",
            )

        try:
            from google.cloud import storage as gcs_module
        except ImportError as e:
            raise StorageError(
                "google-cloud-storage がインストールされていません",
                "GCS_NOT_INSTALLED",
            ) from e

        bucket_name, blob_name = _parse_gcs_uri(gcs_uri)
        client = gcs_module.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        filename = f"{prefix}_{_timestamp()}.mp4"
        path = self.ensure_output_dir() / filename
        blob.download_to_filename(str(path))
        logger.debug(f"GCS から動画をダウンロードしました: {gcs_uri} -> {path}")
        return str(path)

    def save_video_from_gcs_or_bytes(
        self, gcs_uri: str | None, video_bytes: bytes | None, prefix: str = "video"
    ) -> str:
        """GCS URI またはバイナリから動画を保存する."""
        if video_bytes is not None:
            return self.save_video_from_bytes(video_bytes, prefix)
        if gcs_uri is not None:
            return self.save_video_from_gcs(gcs_uri, prefix)
        raise StorageError("動画データが提供されていません", "VIDEO_NO_DATA")


def _timestamp() -> str:
    """タイムスタンプ文字列を返す."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    """GCS URI をバケット名とパスに分解する.

    Args:
        uri: gs://bucket/path 形式の URI

    Returns:
        (bucket_name, blob_name) のタプル

    Raises:
        StorageError: URI 形式が不正な場合
    """
    if not uri.startswith("gs://"):
        raise StorageError(
            f"無効な GCS URI です: {uri}",
            "GCS_INVALID_URI",
            hint="GCS URI は gs://bucket-name/path 形式で指定してください",
        )
    path_part = uri[5:]
    parts = path_part.split("/", 1)
    bucket = parts[0]
    blob = parts[1] if len(parts) > 1 else ""
    return bucket, blob

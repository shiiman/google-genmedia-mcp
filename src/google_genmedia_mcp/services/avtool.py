"""AV ツールサービスモジュール.

ffmpeg を使用した音声/動画合成を提供する。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from ..core.errors import GenMediaError
from ..core.models import GenMediaConfig
from .storage import _timestamp

logger = logging.getLogger(__name__)


class AvToolService:
    """ffmpeg を使用した音声/動画合成サービス."""

    def __init__(self, config: GenMediaConfig) -> None:
        self._config = config
        self._output_dir = Path(config.output.directory).expanduser()

    def combine(
        self,
        video_path: str,
        audio_path: str,
        output_path: str | None = None,
    ) -> dict[str, str]:
        """動画と音声を合成する.

        Args:
            video_path: 動画ファイルのローカルパス
            audio_path: 音声ファイルのローカルパス
            output_path: 出力ファイルパス（省略時は自動生成）

        Returns:
            {"output_path": ..., "video_path": ..., "audio_path": ...}

        Raises:
            GenMediaError: ffmpeg が見つからない場合、または合成に失敗した場合
        """
        if not shutil.which("ffmpeg"):
            raise GenMediaError(
                "ffmpeg が見つかりません。インストールしてください",
                "FFMPEG_NOT_FOUND",
                hint="macOS: brew install ffmpeg、Ubuntu: apt install ffmpeg",
            )

        # パス検証（パストラバーサル防止）
        resolved_video = Path(video_path).resolve()
        resolved_audio = Path(audio_path).resolve()

        if not resolved_video.exists():
            raise GenMediaError(
                f"動画ファイルが見つかりません: {video_path}",
                "VIDEO_FILE_NOT_FOUND",
            )
        if not resolved_video.is_file():
            raise GenMediaError(
                f"動画パスがファイルではありません: {video_path}",
                "VIDEO_NOT_A_FILE",
            )

        if not resolved_audio.exists():
            raise GenMediaError(
                f"音声ファイルが見つかりません: {audio_path}",
                "AUDIO_FILE_NOT_FOUND",
            )
        if not resolved_audio.is_file():
            raise GenMediaError(
                f"音声パスがファイルではありません: {audio_path}",
                "AUDIO_NOT_A_FILE",
            )

        if output_path is None:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(self._output_dir / f"combined_{_timestamp()}.mp4")
        else:
            # 出力先パスも resolve する
            output_path = str(Path(output_path).resolve())

        # 安全な resolve 済みパスを使用
        video_path = str(resolved_video)
        audio_path = str(resolved_audio)

        logger.info(f"ffmpeg で動画と音声を合成します: {video_path} + {audio_path} -> {output_path}")

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i", video_path,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-y",
                    output_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired as e:
            raise GenMediaError(
                "ffmpeg 合成がタイムアウトしました（600秒）",
                "FFMPEG_TIMEOUT",
            ) from e
        except subprocess.CalledProcessError as e:
            raise GenMediaError(
                f"ffmpeg 合成に失敗しました: {e.stderr}",
                "FFMPEG_ERROR",
            ) from e

        logger.info(f"動画と音声の合成が完了しました: {output_path}")
        return {
            "output_path": output_path,
            "video_path": video_path,
            "audio_path": audio_path,
        }

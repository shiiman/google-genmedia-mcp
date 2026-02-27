"""Chirp TTS サービスモジュール.

Chirp 3 HD を使用したテキスト音声変換を提供する。
"""

from __future__ import annotations

import logging

from ..core.client import GenMediaClient
from ..core.errors import AuthError, GenerationError, UnsupportedAuthMethodError
from ..core.models import GeneratedAudio, GenerationResult, GenMediaConfig
from .storage import StorageService

logger = logging.getLogger(__name__)


class ChirpService:
    """Chirp 3 HD TTS サービス."""

    def __init__(
        self,
        client: GenMediaClient,
        config: GenMediaConfig,
        storage: StorageService,
    ) -> None:
        self._client = client
        self._config = config
        self._storage = storage

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        language: str | None = None,
        audio_encoding: str = "mp3",
    ) -> GenerationResult:
        """テキストを音声に変換する.

        Args:
            text: 変換するテキスト
            voice: ボイス名（Kore, Charon, Puck 等。省略時は config のデフォルト）
            language: 言語コード（ja-JP, en-US 等。省略時は config のデフォルト）
            audio_encoding: 出力フォーマット（mp3 / ogg_opus / pcm）

        Returns:
            生成結果（音声ファイルパスを含む）

        Raises:
            UnsupportedAuthMethodError: API Key 方式で呼び出された場合
        """
        if not self._client.has_cloud_credentials:
            raise UnsupportedAuthMethodError(
                "chirp_tts は Vertex AI または OAuth 認証方式で利用可能です",
                "AUTH_NOT_SUPPORTED",
                hint="config.yaml の auth.method を vertex_ai または oauth に設定してください",
            )

        tts_client = self._client.tts
        if tts_client is None:
            raise AuthError(
                "TTS クライアントの初期化に失敗しました。"
                "google-cloud-texttospeech がインストールされているか確認してください",
                "TTS_CLIENT_ERROR",
                hint="uv sync --extra phase2 を実行してください",
            )

        resolved_voice = voice if voice is not None else self._config.tools.generate_speech.default_voice
        resolved_lang = language if language is not None else self._config.tools.generate_speech.default_language
        voice_name = f"{resolved_lang}-Chirp3-HD-{resolved_voice}"

        logger.info(f"Chirp TTS で音声合成を開始します (voice={voice_name})")

        try:
            from google.cloud import texttospeech

            enc_map = {
                "mp3": texttospeech.AudioEncoding.MP3,
                "ogg_opus": texttospeech.AudioEncoding.OGG_OPUS,
                "pcm": texttospeech.AudioEncoding.LINEAR16,
            }

            response = tts_client.synthesize_speech(
                input=texttospeech.SynthesisInput(text=text),
                voice=texttospeech.VoiceSelectionParams(
                    language_code=resolved_lang,
                    name=voice_name,
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=enc_map.get(audio_encoding, texttospeech.AudioEncoding.MP3)
                ),
            )
        except Exception as e:
            raise GenerationError(
                f"Chirp TTS 音声合成に失敗しました: {e!s}",
                "CHIRP_TTS_ERROR",
            ) from e

        path = self._storage.save_audio(response.audio_content, audio_encoding, "chirp")
        audio = GeneratedAudio(
            file_path=path,
            audio_encoding=audio_encoding,
            model=voice_name,
        )
        logger.info(f"Chirp TTS で音声を生成しました: {path}")
        return GenerationResult(audios=[audio], model=voice_name)

"""Lyria 音楽生成サービスモジュール.

Lyria モデルを使用した音楽生成を提供する。

制約:
- インストゥルメンタルのみ（ボーカルなし）
- 30 秒固定
- Vertex AI または OAuth 認証方式が必要
"""

from __future__ import annotations

import base64
import logging

from ..core.client import GenMediaClient
from ..core.errors import AuthError, GenerationError, UnsupportedAuthMethodError
from ..core.models import GeneratedAudio, GenerationResult, GenMediaConfig
from .storage import StorageService

logger = logging.getLogger(__name__)

LYRIA_DURATION_SECONDS = 30.0


class LyriaService:
    """Lyria 音楽生成サービス."""

    def __init__(
        self,
        client: GenMediaClient,
        config: GenMediaConfig,
        storage: StorageService,
    ) -> None:
        self._client = client
        self._config = config
        self._storage = storage

    def resolve_model(self, model: str | None) -> str:
        """モデル名またはエイリアスを解決する."""
        return self._config.tools.generate_music.resolve_model(model)

    def generate_music(
        self,
        prompt: str,
        model: str | None = None,
        negative_prompt: str | None = None,
        seed: int | None = None,
    ) -> GenerationResult:
        """テキストから音楽を生成する.

        Args:
            prompt: 生成する音楽の説明（100〜512文字推奨）
            model: モデル名またはエイリアス
            negative_prompt: 生成から除外したい要素
            seed: 再現性用シード（0〜2147483647）

        Returns:
            生成結果（30 秒の WAV ファイルパスを含む）

        Raises:
            UnsupportedAuthMethodError: API Key 方式で呼び出された場合
        """
        if not self._client.has_cloud_credentials:
            raise UnsupportedAuthMethodError(
                "lyria_generate_music は Vertex AI または OAuth 認証方式で利用可能です",
                "AUTH_NOT_SUPPORTED",
                hint="config.yaml の auth.method を vertex_ai または oauth に設定してください",
            )

        ap_client = self._client.aiplatform
        if ap_client is None:
            raise AuthError(
                "AI Platform クライアントの初期化に失敗しました。"
                "google-cloud-aiplatform がインストールされているか確認してください",
                "AIPLATFORM_CLIENT_ERROR",
                hint="uv sync を実行してください",
            )

        resolved_model = self.resolve_model(model)
        project = self._config.auth.vertex_ai.project
        location = self._config.auth.vertex_ai.location

        if not project:
            raise AuthError(
                "Vertex AI のプロジェクト ID が設定されていません",
                "AUTH_NO_PROJECT",
                hint="config.yaml の auth.vertexAi.project を設定してください",
            )

        endpoint = (
            f"projects/{project}/locations/{location}/"
            f"publishers/google/models/{resolved_model}"
        )

        logger.info(f"Lyria で音楽生成を開始します (model={resolved_model})")

        try:
            instance: dict[str, object] = {"prompt": prompt}
            if negative_prompt:
                instance["negative_prompt"] = negative_prompt
            if seed is not None:
                instance["seed"] = seed

            from google.cloud import aiplatform_v1
            from google.protobuf import struct_pb2

            pb_struct = struct_pb2.Struct()
            for k, v in instance.items():
                pb_struct[k] = v

            pb_value = struct_pb2.Value(struct_value=pb_struct)

            request = aiplatform_v1.PredictRequest(
                endpoint=endpoint,
                instances=[pb_value],
            )
            response = ap_client.predict(request=request)
        except Exception as e:
            raise GenerationError(
                f"Lyria 音楽生成に失敗しました: {e!s}",
                "LYRIA_GENERATION_ERROR",
            ) from e

        # WAV データの取得
        predictions = list(response.predictions)
        if not predictions:
            raise GenerationError("Lyria が音楽を生成しませんでした", "LYRIA_NO_OUTPUT")

        pred = dict(predictions[0])
        audio_b64 = pred.get("bytesBase64Encoded") or pred.get("audio")
        if not audio_b64:
            raise GenerationError(
                "Lyria のレスポンスに音声データが含まれていません",
                "LYRIA_NO_AUDIO",
            )

        wav_bytes = base64.b64decode(str(audio_b64))
        path = self._storage.save_audio(wav_bytes, "wav", "lyria")
        audio = GeneratedAudio(
            file_path=path,
            audio_encoding="wav",
            model=resolved_model,
            duration_seconds=LYRIA_DURATION_SECONDS,
        )
        logger.info(f"Lyria で {LYRIA_DURATION_SECONDS} 秒の音楽を生成しました: {path}")
        return GenerationResult(audios=[audio], model=resolved_model)

"""Lyria 音楽生成サービスモジュール.

Lyria モデルを使用した音楽生成を提供する。

- Lyria 3 Pro/Clip: generateContent API（Gemini SDK）、ボーカル・歌詞対応、MP3 出力
- Lyria 2: Predict API（AI Platform）、インストゥルメンタルのみ、WAV 出力
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from ..core.client import GenMediaClient
from ..core.errors import AuthError, GenerationError, UnsupportedAuthMethodError
from ..core.models import GeneratedAudio, GenerationResult, GenMediaConfig
from .storage import StorageService

logger = logging.getLogger(__name__)

LYRIA2_DURATION_SECONDS = 30.0


def _is_lyria3(model_id: str) -> bool:
    """モデル ID が Lyria 3 系かどうかを判定する."""
    return model_id.startswith("lyria-3")


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

        Lyria 3 と Lyria 2 でバックエンドの API が異なる:
        - Lyria 3: genai SDK の generateContent API（ボーカル・歌詞対応）
        - Lyria 2: AI Platform の Predict API（インストゥルメンタルのみ）

        Args:
            prompt: 生成する音楽の説明
            model: モデル名またはエイリアス
            negative_prompt: 生成から除外したい要素（Lyria 2 のみ）
            seed: 再現性用シード（0〜2147483647、Lyria 2 のみ）

        Returns:
            生成結果（音楽ファイルパス、テキスト（歌詞等）を含む）
        """
        resolved_model = self.resolve_model(model)

        if _is_lyria3(resolved_model):
            if negative_prompt is not None:
                logger.warning(
                    "negative_prompt は Lyria 3 では無視されます（Lyria 2 のみ有効）"
                )
            if seed is not None:
                logger.warning(
                    "seed は Lyria 3 では無視されます（Lyria 2 のみ有効）"
                )
            return self._generate_lyria3(resolved_model, prompt)
        return self._generate_lyria2(resolved_model, prompt, negative_prompt, seed)

    def _generate_lyria3(
        self,
        resolved_model: str,
        prompt: str,
    ) -> GenerationResult:
        """Lyria 3 で音楽を生成する（generateContent API）."""
        from google.genai import types

        logger.info(f"Lyria 3 で音楽生成を開始します (model={resolved_model})")

        try:
            # Lyria 3 はグローバルエンドポイントが必要
            client = self._client.genai_global
            response = client.models.generate_content(
                model=resolved_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO", "TEXT"],
                ),
            )
        except Exception as e:
            raise GenerationError(
                f"Lyria 3 音楽生成に失敗しました: {e!s}",
                "LYRIA3_GENERATION_ERROR",
            ) from e

        return self._parse_lyria3_response(response, resolved_model)

    def _parse_lyria3_response(
        self,
        response: Any,
        resolved_model: str,
    ) -> GenerationResult:
        """Lyria 3 のレスポンスをパースする."""
        audios: list[GeneratedAudio] = []
        text_parts: list[str] = []

        for candidate in response.candidates or []:
            if not candidate.content or not candidate.content.parts:
                continue
            for part in candidate.content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    audio_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "audio/mp3"
                    # MIME タイプから拡張子を決定
                    encoding = "mp3" if "mp3" in mime_type or "mpeg" in mime_type else "wav"
                    path = self._storage.save_audio(audio_bytes, encoding, "lyria3")
                    audios.append(
                        GeneratedAudio(
                            file_path=path,
                            audio_encoding=encoding,
                            model=resolved_model,
                        )
                    )
                elif hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

        if not audios:
            raise GenerationError(
                "Lyria 3 が音楽を生成しませんでした",
                "LYRIA3_NO_OUTPUT",
            )

        logger.info(f"Lyria 3 で音楽を生成しました: {audios[0].file_path}")
        return GenerationResult(
            audios=audios,
            text="\n".join(text_parts) if text_parts else None,
            model=resolved_model,
        )

    def _generate_lyria2(
        self,
        resolved_model: str,
        prompt: str,
        negative_prompt: str | None,
        seed: int | None,
    ) -> GenerationResult:
        """Lyria 2 で音楽を生成する（Predict API）."""
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

        logger.info(f"Lyria 2 で音楽生成を開始します (model={resolved_model})")

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

            request = aiplatform_v1.PredictRequest(endpoint=endpoint)
            request._pb.instances.append(pb_value)
            response = ap_client.predict(request=request)
        except Exception as e:
            raise GenerationError(
                f"Lyria 2 音楽生成に失敗しました: {e!s}",
                "LYRIA_GENERATION_ERROR",
            ) from e

        # WAV データの取得
        predictions = list(response.predictions)
        if not predictions:
            raise GenerationError("Lyria 2 が音楽を生成しませんでした", "LYRIA_NO_OUTPUT")

        pred = dict(predictions[0])
        audio_b64 = pred.get("bytesBase64Encoded") or pred.get("audio")
        if not audio_b64:
            raise GenerationError(
                "Lyria 2 のレスポンスに音声データが含まれていません",
                "LYRIA_NO_AUDIO",
            )

        wav_bytes = base64.b64decode(str(audio_b64))
        path = self._storage.save_audio(wav_bytes, "wav", "lyria2")
        audio = GeneratedAudio(
            file_path=path,
            audio_encoding="wav",
            model=resolved_model,
            duration_seconds=LYRIA2_DURATION_SECONDS,
        )
        logger.info(f"Lyria 2 で {LYRIA2_DURATION_SECONDS} 秒の音楽を生成しました: {path}")
        return GenerationResult(audios=[audio], model=resolved_model)

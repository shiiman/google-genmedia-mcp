"""Gemini 画像生成・編集サービスモジュール.

Gemini モデルを使用した画像生成・参照画像編集を提供する。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..core.client import GenMediaClient
from ..core.errors import GenerationError
from ..core.models import GeneratedImage, GenerationResult, GenMediaConfig
from .storage import StorageService

logger = logging.getLogger(__name__)


class GeminiImageService:
    """Gemini 画像生成・編集サービス."""

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
        """モデル名またはエイリアスを正式モデル ID に解決する."""
        return self._config.tools.generate_image.resolve_model(model, "Gemini 画像モデル")

    def _get_genai_client(self, model_id: str) -> Any:
        """config の global フラグに基づいて genai クライアントを返す."""
        tool_cfg = self._config.tools.generate_image
        if tool_cfg.is_global_model(model_id):
            return self._client.genai_global
        return self._client.genai

    def generate(
        self,
        prompt: str,
        model: str | None = None,
        reference_image: str | None = None,
        aspect_ratio: str | None = None,
    ) -> GenerationResult:
        """Gemini を使用して画像を生成・編集する.

        Args:
            prompt: 生成・編集の指示テキスト
            model: モデル名またはエイリアス
            reference_image: 参照画像（ローカルパス または GCS URI）。指定時は編集モード
            aspect_ratio: アスペクト比

        Returns:
            生成結果（画像とテキストを含む場合あり）
        """
        from google.genai import types

        resolved_model = self.resolve_model(model)
        logger.info(f"Gemini で画像生成を開始します (model={resolved_model})")

        try:
            contents: list[object] = [prompt]
            if reference_image:
                contents.append(_load_image_part(reference_image))

            config_params: dict[str, object] = {"response_modalities": ["IMAGE", "TEXT"]}
            if aspect_ratio:
                config_params["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)

            client = self._get_genai_client(resolved_model)
            response = client.models.generate_content(
                model=resolved_model,
                contents=contents,
                config=types.GenerateContentConfig(**config_params),  # type: ignore[arg-type]
            )
        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(
                f"Gemini 画像生成に失敗しました: {e!s}",
                "GEMINI_GENERATION_ERROR",
            ) from e

        images = []
        text_parts = []

        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                if hasattr(part, "inline_data") and part.inline_data:
                    path = self._storage.save_image(
                        part.inline_data.data,
                        part.inline_data.mime_type,
                        "gemini",
                    )
                    images.append(
                        GeneratedImage(
                            file_path=path,
                            mime_type=part.inline_data.mime_type,
                            model=resolved_model,
                        )
                    )
                elif hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

        logger.info(f"Gemini で {len(images)} 枚の画像を生成しました")
        return GenerationResult(
            images=images,
            text="\n".join(text_parts) if text_parts else None,
            model=resolved_model,
        )


# 拡張子から MIME タイプへのマッピング（既定は image/jpeg）
_IMAGE_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


def _guess_image_mime_type(path_or_uri: str) -> str:
    """パス／URI の拡張子から画像 MIME タイプを推定する（不明時は image/jpeg）."""
    suffix = Path(path_or_uri).suffix.lower()
    return _IMAGE_MIME_BY_SUFFIX.get(suffix, "image/jpeg")


def _validate_local_path(path_str: str) -> Path:
    """ローカルパスを正規化し、ファイルの存在と種別を検証する.

    `Path.resolve()` で `..` やシンボリックリンクを展開した上で、
    対象が実在するファイルであることを確認する。

    Raises:
        GenerationError: ファイルが存在しない、またはファイルでない場合
    """
    resolved = Path(path_str).resolve()
    if not resolved.exists():
        raise GenerationError(
            f"ファイルが見つかりません: {path_str}",
            "FILE_NOT_FOUND",
        )
    if not resolved.is_file():
        raise GenerationError(
            f"ファイルではありません: {path_str}",
            "NOT_A_FILE",
        )
    return resolved


def _load_image_part(path_or_uri: str) -> Any:
    """パスまたは GCS URI から画像入力 Part を生成する.

    ローカルパスの場合は存在・種別を検証する。MIME タイプは拡張子から推定する。
    """
    from google.genai import types

    if path_or_uri.startswith("gs://"):
        return types.Part.from_uri(
            file_uri=path_or_uri, mime_type=_guess_image_mime_type(path_or_uri)
        )
    validated = _validate_local_path(path_or_uri)
    image_bytes = validated.read_bytes()
    return types.Part.from_bytes(
        data=image_bytes, mime_type=_guess_image_mime_type(str(validated))
    )

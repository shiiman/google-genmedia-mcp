"""Gemini Omni 動画生成サービスモジュール.

Gemini Omni（`gemini-omni-1.2-flash`）を Vertex Interactions API 経由で呼び出し、
テキスト・画像・動画入力からの動画生成（音声付き）、延長、アップスケールを提供する。

Omni は Veo の `generate_videos` API では呼べず、Interactions API（global エンドポイント専用、
同期呼び出し）を使うため、SDK ではなく認証済み REST セッションで直接呼び出す。
リクエスト／レスポンスの形式は公式 mcp-genmedia (Go) 実装の検証済み仕様に合わせている。
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

import requests

from ..core.client import GenMediaClient
from ..core.errors import GenerationError, UnsupportedAuthMethodError
from ..core.models import (
    OMNI_MAX_SAMPLE_COUNT,
    OMNI_TASK_EXTEND,
    OMNI_TASK_REFERENCE_TO_VIDEO,
    OMNI_TASK_UPSCALE,
    GeneratedVideo,
    GenerationResult,
    GenMediaConfig,
    OmniModelConstraints,
    get_omni_constraints,
)
from .gemini_image import _IMAGE_MIME_BY_SUFFIX, _validate_local_path
from .storage import StorageService

logger = logging.getLogger(__name__)

# Interactions API のリビジョン。Pre-GA のワイヤ形式の変化をこの定数に局所化する
INTERACTIONS_API_REVISION = "2026-05-20"
INTERACTIONS_ENDPOINT = "https://aiplatform.googleapis.com"

# ローカルファイルをインライン送信する際の上限（公式仕様: 20 MB）
MAX_INLINE_BYTES = 20 * 1024 * 1024
MAX_IMAGES = 10
MAX_VIDEOS = 3

_VIDEO_MIME_BY_SUFFIX = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".flv": "video/x-flv",
    ".wmv": "video/wmv",
    ".3gp": "video/3gpp",
}

# 失敗として扱う Interaction のステータス
_FAILED_STATUSES = {"failed", "cancelled", "incomplete", "budget_exceeded"}

# エラー本文の最大表示長（巨大なレスポンスでログ・ツール出力が溢れるのを防ぐ）
_MAX_ERROR_BODY_CHARS = 2000


class OmniService:
    """Gemini Omni 動画生成サービス."""

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
        return self._config.tools.generate_video_omni.resolve_model(model)

    def generate(
        self,
        prompt: str | None = None,
        task: str | None = None,
        model: str | None = None,
        images: list[str] | None = None,
        videos: list[str] | None = None,
        resolution: str | None = None,
        aspect_ratio: str | None = None,
        duration_seconds: int | None = None,
        sample_count: int = 1,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> GenerationResult:
        """Omni で動画を生成・編集する.

        Args:
            prompt: 生成・編集の指示。task=upscale では指定不可、それ以外は必須
            task: 明示タスク（extend / upscale / reference_to_video）。省略時は入力から自動判定
            model: モデル名またはエイリアス
            images: 入力画像（ローカルパス または GCS URI）
            videos: 入力動画（ローカルパス または GCS URI）
            resolution: 出力解像度（360p / 720p / 1080p / 4k）
            aspect_ratio: アスペクト比（16:9 / 9:16）
            duration_seconds: 動画の長さ（秒）
            sample_count: 生成本数（1〜3。複数本は API を逐次呼び出して生成する）
            temperature: サンプリング温度（0.0〜2.0）
            top_p: nucleus sampling（0.0〜1.0）

        Returns:
            生成結果（動画ファイルパスと、モデルのテキスト出力があれば text）
        """
        if not self._client.has_cloud_credentials:
            raise UnsupportedAuthMethodError(
                "generate_video_omni は Vertex AI または OAuth 認証方式で利用可能です",
                "AUTH_NOT_SUPPORTED",
                hint="config.yaml の auth.method を vertex_ai または oauth に設定してください",
            )

        resolved_model = self.resolve_model(model)
        constraints = get_omni_constraints(resolved_model)
        images = images or []
        videos = videos or []
        self._validate_params(
            resolved_model,
            constraints,
            prompt=prompt,
            task=task,
            image_count=len(images),
            video_count=len(videos),
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            sample_count=sample_count,
            temperature=temperature,
            top_p=top_p,
        )

        request = self._build_request(
            resolved_model,
            prompt=prompt,
            task=task,
            image_parts=[_media_part("image", ref) for ref in images],
            video_parts=[_media_part("video", ref) for ref in videos],
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            temperature=temperature,
            top_p=top_p,
        )
        logger.info(
            f"Omni で動画生成を開始します (model={resolved_model}, task={task or 'auto'}, "
            f"samples={sample_count})"
        )

        saved: list[GeneratedVideo] = []
        texts: list[str] = []
        for index in range(sample_count):
            try:
                response = self._create_interaction(request)
                video_bytes_list, text = _parse_response(response)
            except GenerationError as e:
                if sample_count == 1:
                    raise
                raise GenerationError(
                    f"Omni 動画生成のサンプル {index + 1}/{sample_count} が失敗しました: "
                    f"{e.user_message}",
                    e.debug_code,
                    e.hint,
                ) from e
            for video_bytes in video_bytes_list:
                path = self._storage.save_video_from_bytes(video_bytes, "omni")
                saved.append(
                    GeneratedVideo(
                        file_path=path,
                        model=resolved_model,
                        duration_seconds=float(duration_seconds) if duration_seconds else None,
                    )
                )
            if text:
                texts.append(text)

        logger.info(f"Omni で {len(saved)} 本の動画を生成しました")
        return GenerationResult(
            videos=saved,
            text="\n".join(texts) if texts else None,
            model=resolved_model,
        )

    @staticmethod
    def _validate_params(
        model_id: str,
        constraints: OmniModelConstraints | None,
        *,
        prompt: str | None,
        task: str | None,
        image_count: int,
        video_count: int,
        resolution: str | None,
        aspect_ratio: str | None,
        duration_seconds: int | None,
        sample_count: int,
        temperature: float | None,
        top_p: float | None,
    ) -> None:
        """Omni の入力契約（公式 Go 実装で実機検証済み）に基づいてパラメータを検証する."""
        has_prompt = bool(prompt and prompt.strip())

        if not 1 <= sample_count <= OMNI_MAX_SAMPLE_COUNT:
            raise GenerationError(
                f"sample_count は 1〜{OMNI_MAX_SAMPLE_COUNT} で指定してください: {sample_count}",
                "INVALID_PARAMETER",
            )
        if image_count > MAX_IMAGES:
            raise GenerationError(
                f"images は最大 {MAX_IMAGES} 枚までです: {image_count}", "INVALID_PARAMETER"
            )
        if video_count > MAX_VIDEOS:
            raise GenerationError(
                f"videos は最大 {MAX_VIDEOS} 本までです: {video_count}", "INVALID_PARAMETER"
            )
        if temperature is not None and not 0.0 <= temperature <= 2.0:
            raise GenerationError(
                f"temperature は 0.0〜2.0 で指定してください: {temperature}", "INVALID_PARAMETER"
            )
        if top_p is not None and not 0.0 <= top_p <= 1.0:
            raise GenerationError(
                f"top_p は 0.0〜1.0 で指定してください: {top_p}", "INVALID_PARAMETER"
            )

        if constraints is not None:
            if resolution is not None and resolution not in constraints.valid_resolutions:
                raise GenerationError(
                    f"モデル {model_id} では無効な解像度です: {resolution}",
                    "INVALID_PARAMETER",
                    hint=f"利用可能な解像度: {constraints.valid_resolutions}",
                )
            if aspect_ratio is not None and aspect_ratio not in constraints.valid_aspect_ratios:
                raise GenerationError(
                    f"モデル {model_id} では無効なアスペクト比です: {aspect_ratio}",
                    "INVALID_PARAMETER",
                    hint=f"利用可能なアスペクト比: {constraints.valid_aspect_ratios}",
                )
            if duration_seconds is not None and not (
                constraints.min_duration <= duration_seconds <= constraints.max_duration
            ):
                raise GenerationError(
                    f"モデル {model_id} では無効な動画長です: {duration_seconds}秒",
                    "INVALID_PARAMETER",
                    hint=f"利用可能な動画長: {constraints.min_duration}〜"
                    f"{constraints.max_duration} 秒",
                )
            if task is not None and task not in constraints.supported_tasks:
                raise GenerationError(
                    f"モデル {model_id} では task={task} は利用できません",
                    "INVALID_PARAMETER",
                    hint=f"利用可能な task: {constraints.supported_tasks}",
                )
        elif duration_seconds is not None and duration_seconds < 1:
            raise GenerationError(
                f"duration_seconds は 1 以上で指定してください: {duration_seconds}",
                "INVALID_PARAMETER",
            )

        if task is None:
            if not has_prompt:
                raise GenerationError("prompt を指定してください", "INVALID_PARAMETER")
            return

        known_tasks = (OMNI_TASK_EXTEND, OMNI_TASK_UPSCALE, OMNI_TASK_REFERENCE_TO_VIDEO)
        if task not in known_tasks:
            raise GenerationError(
                f"未対応の task です: {task}",
                "INVALID_PARAMETER",
                hint=f"利用可能な task: {list(known_tasks)}",
            )

        if task == OMNI_TASK_REFERENCE_TO_VIDEO:
            if not has_prompt:
                raise GenerationError(
                    "task=reference_to_video には prompt が必要です", "INVALID_PARAMETER"
                )
            if image_count < 1:
                raise GenerationError(
                    "task=reference_to_video には参照画像（images）が 1 枚以上必要です",
                    "INVALID_PARAMETER",
                )
            if video_count > 0:
                raise GenerationError(
                    "task=reference_to_video では videos は指定できません", "INVALID_PARAMETER"
                )
            return

        # extend / upscale: 入力動画 1 本のみ。出力の構図は入力に従うため比率・長さは指定不可
        if video_count != 1:
            raise GenerationError(
                f"task={task} には入力動画（videos）がちょうど 1 本必要です: {video_count} 本",
                "INVALID_PARAMETER",
            )
        if image_count > 0:
            raise GenerationError(
                f"task={task} では images は指定できません", "INVALID_PARAMETER"
            )
        if aspect_ratio is not None or duration_seconds is not None:
            raise GenerationError(
                f"task={task} では aspect_ratio / duration_seconds は指定できません",
                "INVALID_PARAMETER",
            )
        if task == OMNI_TASK_UPSCALE and has_prompt:
            raise GenerationError(
                "task=upscale は動画のみを入力とし、prompt は指定できません", "INVALID_PARAMETER"
            )

    @staticmethod
    def _build_request(
        model_id: str,
        *,
        prompt: str | None,
        task: str | None,
        image_parts: list[dict[str, Any]],
        video_parts: list[dict[str, Any]],
        resolution: str | None,
        aspect_ratio: str | None,
        duration_seconds: int | None,
        temperature: float | None,
        top_p: float | None,
    ) -> dict[str, Any]:
        """Interactions API のリクエストボディを構築する."""
        content: list[dict[str, Any]] = []
        if prompt and prompt.strip():
            content.append({"type": "text", "text": prompt})
        content.extend(image_parts)
        content.extend(video_parts)

        request: dict[str, Any] = {
            "model": model_id,
            # ワイヤ上は小文字である必要がある
            "response_modalities": ["text", "video"],
            "input": [{"type": "user_input", "content": content}],
            # 単発呼び出し。履歴を保存しない（previous_interaction_id も送らない）
            "store": False,
        }

        generation_config: dict[str, Any] = {}
        if temperature is not None:
            generation_config["temperature"] = temperature
        if top_p is not None:
            generation_config["top_p"] = top_p
        if task is not None:
            generation_config["video_config"] = {"task": task}
        if generation_config:
            request["generation_config"] = generation_config

        if resolution is not None or aspect_ratio is not None or duration_seconds is not None:
            response_format: dict[str, Any] = {"type": "video"}
            if resolution is not None:
                response_format["resolution"] = resolution
            if aspect_ratio is not None:
                response_format["aspect_ratio"] = aspect_ratio
            if duration_seconds is not None:
                response_format["duration"] = f"{duration_seconds}s"
            request["response_format"] = [response_format]

        return request

    def _interactions_url(self) -> str:
        """Interactions API のエンドポイント URL を返す（global 専用）."""
        project = self._config.auth.vertex_ai.project
        if not project:
            raise GenerationError(
                "Vertex AI のプロジェクト ID が設定されていません",
                "AUTH_NO_PROJECT",
                hint="config.yaml の auth.vertexAi.project を設定してください",
            )
        return f"{INTERACTIONS_ENDPOINT}/v1beta1/projects/{project}/locations/global/interactions"

    def _create_interaction(self, request: dict[str, Any]) -> dict[str, Any]:
        """Interactions API を同期呼び出しし、レスポンスの JSON を返す."""
        url = self._interactions_url()
        headers = {
            "Content-Type": "application/json",
            "x-goog-user-project": self._config.auth.vertex_ai.project,
            "Api-Revision": INTERACTIONS_API_REVISION,
        }
        timeout = self._config.tools.generate_video_omni.request_timeout

        # 認証エラー（AuthError）はそのまま上位へ伝える
        session = self._client.authorized_session
        try:
            http_response = session.post(url, json=request, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout as e:
            raise GenerationError(
                f"Omni 動画生成がタイムアウトしました ({timeout} 秒)",
                "OMNI_TIMEOUT",
                hint="config.yaml の tools.generateVideoOmni.requestTimeout を増やしてください",
            ) from e
        except Exception as e:
            raise GenerationError(
                f"Omni 動画生成の API 呼び出しに失敗しました: {e!s}",
                "OMNI_REQUEST_ERROR",
            ) from e

        if http_response.status_code >= 400:
            body = http_response.text[:_MAX_ERROR_BODY_CHARS]
            hint = ""
            if http_response.status_code in (403, 404):
                hint = (
                    "Omni は global エンドポイント専用で、プロジェクトでの利用許可が必要です。"
                    "auth.vertexAi.project と API の有効化・権限を確認してください"
                )
            raise GenerationError(
                f"Omni API がエラーを返しました (status {http_response.status_code}): {body}",
                "OMNI_API_ERROR",
                hint=hint,
            )

        try:
            data = http_response.json()
        except ValueError as e:
            raise GenerationError(
                "Omni API のレスポンスを JSON として解析できませんでした", "OMNI_INVALID_RESPONSE"
            ) from e
        if not isinstance(data, dict):
            raise GenerationError(
                "Omni API のレスポンス形式が不正です", "OMNI_INVALID_RESPONSE"
            )
        return data


def _failure_detail(response: dict[str, Any]) -> str:
    """レスポンスの error / errors からメッセージを組み立てる."""
    entries: list[Any] = []
    if isinstance(response.get("error"), dict):
        entries.append(response["error"])
    errors = response.get("errors")
    if isinstance(errors, list):
        entries.extend(errors)

    parts = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("message"):
            continue
        message = str(entry["message"])
        if entry.get("code"):
            message += f" (code: {entry['code']})"
        parts.append(message)
    return "; ".join(parts)


def _parse_response(response: dict[str, Any]) -> tuple[list[bytes], str]:
    """Interaction レスポンスから動画バイナリとテキストを取り出す.

    結果は steps[]（Omni）または outputs[]（フォールバック）に入り、
    ネストした content[] 形式とフラットな形式の両方を許容する。

    Raises:
        GenerationError: 失敗ステータス、エラー付き、または動画が含まれない場合
    """
    status = str(response.get("status") or "")
    detail = _failure_detail(response)
    singular_error = (
        isinstance(response.get("error"), dict) and bool(response["error"].get("message"))
    )
    not_completed = bool(status) and status != "completed"

    # 単一の error は常に致命的。errors[] は完了済みなら診断情報のみ
    if detail and (singular_error or not_completed):
        if not_completed:
            detail += f" (interaction status: {status})"
        raise GenerationError(f"Omni API がエラーを返しました: {detail}", "OMNI_API_ERROR")
    if status in _FAILED_STATUSES:
        raise GenerationError(
            f"Omni の生成がステータス {status!r} で終了しました（詳細なし）", "OMNI_API_ERROR"
        )

    steps = response.get("steps") or response.get("outputs") or []
    videos: list[bytes] = []
    text_parts: list[str] = []

    def _consume(item: dict[str, Any]) -> None:
        item_type = item.get("type")
        mime = str(item.get("mime_type") or "")
        if item_type == "text" or item.get("text"):
            if item.get("text"):
                text_parts.append(str(item["text"]))
        elif mime.startswith("video/") or item_type == "video":
            try:
                videos.append(base64.b64decode(item.get("data") or "", validate=True))
            except ValueError as e:
                raise GenerationError(
                    "Omni のレスポンスの動画データ（base64）を解析できませんでした",
                    "OMNI_INVALID_RESPONSE",
                ) from e

    for step in steps:
        if not isinstance(step, dict) or step.get("type") == "thought":
            continue
        nested = step.get("content")
        if isinstance(nested, list) and nested:
            for part in nested:
                if isinstance(part, dict):
                    _consume(part)
        else:
            _consume(step)

    videos = [v for v in videos if v]
    if not videos:
        raise GenerationError(
            f"Omni のレスポンスに動画が含まれていませんでした (status={status!r})",
            "OMNI_NO_VIDEO",
            hint=detail or "プロンプトが安全フィルタ等で拒否された可能性があります",
        )
    return videos, "".join(text_parts)


def _media_part(kind: str, ref: str) -> dict[str, Any]:
    """画像/動画の参照（ローカルパス or GCS URI）から入力 Part を生成する.

    Args:
        kind: "image" または "video"
        ref: ローカルファイルパス（20 MB まで）または gs:// URI
    """
    mime_map = _IMAGE_MIME_BY_SUFFIX if kind == "image" else _VIDEO_MIME_BY_SUFFIX
    default_mime = "image/jpeg" if kind == "image" else "video/mp4"

    if ref.startswith("gs://"):
        suffix = Path(ref).suffix.lower()
        return {"type": kind, "mime_type": mime_map.get(suffix, default_mime), "uri": ref}

    validated = _validate_local_path(ref)
    size = validated.stat().st_size
    if size > MAX_INLINE_BYTES:
        raise GenerationError(
            f"ファイルが大きすぎます（{size / 1024 / 1024:.1f} MB）: {ref}",
            "FILE_TOO_LARGE",
            hint="ローカルファイルは 20 MB までです。大きいファイルは GCS にアップロードして "
            "gs:// URI で指定してください",
        )
    mime = mime_map.get(validated.suffix.lower(), default_mime)
    return {
        "type": kind,
        "mime_type": mime,
        "data": base64.b64encode(validated.read_bytes()).decode("ascii"),
    }

"""データモデル定義モジュール.

config.yaml の設定モデルと生成結果モデルを提供する。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VertexAiConfig(BaseModel):
    """Vertex AI 認証設定."""

    model_config = ConfigDict(populate_by_name=True)

    project: str = ""
    location: str = "us-central1"


class OAuthConfig(BaseModel):
    """OAuth 認証設定."""

    model_config = ConfigDict(populate_by_name=True)

    client_id: str = Field(default="", alias="clientId")
    client_secret: str = Field(default="", alias="clientSecret")


class AuthConfig(BaseModel):
    """認証設定."""

    model_config = ConfigDict(populate_by_name=True)

    method: str = "vertex_ai"  # "api_key" | "vertex_ai" | "oauth"
    api_key: str = Field(default="", alias="apiKey")
    vertex_ai: VertexAiConfig = Field(default_factory=VertexAiConfig, alias="vertexAi")
    oauth: OAuthConfig = Field(default_factory=OAuthConfig)


class OutputConfig(BaseModel):
    """出力設定."""

    directory: str = ".google-genmedia-mcp/output"


class GcsConfig(BaseModel):
    """GCS 設定."""

    enabled: bool = False
    bucket: str = ""


class ServerConfig(BaseModel):
    """サーバー設定."""

    model_config = ConfigDict(populate_by_name=True)

    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = Field(default="INFO", alias="logLevel")


class PromptConfig(BaseModel):
    """プロンプト設定."""

    prefix: str = ""
    separator: str = "\n"


class ModelEntry(BaseModel):
    """モデルエントリー（ID とエイリアス）."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    aliases: list[str] = []
    global_: bool = Field(default=False, alias="global")


class ChirpVoice(BaseModel):
    """Chirp TTS ボイス定義."""

    name: str
    gender: str


class VeoPollingConfig(BaseModel):
    """Veo ポーリング設定."""

    model_config = ConfigDict(populate_by_name=True)

    poll_interval: int = Field(default=15, alias="pollInterval")
    poll_timeout: int = Field(default=600, alias="pollTimeout")


class VeoModelConstraints(BaseModel):
    """Veo モデル固有の制約."""

    valid_durations: list[int]
    max_videos: int
    valid_aspect_ratios: list[str]
    supports_audio: bool


VEO_MODEL_CONSTRAINTS: dict[str, VeoModelConstraints] = {
    "veo-2.0": VeoModelConstraints(
        valid_durations=[5, 6, 7, 8],
        max_videos=4,
        valid_aspect_ratios=["16:9", "9:16"],
        supports_audio=False,
    ),
    "veo-3.0": VeoModelConstraints(
        valid_durations=[4, 6, 8],
        max_videos=2,
        valid_aspect_ratios=["16:9"],
        supports_audio=True,
    ),
    "veo-3.1": VeoModelConstraints(
        valid_durations=[4, 6, 8],
        max_videos=2,
        valid_aspect_ratios=["16:9", "9:16"],
        supports_audio=True,
    ),
}


def get_veo_constraints(model_id: str) -> VeoModelConstraints | None:
    """モデル ID からプレフィックスベースで Veo 制約を取得する.

    長いプレフィックスから順にマッチさせることで、
    "veo-3.1" が "veo-3.0" より優先的にマッチする。
    """
    for prefix in sorted(VEO_MODEL_CONSTRAINTS, key=len, reverse=True):
        if model_id.startswith(prefix):
            return VEO_MODEL_CONSTRAINTS[prefix]
    return None


# ===== モデル解決ユーティリティ =====


def _resolve_model(
    model: str | None,
    default_model: str,
    models: list[ModelEntry],
    allow_unregistered: bool,
    category_name: str,
) -> str:
    """モデル名またはエイリアスを正式モデル ID に解決する.

    Args:
        model: モデル名またはエイリアス（None の場合は default_model を使用）
        default_model: デフォルトモデル名（ID またはエイリアス）
        models: 利用可能なモデル一覧
        allow_unregistered: 未登録モデルを許可するか
        category_name: エラーメッセージ用のカテゴリ名

    Returns:
        解決されたモデル ID

    Raises:
        ModelNotFoundError: モデルが見つからない場合
    """
    # 循環 import 回避のため遅延 import（errors.py → models.py の依存を避ける）
    from .errors import ModelNotFoundError

    target = model if model is not None else default_model

    for entry in models:
        if entry.id == target or target in entry.aliases:
            return entry.id

    if allow_unregistered:
        return target

    raise ModelNotFoundError(
        f"{category_name}が見つかりません: {target}",
        "MODEL_NOT_FOUND",
        hint=f"利用可能なモデル: {[e.id for e in models]}"
        + (f" (デフォルト: {default_model})" if default_model else ""),
    )


# ===== デフォルトモデル定義 =====


def _default_image_models() -> list[ModelEntry]:
    """画像モデルのデフォルト定義（Imagen + Gemini）."""
    return [
        ModelEntry(
            id="imagen-4.0-ultra-generate-001",
            aliases=["Imagen 4 Ultra", "imagen-4.0-ultra"],
        ),
        ModelEntry(
            id="imagen-4.0-generate-001",
            aliases=["Imagen 4", "imagen-4.0"],
        ),
        ModelEntry(
            id="imagen-4.0-fast-generate-001",
            aliases=["Imagen 4 Fast", "imagen-4.0-fast"],
        ),
        ModelEntry(
            id="gemini-3.1-flash-image-preview",
            aliases=["Nano Banana 2", "gemini-3.1-flash-image"],
            global_=True,  # type: ignore[call-arg]
        ),
        ModelEntry(
            id="gemini-3-pro-image-preview",
            aliases=["Nano Banana Pro", "gemini-3-pro-image"],
            global_=True,  # type: ignore[call-arg]
        ),
        ModelEntry(
            id="gemini-2.5-flash-image",
            aliases=["Nano Banana", "gemini-2.5-flash-preview-image-generation"],
        ),
    ]


def _default_veo_models() -> list[ModelEntry]:
    """Veo モデルのデフォルト定義."""
    return [
        ModelEntry(
            id="veo-3.1-generate-preview",
            aliases=["Veo 3.1", "veo-3.1", "veo-3.1-generate-001"],
        ),
        ModelEntry(
            id="veo-3.1-fast-generate-preview",
            aliases=["Veo 3.1 Fast", "veo-3.1-fast", "veo-3.1-fast-generate-001"],
        ),
        ModelEntry(
            id="veo-3.0-generate-preview",
            aliases=["Veo 3", "veo-3.0"],
        ),
        ModelEntry(
            id="veo-3.0-generate-001",
            aliases=["veo-3.0-generate"],
        ),
        ModelEntry(
            id="veo-3.0-fast-generate-preview",
            aliases=["Veo 3 Fast", "veo-3.0-fast"],
        ),
        ModelEntry(
            id="veo-3.0-fast-generate-001",
            aliases=["veo-3.0-fast-generate"],
        ),
        ModelEntry(
            id="veo-2.0-generate-001",
            aliases=["Veo 2", "veo-2.0"],
        ),
        ModelEntry(
            id="veo-2.0-generate-exp",
            aliases=["Veo 2 Exp", "veo-2.0-exp"],
        ),
        ModelEntry(
            id="veo-2.0-generate-preview",
            aliases=["Veo 2 Preview", "veo-2.0-preview"],
        ),
    ]


def _default_lyria_models() -> list[ModelEntry]:
    """Lyria モデルのデフォルト定義."""
    return [
        ModelEntry(
            id="lyria-002",
            aliases=["Lyria 2", "lyria2"],
        ),
    ]


def _default_chirp_voices() -> list[ChirpVoice]:
    """Chirp TTS ボイスのデフォルト定義."""
    return [
        ChirpVoice(name="Aoede", gender="female"),
        ChirpVoice(name="Kore", gender="female"),
        ChirpVoice(name="Leda", gender="female"),
        ChirpVoice(name="Zephyr", gender="female"),
        ChirpVoice(name="Puck", gender="male"),
        ChirpVoice(name="Charon", gender="male"),
        ChirpVoice(name="Fenrir", gender="male"),
        ChirpVoice(name="Orus", gender="male"),
    ]


# ===== ツール別設定 =====


class GenerateImageToolConfig(BaseModel):
    """generate_image ツール設定."""

    model_config = ConfigDict(populate_by_name=True)

    aspect_ratio: str = Field(default="16:9", alias="aspectRatio")
    number_of_images: int = Field(default=1, alias="numberOfImages")
    output_mime_type: str = Field(default="image/png", alias="outputMimeType")
    default_model: str = Field(default="Nano Banana 2", alias="defaultModel")
    models: list[ModelEntry] = Field(default_factory=_default_image_models)
    allow_unregistered: bool = Field(default=True, alias="allowUnregistered")

    def resolve_model(self, model: str | None, category_name: str = "画像モデル") -> str:
        """モデル名またはエイリアスを正式モデル ID に解決する."""
        return _resolve_model(
            model, self.default_model, self.models,
            self.allow_unregistered, category_name,
        )

    def is_global_model(self, model_id: str) -> bool:
        """解決済みモデル ID がグローバルエンドポイントを使うか判定する."""
        for entry in self.models:
            if entry.id == model_id:
                return entry.global_
        return False


def _default_imagen_edit_models() -> list[ModelEntry]:
    """画像編集用 Imagen モデルのデフォルト定義."""
    return [
        ModelEntry(
            id="imagen-4.0-ultra-generate-001",
            aliases=["Imagen 4 Ultra", "imagen-4.0-ultra"],
        ),
        ModelEntry(
            id="imagen-4.0-generate-001",
            aliases=["Imagen 4", "imagen-4.0"],
        ),
        ModelEntry(
            id="imagen-4.0-fast-generate-001",
            aliases=["Imagen 4 Fast", "imagen-4.0-fast"],
        ),
    ]


class EditImageToolConfig(BaseModel):
    """edit_image ツール設定."""

    model_config = ConfigDict(populate_by_name=True)

    edit_mode: str = Field(default="inpaint_insertion", alias="editMode")
    number_of_images: int = Field(default=1, alias="numberOfImages")
    default_model: str = Field(default="Imagen 4", alias="defaultModel")
    models: list[ModelEntry] = Field(default_factory=_default_imagen_edit_models)
    allow_unregistered: bool = Field(default=False, alias="allowUnregistered")

    def resolve_model(self, model: str | None, category_name: str = "画像編集モデル") -> str:
        """モデル名またはエイリアスを正式モデル ID に解決する."""
        return _resolve_model(
            model, self.default_model, self.models,
            self.allow_unregistered, category_name,
        )


class GenerateVideoToolConfig(BaseModel):
    """generate_video ツール設定."""

    model_config = ConfigDict(populate_by_name=True)

    aspect_ratio: str = Field(default="16:9", alias="aspectRatio")
    duration_seconds: int = Field(default=8, alias="durationSeconds")
    number_of_videos: int = Field(default=1, alias="numberOfVideos")
    generate_audio: bool | None = Field(default=None, alias="generateAudio")
    default_model: str = Field(default="Veo 3.1", alias="defaultModel")
    models: list[ModelEntry] = Field(default_factory=_default_veo_models)
    polling: VeoPollingConfig = Field(default_factory=VeoPollingConfig)

    def resolve_model(self, model: str | None, category_name: str = "Veo モデル") -> str:
        """モデル名またはエイリアスを正式モデル ID に解決する."""
        return _resolve_model(
            model, self.default_model, self.models,
            False, category_name,
        )


class GenerateVideoFromImageToolConfig(BaseModel):
    """generate_video_from_image ツール設定."""

    model_config = ConfigDict(populate_by_name=True)

    aspect_ratio: str = Field(default="16:9", alias="aspectRatio")
    duration_seconds: int = Field(default=8, alias="durationSeconds")
    generate_audio: bool | None = Field(default=None, alias="generateAudio")
    default_model: str = Field(default="Veo 3.1", alias="defaultModel")
    models: list[ModelEntry] = Field(default_factory=_default_veo_models)
    polling: VeoPollingConfig = Field(default_factory=VeoPollingConfig)

    def resolve_model(self, model: str | None, category_name: str = "Veo モデル") -> str:
        """モデル名またはエイリアスを正式モデル ID に解決する."""
        return _resolve_model(
            model, self.default_model, self.models,
            False, category_name,
        )


class GenerateSpeechToolConfig(BaseModel):
    """generate_speech ツール設定（Chirp TTS ボイス設定含む）."""

    model_config = ConfigDict(populate_by_name=True)

    voice: str | None = None  # None = defaultVoice にフォールバック
    language: str | None = None  # None = defaultLanguage にフォールバック
    audio_encoding: str = Field(default="mp3", alias="audioEncoding")
    default_voice: str = Field(default="Kore", alias="defaultVoice")
    default_language: str = Field(default="ja-JP", alias="defaultLanguage")
    voices: list[ChirpVoice] = Field(default_factory=_default_chirp_voices)


class GenerateMusicToolConfig(BaseModel):
    """generate_music ツール設定."""

    model_config = ConfigDict(populate_by_name=True)

    default_model: str = Field(default="Lyria 2", alias="defaultModel")
    models: list[ModelEntry] = Field(default_factory=_default_lyria_models)

    def resolve_model(self, model: str | None, category_name: str = "Lyria モデル") -> str:
        """モデル名またはエイリアスを正式モデル ID に解決する."""
        return _resolve_model(
            model, self.default_model, self.models,
            False, category_name,
        )


class ToolsConfig(BaseModel):
    """ツール別設定."""

    model_config = ConfigDict(populate_by_name=True)

    generate_image: GenerateImageToolConfig = Field(
        default_factory=GenerateImageToolConfig, alias="generateImage"
    )
    edit_image: EditImageToolConfig = Field(
        default_factory=EditImageToolConfig, alias="editImage"
    )
    generate_video: GenerateVideoToolConfig = Field(
        default_factory=GenerateVideoToolConfig, alias="generateVideo"
    )
    generate_video_from_image: GenerateVideoFromImageToolConfig = Field(
        default_factory=GenerateVideoFromImageToolConfig,
        alias="generateVideoFromImage",
    )
    generate_speech: GenerateSpeechToolConfig = Field(
        default_factory=GenerateSpeechToolConfig, alias="generateSpeech"
    )
    generate_music: GenerateMusicToolConfig = Field(
        default_factory=GenerateMusicToolConfig, alias="generateMusic"
    )


class GenMediaConfig(BaseModel):
    """google-genmedia-mcp 全体設定."""

    model_config = ConfigDict(populate_by_name=True)

    auth: AuthConfig = Field(default_factory=AuthConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    gcs: GcsConfig = Field(default_factory=GcsConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    prompt: PromptConfig = Field(default_factory=PromptConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)


# ===== 生成結果モデル =====


class GeneratedImage(BaseModel):
    """生成済み画像."""

    file_path: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    model: str


class GeneratedVideo(BaseModel):
    """生成済み動画."""

    file_path: str
    model: str
    duration_seconds: float | None = None


class GeneratedAudio(BaseModel):
    """生成済み音声."""

    file_path: str
    audio_encoding: str  # mp3 / ogg_opus / pcm / wav
    model: str
    duration_seconds: float | None = None


class GenerationResult(BaseModel):
    """生成結果コンテナ."""

    images: list[GeneratedImage] = []
    videos: list[GeneratedVideo] = []
    audios: list[GeneratedAudio] = []
    text: str | None = None
    model: str = ""

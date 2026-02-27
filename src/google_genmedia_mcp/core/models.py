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


class ModelEntry(BaseModel):
    """モデルエントリー（ID とエイリアス）."""

    id: str
    aliases: list[str] = []


class ModelCategory(BaseModel):
    """モデルカテゴリー（デフォルト + 利用可能モデル一覧）."""

    model_config = ConfigDict(populate_by_name=True)

    default: str
    available: list[ModelEntry] = []
    allow_unregistered: bool = Field(default=False, alias="allowUnregistered")

    def resolve(self, model: str | None, category_name: str = "モデル") -> str:
        """モデル名またはエイリアスを正式モデル ID に解決する.

        Args:
            model: モデル名またはエイリアス（None の場合はデフォルトを使用）
            category_name: エラーメッセージ用のカテゴリ名

        Returns:
            解決されたモデル ID

        Raises:
            ModelNotFoundError: モデルが見つからない場合
        """
        from .errors import ModelNotFoundError

        if model is None:
            return self.default

        # デフォルトモデルは常に許可
        if model == self.default:
            return self.default

        for entry in self.available:
            if entry.id == model or model in entry.aliases:
                return entry.id

        if self.allow_unregistered:
            return model

        raise ModelNotFoundError(
            f"{category_name}が見つかりません: {model}",
            "MODEL_NOT_FOUND",
            hint=f"利用可能なモデル: {[e.id for e in self.available]}"
            + (f" (デフォルト: {self.default})" if self.default else ""),
        )


class ModelsConfig(BaseModel):
    """モデル設定."""

    imagen: ModelCategory = Field(
        default_factory=lambda: ModelCategory(
            default="imagen-4.0-fast-generate-001",
            available=[
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
            ],
        )
    )
    gemini: ModelCategory = Field(
        default_factory=lambda: ModelCategory(
            default="gemini-3.1-flash-image-preview",
            allowUnregistered=True,
            available=[
                ModelEntry(
                    id="gemini-3.1-flash-image-preview",
                    aliases=["Nano Banana 2", "gemini-3.1-flash-image"],
                ),
                ModelEntry(
                    id="gemini-3-pro-image-preview",
                    aliases=["Nano Banana Pro", "gemini-3-pro-image"],
                ),
                ModelEntry(
                    id="gemini-2.5-flash-image",
                    aliases=["Nano Banana", "gemini-2.5-flash-preview-image-generation"],
                ),
            ],
        )
    )
    veo: ModelCategory = Field(
        default_factory=lambda: ModelCategory(
            default="veo-3.1-generate-preview",
            available=[
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
                    aliases=["Veo 3", "veo-3.0", "veo-3.0-generate-001"],
                ),
                ModelEntry(
                    id="veo-3.0-fast-generate-preview",
                    aliases=["Veo 3 Fast", "veo-3.0-fast", "veo-3.0-fast-generate-001"],
                ),
                ModelEntry(
                    id="veo-2.0-generate-001",
                    aliases=["Veo 2", "veo-2.0"],
                ),
            ],
        )
    )
    lyria: ModelCategory = Field(
        default_factory=lambda: ModelCategory(
            default="lyria-002",
            available=[
                ModelEntry(
                    id="lyria-002",
                    aliases=["Lyria 2", "lyria2"],
                ),
            ],
        )
    )


class ChirpVoice(BaseModel):
    """Chirp TTS ボイス定義."""

    name: str
    gender: str


class ChirpConfig(BaseModel):
    """Chirp TTS 設定."""

    model_config = ConfigDict(populate_by_name=True)

    default_voice: str = Field(default="Kore", alias="defaultVoice")
    default_language: str = Field(default="ja-JP", alias="defaultLanguage")
    voices: list[ChirpVoice] = Field(
        default_factory=lambda: [
            ChirpVoice(name="Aoede", gender="female"),
            ChirpVoice(name="Kore", gender="female"),
            ChirpVoice(name="Leda", gender="female"),
            ChirpVoice(name="Zephyr", gender="female"),
            ChirpVoice(name="Puck", gender="male"),
            ChirpVoice(name="Charon", gender="male"),
            ChirpVoice(name="Fenrir", gender="male"),
            ChirpVoice(name="Orus", gender="male"),
        ]
    )


class VeoPollingConfig(BaseModel):
    """Veo ポーリング設定."""

    model_config = ConfigDict(populate_by_name=True)

    poll_interval: int = Field(default=15, alias="pollInterval")
    poll_timeout: int = Field(default=600, alias="pollTimeout")


class GenMediaConfig(BaseModel):
    """google-genmedia-mcp 全体設定."""

    model_config = ConfigDict(populate_by_name=True)

    auth: AuthConfig = Field(default_factory=AuthConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    gcs: GcsConfig = Field(default_factory=GcsConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    chirp: ChirpConfig = Field(default_factory=ChirpConfig)
    veo: VeoPollingConfig = Field(default_factory=VeoPollingConfig)


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

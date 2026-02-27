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

    method: str = "api_key"  # "api_key" | "vertex_ai" | "oauth"
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

        for entry in self.available:
            if entry.id == model or model in entry.aliases:
                return entry.id

        if self.allow_unregistered:
            return model

        raise ModelNotFoundError(
            f"{category_name}が見つかりません: {model}",
            "MODEL_NOT_FOUND",
            hint=f"利用可能なモデル: {[e.id for e in self.available]}",
        )


class ModelsConfig(BaseModel):
    """モデル設定."""

    imagen: ModelCategory = Field(
        default_factory=lambda: ModelCategory(default="imagen-4.0-fast-generate-001")
    )
    gemini: ModelCategory = Field(
        default_factory=lambda: ModelCategory(
            default="gemini-3.1-flash-image-preview"
        )
    )
    veo: ModelCategory = Field(
        default_factory=lambda: ModelCategory(default="veo-3.1-generate-preview")
    )
    lyria: ModelCategory = Field(
        default_factory=lambda: ModelCategory(default="lyria-002")
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
    voices: list[ChirpVoice] = []


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

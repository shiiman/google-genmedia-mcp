"""GenMediaService ファサードモジュール.

全サービスの遅延初期化を担うファサードクラス。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..core.client import GenMediaClient
from ..core.models import GenMediaConfig
from ..utils.config import get_config

if TYPE_CHECKING:
    from .avtool import AvToolService
    from .chirp import ChirpService
    from .gemini_image import GeminiImageService
    from .imagen import ImagenService
    from .imagen_edit import ImagenEditService
    from .lyria import LyriaService
    from .storage import StorageService
    from .veo import VeoService

logger = logging.getLogger(__name__)


class GenMediaService:
    """全サービスへのアクセスを提供するファサードクラス."""

    def __init__(self, config: GenMediaConfig | None = None) -> None:
        self._config = config or get_config()
        self._client: GenMediaClient | None = None
        self._storage_instance: StorageService | None = None
        self._imagen_instance: ImagenService | None = None
        self._imagen_edit_instance: ImagenEditService | None = None
        self._gemini_image_instance: GeminiImageService | None = None
        self._veo_instance: VeoService | None = None
        self._chirp_instance: ChirpService | None = None
        self._lyria_instance: LyriaService | None = None
        self._avtool_instance: AvToolService | None = None

    @property
    def client(self) -> GenMediaClient:
        """SDK クライアントを返す（遅延初期化）."""
        if self._client is None:
            self._client = GenMediaClient(self._config)
        return self._client

    @property
    def storage(self) -> StorageService:
        """ストレージサービスを返す（遅延初期化）."""
        if self._storage_instance is None:
            from .storage import StorageService
            self._storage_instance = StorageService(self._config)
        return self._storage_instance

    @property
    def imagen(self) -> ImagenService:
        """Imagen サービスを返す（遅延初期化）."""
        if self._imagen_instance is None:
            from .imagen import ImagenService
            self._imagen_instance = ImagenService(self.client, self._config, self.storage)
        return self._imagen_instance

    @property
    def imagen_edit(self) -> ImagenEditService:
        """Imagen 編集サービスを返す（遅延初期化）."""
        if self._imagen_edit_instance is None:
            from .imagen_edit import ImagenEditService
            self._imagen_edit_instance = ImagenEditService(self.client, self._config, self.storage)
        return self._imagen_edit_instance

    @property
    def gemini_image(self) -> GeminiImageService:
        """Gemini Image サービスを返す（遅延初期化）."""
        if self._gemini_image_instance is None:
            from .gemini_image import GeminiImageService
            self._gemini_image_instance = GeminiImageService(
                self.client, self._config, self.storage
            )
        return self._gemini_image_instance

    @property
    def veo(self) -> VeoService:
        """Veo サービスを返す（遅延初期化）."""
        if self._veo_instance is None:
            from .veo import VeoService
            self._veo_instance = VeoService(self.client, self._config, self.storage)
        return self._veo_instance

    @property
    def chirp(self) -> ChirpService:
        """Chirp TTS サービスを返す（遅延初期化）."""
        if self._chirp_instance is None:
            from .chirp import ChirpService
            self._chirp_instance = ChirpService(self.client, self._config, self.storage)
        return self._chirp_instance

    @property
    def lyria(self) -> LyriaService:
        """Lyria 音楽生成サービスを返す（遅延初期化）."""
        if self._lyria_instance is None:
            from .lyria import LyriaService
            self._lyria_instance = LyriaService(self.client, self._config, self.storage)
        return self._lyria_instance

    @property
    def avtool(self) -> AvToolService:
        """AV ツールサービスを返す（遅延初期化）."""
        if self._avtool_instance is None:
            from .avtool import AvToolService
            self._avtool_instance = AvToolService(self._config)
        return self._avtool_instance

    @property
    def has_cloud_credentials(self) -> bool:
        """Vertex AI または OAuth 認証方式かどうか."""
        return self.client.has_cloud_credentials

    @property
    def config(self) -> GenMediaConfig:
        """設定を返す."""
        return self._config

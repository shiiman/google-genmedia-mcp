# モデル更新・Imagen 廃止・edit_image 統合 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Veo モデルを GA 化・lite 追加し、Imagen を完全削除、画像編集を generate_image の reference_image（Gemini）へ統合する。

**Architecture:** モデル定義（`core/models.py`）を更新し、Imagen 専用サービス（`imagen.py` / `imagen_edit.py`）と `edit_image` ツールを削除。`GeminiImageService` をローカル画像入力対応に拡張し、`generate_image` だけで生成と参照画像編集を兼ねる。設定・ドキュメント・テストを同期する。

**Tech Stack:** Python, FastMCP, Pydantic, google-genai SDK, pytest, ruff, mypy, uv

設計: [docs/superpowers/specs/2026-05-29-model-update-imagen-removal-design.md](../specs/2026-05-29-model-update-imagen-removal-design.md)

---

## 前提

- 作業ディレクトリ: リポジトリルート
- テスト実行: `uv run pytest`
- lint: `uv run ruff check src/ tests/`
- 型: `uv run mypy src/`
- 各タスク完了時にコミットする（Conventional Commits、日本語、`--no-verify` 禁止）

---

## Task 1: Veo モデル定義を GA 化・lite 追加・廃止削除

**Files:**
- Modify: `src/google_genmedia_mcp/core/models.py`（`_default_veo_models`）
- Test: `tests/test_models.py`

- [ ] **Step 1: テストを更新（失敗させる）**

`tests/test_models.py` の `TestResolveModel.test_veo_resolve_none` を以下に変更:

```python
    def test_veo_resolve_none(self) -> None:
        """Veo の model=None でデフォルト（GA ID）が返ることを検証."""
        config = GenMediaConfig()
        assert config.tools.generate_video.resolve_model(None) == "veo-3.1-generate-001"
```

同ファイルに新規テストを追加（`TestResolveModel` クラス内）:

```python
    def test_veo_lite_resolve(self) -> None:
        """veo-3.1-lite エイリアスが GA ID に解決されることを検証."""
        config = GenMediaConfig()
        assert config.tools.generate_video.resolve_model("Veo 3.1 Lite") == "veo-3.1-lite-generate-001"
        assert config.tools.generate_video.resolve_model("veo-3.1-lite") == "veo-3.1-lite-generate-001"

    def test_veo_deprecated_preview_removed(self) -> None:
        """廃止 preview ID が解決不能（未登録扱い）になることを検証."""
        import pytest

        from google_genmedia_mcp.core.errors import ModelNotFoundError

        config = GenMediaConfig()
        with pytest.raises(ModelNotFoundError):
            config.tools.generate_video.resolve_model("veo-3.1-generate-preview")
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `uv run pytest tests/test_models.py::TestResolveModel::test_veo_resolve_none tests/test_models.py::TestResolveModel::test_veo_lite_resolve tests/test_models.py::TestResolveModel::test_veo_deprecated_preview_removed -v`
Expected: FAIL（現状は preview ID がデフォルト/エイリアス）

- [ ] **Step 3: `_default_veo_models()` を更新**

`src/google_genmedia_mcp/core/models.py` の `_default_veo_models()` を以下で置き換える:

```python
def _default_veo_models() -> list[ModelEntry]:
    """Veo モデルのデフォルト定義."""
    return [
        ModelEntry(
            id="veo-3.1-generate-001",
            aliases=["Veo 3.1", "veo-3.1"],
        ),
        ModelEntry(
            id="veo-3.1-fast-generate-001",
            aliases=["Veo 3.1 Fast", "veo-3.1-fast"],
        ),
        ModelEntry(
            id="veo-3.1-lite-generate-001",
            aliases=["Veo 3.1 Lite", "veo-3.1-lite"],
        ),
        ModelEntry(
            id="veo-3.0-generate-001",
            aliases=["Veo 3", "veo-3.0"],
        ),
        ModelEntry(
            id="veo-3.0-fast-generate-001",
            aliases=["Veo 3 Fast", "veo-3.0-fast"],
        ),
        ModelEntry(
            id="veo-2.0-generate-001",
            aliases=["Veo 2", "veo-2.0"],
        ),
    ]
```

- [ ] **Step 4: get_veo_constraints テストの ID を GA へ更新**

`tests/test_models.py` の `TestGetVeoConstraints` 内の preview ID を GA ID に置換（プレフィックスマッチ自体は不変だが現実に合わせる）:
- `get_veo_constraints("veo-3.0-generate-preview")` → `get_veo_constraints("veo-3.0-generate-001")`
- `get_veo_constraints("veo-3.1-generate-preview")` → `get_veo_constraints("veo-3.1-generate-001")`
- `get_veo_constraints("veo-3.1-fast-generate-preview")` → `get_veo_constraints("veo-3.1-fast-generate-001")`
- `get_veo_constraints("veo-3.0-fast-generate-preview")` → `get_veo_constraints("veo-3.0-fast-generate-001")`

新規テストを `TestGetVeoConstraints` に追加:

```python
    def test_veo_31_lite_model(self) -> None:
        """veo-3.1-lite が veo-3.1 制約に解決されることを検証."""
        c = get_veo_constraints("veo-3.1-lite-generate-001")
        assert c is not None
        assert c.valid_durations == [4, 6, 8]
        assert c.supports_audio is True
```

- [ ] **Step 5: テストが通ることを確認**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 6: コミット**

```bash
git add src/google_genmedia_mcp/core/models.py tests/test_models.py
git commit -m "feat(models): Veo を GA ID 化し veo-3.1-lite 追加・廃止 preview 削除"
```

---

## Task 2: GeminiImageService をローカル画像入力対応に拡張

**Files:**
- Modify: `src/google_genmedia_mcp/services/gemini_image.py`
- Test: `tests/test_services.py`

- [ ] **Step 1: テストを更新/追加（失敗させる）**

`tests/test_services.py` の `TestGeminiImageServiceGenerate` 内、`test_generate_invalid_gcs_uri_raises` を**削除**し、以下を追加:

```python
    def test_generate_with_gcs_reference(self) -> None:
        """GCS URI 参照画像で generate_content が呼ばれることを検証."""
        response = MagicMock()
        part = MagicMock()
        part.inline_data.data = b"img"
        part.inline_data.mime_type = "image/png"
        candidate = MagicMock()
        candidate.content.parts = [part]
        response.candidates = [candidate]
        self.client_mock.genai.models.generate_content.return_value = response
        self.storage_mock.save_image.return_value = "/tmp/gemini.png"

        result = self.service.generate(
            prompt="編集", model="gemini-2.5-flash-image",
            reference_image="gs://bucket/in.png",
        )
        assert len(result.images) == 1
        self.client_mock.genai.models.generate_content.assert_called_once()

    def test_generate_with_local_reference(self, tmp_path: "Path") -> None:
        """ローカル参照画像で generate_content が呼ばれることを検証."""
        img_file = tmp_path / "in.png"
        img_file.write_bytes(b"\x89PNG\r\n")
        response = MagicMock()
        part = MagicMock()
        part.inline_data.data = b"img"
        part.inline_data.mime_type = "image/png"
        candidate = MagicMock()
        candidate.content.parts = [part]
        response.candidates = [candidate]
        self.client_mock.genai.models.generate_content.return_value = response
        self.storage_mock.save_image.return_value = "/tmp/gemini.png"

        result = self.service.generate(
            prompt="編集", model="gemini-2.5-flash-image",
            reference_image=str(img_file),
        )
        assert len(result.images) == 1

    def test_generate_local_reference_not_found_raises(self) -> None:
        """存在しないローカル参照画像でエラーになることを検証."""
        import pytest

        from google_genmedia_mcp.core.errors import GenerationError

        with pytest.raises(GenerationError):
            self.service.generate(
                prompt="編集", model="gemini-2.5-flash-image",
                reference_image="/nonexistent/path.png",
            )
```

`tests/test_services.py` 冒頭の import に `from pathlib import Path` が無ければ追加（既存確認。`TestAvToolServiceCombine` で tmp_path を使用しているため恐らく既存）。

- [ ] **Step 2: テストが失敗することを確認**

Run: `uv run pytest tests/test_services.py -k GeminiImageServiceGenerate -v`
Expected: FAIL（`reference_image` 引数未対応 / ローカル未対応）

- [ ] **Step 3: gemini_image.py を実装**

`src/google_genmedia_mcp/services/gemini_image.py` を以下で置き換える:

```python
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


def _validate_local_path(path_str: str) -> Path:
    """ローカルパスを検証してパストラバーサルを防ぐ.

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

    ローカルパスの場合は検証を実施する。
    """
    from google.genai import types

    if path_or_uri.startswith("gs://"):
        return types.Part.from_uri(file_uri=path_or_uri, mime_type="image/jpeg")
    validated = _validate_local_path(path_or_uri)
    image_bytes = validated.read_bytes()
    suffix = validated.suffix.lower()
    mime_type = "image/png" if suffix == ".png" else "image/jpeg"
    return types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
```

- [ ] **Step 4: テストが通ることを確認**

Run: `uv run pytest tests/test_services.py -k GeminiImageServiceGenerate -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/google_genmedia_mcp/services/gemini_image.py tests/test_services.py
git commit -m "feat(gemini): 参照画像のローカルパス入力に対応し編集を統合"
```

> **依存メモ:** 本タスクで `generate()` の引数名を `reference_image_gcs_uri` → `reference_image` に変更する。`generate_image` ツール（`image.py`）は次の Task 3 で更新されるまで旧引数名で呼び出すが、`tests/test_tools.py` では `gemini_image` を MagicMock 化しているためテストは緑のまま。Task 3 を必ず本タスク直後に実施すること。

---

## Task 3: generate_image ツールを Gemini 専用化・パラメータ整理

**Files:**
- Modify: `src/google_genmedia_mcp/mcp/tools/image.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: テストを更新（失敗させる）**

`tests/test_tools.py` の `TestGenerateImageTool` から以下を**削除**:
- `test_imagen_explicit_model`（Imagen 分岐廃止）

`TestPromptPrefixIntegration.test_negative_prompt_not_affected` を**削除**（`negative_prompt` パラメータ廃止のため）。

`_make_imagen_result` 関数を**削除**（参照されなくなる）。

`TestGenerateImageTool` に以下を追加:

```python
    def test_local_reference_uses_gemini(self) -> None:
        """ローカル reference_image 指定時に Gemini に渡されることを検証."""
        service_mock = _make_service_mock()
        service_mock.gemini_image.generate.return_value = _make_gemini_result()

        with patch(
            "google_genmedia_mcp.mcp.tools.image.get_service",
            return_value=service_mock,
        ):
            from google_genmedia_mcp.mcp.tools.image import generate_image

            result = generate_image(prompt="編集して", reference_image="/tmp/in.png")

        call_args = service_mock.gemini_image.generate.call_args
        assert call_args.kwargs["reference_image"] == "/tmp/in.png"
        assert "images" in result
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `uv run pytest tests/test_tools.py::TestGenerateImageTool -v`
Expected: FAIL（`reference_image` が `gemini_image.generate` に渡されていない／署名不一致）

- [ ] **Step 3: image.py を実装**

`src/google_genmedia_mcp/mcp/tools/image.py` を以下で置き換える:

```python
"""画像生成 MCP ツールモジュール.

generate_image ツールを提供する（Gemini による生成・参照画像編集）。
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.errors import GenMediaError
from ..server import mcp
from ._utils import apply_prompt_prefix, get_service

logger = logging.getLogger(__name__)


@mcp.tool()
def generate_image(
    prompt: str,
    model: str | None = None,
    aspect_ratio: str | None = None,
    reference_image: str | None = None,
) -> dict[str, Any]:
    """テキストから画像を生成する（Gemini）。

    reference_image を指定すると、その画像を入力にした編集（参照画像編集）を行う。

    Args:
        prompt: 生成・編集の指示テキスト
        model: 使用するモデル名またはエイリアス（省略時は config の defaultModel: Nano Banana 2）
        aspect_ratio: アスペクト比 (1:1 / 16:9 / 9:16 / 4:3 / 3:4)。デフォルト: config 設定値 (16:9)
        reference_image: 参照画像（GCS URI: gs://bucket/file.png またはローカルパス）。
                         指定すると参照画像をもとに編集する

    Returns:
        生成結果（images リストと model 名を含む辞書）
    """
    try:
        prompt = apply_prompt_prefix(prompt)
        service = get_service()
        tool_cfg = service.config.tools.generate_image

        aspect_ratio = aspect_ratio if aspect_ratio is not None else tool_cfg.aspect_ratio
        resolved_model = tool_cfg.resolve_model(model)

        result = service.gemini_image.generate(
            prompt=prompt,
            model=resolved_model,
            reference_image=reference_image,
            aspect_ratio=aspect_ratio,
        )
        return result.model_dump()
    except GenMediaError as e:
        return {"error": e.user_message, "code": e.debug_code, "hint": e.hint}
    except Exception:
        logger.exception("generate_image で予期しないエラーが発生しました")
        return {"error": "内部エラーが発生しました", "code": "INTERNAL_ERROR"}
```

- [ ] **Step 4: テストが通ることを確認**

Run: `uv run pytest tests/test_tools.py::TestGenerateImageTool tests/test_tools.py::TestPromptPrefixIntegration -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/google_genmedia_mcp/mcp/tools/image.py tests/test_tools.py
git commit -m "refactor(image): generate_image を Gemini 専用化し未使用パラメータを削除"
```

---

## Task 4: edit_image ツールを削除し server_info / server を更新

**Files:**
- Delete: `src/google_genmedia_mcp/mcp/tools/image_edit.py`
- Modify: `src/google_genmedia_mcp/mcp/server.py`
- Modify: `src/google_genmedia_mcp/mcp/tools/server_info.py`

- [ ] **Step 1: edit_image ツールファイルを削除**

```bash
git rm src/google_genmedia_mcp/mcp/tools/image_edit.py
```

- [ ] **Step 2: server.py の登録から image_edit を削除**

`src/google_genmedia_mcp/mcp/server.py` の `_register_tools()` 内 import から `image_edit,  # noqa: F401` 行を削除する。
また、`mcp = FastMCP(...)` の `instructions` 文字列の "Imagen, " を削除し、`"Google の生成メディア API（Gemini Image, Veo, Chirp, Lyria）を "` とする。

- [ ] **Step 3: server_info.py から edit_image を除去**

`src/google_genmedia_mcp/mcp/tools/server_info.py` を以下のとおり修正:

`phase2_tools` リストから `"edit_image",` を削除:

```python
        phase2_tools = [
            "generate_speech",
            "generate_music",
            "combine_audio_video",
        ]
```

`tools_models` 辞書から `edit_image` 行を削除:

```python
        tools_models: dict[str, Any] = {
            "generate_image": _tool_models(config.tools.generate_image),
            "generate_video": _tool_models(config.tools.generate_video),
            "generate_video_from_image": _tool_models(config.tools.generate_video_from_image),
            "generate_music": _tool_models(config.tools.generate_music),
        }
```

- [ ] **Step 4: サーバー起動とツール一覧を確認**

Run: `uv run python -c "from google_genmedia_mcp.mcp.server import _register_tools; _register_tools(); print('ok')"`
Expected: `ok`（import エラーが出ないこと）

- [ ] **Step 5: コミット**

```bash
git add -A
git commit -m "feat(tools): edit_image ツールを削除し server_info を更新"
```

---

## Task 5: Imagen / ImagenEdit サービスとファサード参照を削除

**Files:**
- Delete: `src/google_genmedia_mcp/services/imagen.py`
- Delete: `src/google_genmedia_mcp/services/imagen_edit.py`
- Modify: `src/google_genmedia_mcp/services/service.py`
- Test: `tests/test_services.py`

- [ ] **Step 1: test_services.py から Imagen 関連を削除（失敗させる）**

`tests/test_services.py` で以下を実施:

(a) import 削除: `from google_genmedia_mcp.services.imagen import ImagenService`

(b) クラス全体を削除: `TestImagenServiceResolveModel`, `TestImagenServiceGenerate`

(c) 設定ヘルパー `_make_config()`（ファイル冒頭付近の YAML を返す関数）内の `tools:` の `generateImage` / `editImage` ブロックを以下で置き換える（imagen を排除し editImage を削除）:

```yaml
  generateImage:
    defaultModel: "Nano Banana"
    allowUnregistered: true
    models:
      - id: "gemini-2.5-flash-preview-image-generation"
        aliases: ["Nano Banana", "gemini-2.5-flash-image"]
```

（`editImage:` セクション全体を削除する。`generateVideo` 以降は変更しない。）

(d) `TestGeminiImageServiceResolveModel.test_resolve_none_returns_default` の期待値を更新（defaultModel が "Nano Banana" → id へ解決）:

```python
    def test_resolve_none_returns_default(self) -> None:
        """None で共有デフォルトモデルが返ることを検証."""
        assert self.service.resolve_model(None) == "gemini-2.5-flash-preview-image-generation"
```

（`test_resolve_by_alias` は `"Nano Banana"` → `"gemini-2.5-flash-preview-image-generation"` のままで通る。`test_allow_unregistered_model` / `test_disallow_unregistered_model` は変更不要。）

- [ ] **Step 2: テストが失敗することを確認**

Run: `uv run pytest tests/test_services.py -v`
Expected: FAIL（import エラー、または fixture 不整合）

- [ ] **Step 3: サービスファイルを削除**

```bash
git rm src/google_genmedia_mcp/services/imagen.py src/google_genmedia_mcp/services/imagen_edit.py
```

- [ ] **Step 4: service.py からプロパティ・参照を削除**

`src/google_genmedia_mcp/services/service.py` で以下を削除:
- TYPE_CHECKING import: `from .imagen import ImagenService` と `from .imagen_edit import ImagenEditService`
- `__init__` 内: `self._imagen_instance: ImagenService | None = None` と `self._imagen_edit_instance: ImagenEditService | None = None`
- `imagen` プロパティ（`@property def imagen` ブロック全体）
- `imagen_edit` プロパティ（`@property def imagen_edit` ブロック全体）

- [ ] **Step 5: テストが通ることを確認**

Run: `uv run pytest tests/test_services.py -v`
Expected: PASS

- [ ] **Step 6: コミット**

```bash
git add -A
git commit -m "refactor(services): Imagen / ImagenEdit サービスを削除"
```

---

## Task 6: models.py から EditImageToolConfig と Imagen 定義を削除

**Files:**
- Modify: `src/google_genmedia_mcp/core/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: テストを更新（失敗させる）**

`tests/test_models.py` で以下を修正:

`TestGenMediaConfig.test_model_defaults` から edit_image アサーションを削除:

```python
    def test_model_defaults(self) -> None:
        """各ツールのデフォルトモデルを検証."""
        config = GenMediaConfig()
        assert config.tools.generate_video.default_model == "Veo 3.1"
        assert config.tools.generate_video_from_image.default_model == "Veo 3.1"
        assert config.tools.generate_image.default_model == "Nano Banana 2"
```

`TestGenMediaConfig.test_model_list_defaults` を更新:

```python
    def test_model_list_defaults(self) -> None:
        """各ツールのモデル一覧件数を検証."""
        config = GenMediaConfig()
        assert len(config.tools.generate_image.models) == 3  # Gemini のみ
        assert len(config.tools.generate_video.models) == 6  # Veo
```

`TestResolveModel.test_edit_image_resolve` を**削除**。

`TestResolveModel.test_resolve_none_returns_default` は現状すでに `"gemini-3.1-flash-image-preview"` を期待しているため変更不要。

`TestResolveModel.test_resolve_by_alias` を以下に置き換える（Imagen エイリアスは削除済みのため Gemini エイリアスへ）:

```python
    def test_resolve_by_alias(self) -> None:
        """エイリアスからモデルを解決できることを検証."""
        config = GenMediaConfig()
        assert config.tools.generate_image.resolve_model("Nano Banana") == "gemini-2.5-flash-image"
        assert config.tools.generate_image.resolve_model("Nano Banana 2") == "gemini-3.1-flash-image-preview"
```

`TestResolveModel.test_resolve_by_id` を以下に置き換える（imagen ID → Gemini ID）:

```python
    def test_resolve_by_id(self) -> None:
        """モデル ID で直接解決できることを検証."""
        config = GenMediaConfig()
        assert config.tools.generate_image.resolve_model("gemini-2.5-flash-image") == "gemini-2.5-flash-image"
```

`TestToolsConfig.test_default_values` から edit_image アサーション（`edit_mode`, `number_of_images`）を削除。

`TestToolsConfig.test_models_in_each_tool` から `edit_image` 行を削除:

```python
    def test_models_in_each_tool(self) -> None:
        """各ツールがモデル一覧を持つことを検証."""
        config = GenMediaConfig()
        assert len(config.tools.generate_image.models) == 3  # Gemini のみ
        assert len(config.tools.generate_video.models) == 6
        assert len(config.tools.generate_music.models) == 3
```

`TestToolsConfig.test_yaml_alias_with_default_model` の `defaultModel: "Imagen 4 Fast"` を Gemini に変更し、対応する `models` と期待値を Gemini ID へ更新:

```python
    def test_yaml_alias_with_default_model(self) -> None:
        """defaultModel にエイリアスを指定できることを検証."""
        tc = ToolsConfig.model_validate({
            "generateImage": {
                "defaultModel": "Nano Banana",
                "models": [
                    {"id": "gemini-2.5-flash-image", "aliases": ["Nano Banana"]},
                ],
            }
        })
        assert tc.generate_image.default_model == "Nano Banana"
        assert tc.generate_image.resolve_model(None) == "gemini-2.5-flash-image"
```

`TestModelEntryGlobalFlag.test_is_global_model` の imagen 参照を Gemini に変更:

```python
    def test_is_global_model(self) -> None:
        """is_global_model がエントリの global フラグを返すことを検証."""
        config = GenMediaConfig()
        tool_cfg = config.tools.generate_image
        assert tool_cfg.is_global_model("gemini-3.1-flash-image-preview") is True
        assert tool_cfg.is_global_model("gemini-2.5-flash-image") is False
```

（`test_image_result` / `test_model_dump` 等 `GeneratedImage` の `model="imagen-..."` は単なる文字列値なので変更不要。残してよい。）

- [ ] **Step 2: テストが失敗することを確認**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL（edit_image 属性参照・件数不一致）

- [ ] **Step 3: models.py を修正**

`src/google_genmedia_mcp/core/models.py` で以下を実施:

(a) `_default_image_models()` を Gemini のみに置き換え:

```python
def _default_image_models() -> list[ModelEntry]:
    """画像モデルのデフォルト定義（Gemini）."""
    return [
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
```

(b) `GenerateImageToolConfig` から未使用フィールドを削除（`number_of_images`, `output_mime_type`）:

```python
class GenerateImageToolConfig(BaseModel):
    """generate_image ツール設定."""

    model_config = ConfigDict(populate_by_name=True)

    aspect_ratio: str = Field(default="16:9", alias="aspectRatio")
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
```

(c) `_default_imagen_edit_models()` 関数を**削除**。

(d) `EditImageToolConfig` クラスを**削除**。

(e) `ToolsConfig` から `edit_image` フィールドを削除:

```python
class ToolsConfig(BaseModel):
    """ツール別設定."""

    model_config = ConfigDict(populate_by_name=True)

    generate_image: GenerateImageToolConfig = Field(
        default_factory=GenerateImageToolConfig, alias="generateImage"
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
```

- [ ] **Step 4: テストが通ることを確認**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: 全テスト・lint・型チェック**

Run: `uv run pytest`
Expected: PASS

Run: `uv run ruff check src/ tests/`
Expected: All checks passed

Run: `uv run mypy src/`
Expected: Success（エラーなし）

- [ ] **Step 6: コミット**

```bash
git add -A
git commit -m "refactor(models): EditImageToolConfig と Imagen モデル定義を削除"
```

---

## Task 7: config.example.yaml を更新

**Files:**
- Modify: `config.example.yaml`

- [ ] **Step 1: generateImage セクションを Gemini のみ・未使用キー削除**

`config.example.yaml` の `generateImage` を以下に置き換える:

```yaml
  generateImage:
    aspectRatio: "16:9"
    defaultModel: "Nano Banana 2"
    models:
      - id: "gemini-3.1-flash-image-preview"
        aliases: ["Nano Banana 2", "gemini-3.1-flash-image"]
        global: true  # Vertex AI ではグローバルエンドポイントが必要
      - id: "gemini-3-pro-image-preview"
        aliases: ["Nano Banana Pro", "gemini-3-pro-image"]
        global: true  # Vertex AI ではグローバルエンドポイントが必要
      - id: "gemini-2.5-flash-image"
        aliases: ["Nano Banana", "gemini-2.5-flash-preview-image-generation"]
```

- [ ] **Step 2: editImage セクションを削除**

`config.example.yaml` の `editImage:` セクション全体（`editImage:` から次の `generateVideo:` の直前まで）を削除する。

- [ ] **Step 3: generateVideo / generateVideoFromImage の models を GA ID に更新**

両セクションの `models` リストを以下に置き換える（2 箇所とも同一内容）:

```yaml
    models:
      - id: "veo-3.1-generate-001"
        aliases: ["Veo 3.1", "veo-3.1"]
      - id: "veo-3.1-fast-generate-001"
        aliases: ["Veo 3.1 Fast", "veo-3.1-fast"]
      - id: "veo-3.1-lite-generate-001"
        aliases: ["Veo 3.1 Lite", "veo-3.1-lite"]
      - id: "veo-3.0-generate-001"
        aliases: ["Veo 3", "veo-3.0"]
      - id: "veo-3.0-fast-generate-001"
        aliases: ["Veo 3 Fast", "veo-3.0-fast"]
      - id: "veo-2.0-generate-001"
        aliases: ["Veo 2", "veo-2.0"]
```

- [ ] **Step 4: 設定読み込みを確認**

Run: `uv run python -c "import yaml; from google_genmedia_mcp.core.models import GenMediaConfig; d=yaml.safe_load(open('config.example.yaml')); GenMediaConfig.model_validate(d); print('config ok')"`
Expected: `config ok`

- [ ] **Step 5: コミット**

```bash
git add config.example.yaml
git commit -m "chore(config): config.example.yaml を Imagen 削除・Veo GA 化に同期"
```

---

## Task 8: ドキュメントを更新

**Files:**
- Modify: `docs/MODELS.md`
- Modify: `docs/TOOLS.md`
- Modify: `docs/SETUP.md`
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: docs/MODELS.md を更新**

- 「Imagen（画像生成）」セクション全体を削除。
- 「Gemini Image（画像生成・編集）」セクションを画像生成・編集の主役として記述（`generate_image` の `reference_image` で編集する旨を追記）。
- 「Veo（動画生成）」の表を GA ID に更新し、`veo-3.1-lite-generate-001`（`Veo 3.1 Lite`, `veo-3.1-lite`）行を追加。preview 行を削除。「Vertex AI では `-001`、AI Studio では `-preview`」の注記から、廃止済み preview への言及を削除（現行は GA ID のみ対応）。
- 末尾「モデルエイリアスの使用方法」の例から Imagen 行・`Veo 3.1 → ...-preview` を削除し、`Veo 3.1 → veo-3.1-generate-001` 等の GA ID へ更新。「Imagen を使いたい場合は…」の段落を削除。

- [ ] **Step 2: docs/TOOLS.md を更新**

- `edit_image` ツールの記述を削除。
- `generate_image` の説明に「`reference_image`（ローカル/GCS）指定で参照画像編集が可能」を追記。
- Imagen 固有のパラメータ（`negative_prompt` / `output_mime_type` / `number_of_images`）への言及があれば削除。

- [ ] **Step 3: docs/SETUP.md を更新**

- Imagen / `edit_image` への言及箇所を削除・更新（grep: `grep -n "imagen\|Imagen\|edit_image" docs/SETUP.md` で該当行を確認して修正）。

- [ ] **Step 4: CLAUDE.md を更新**

- 「MCP Tools」の `edit_image: Image editing with Imagen ...` 行を削除。
- `generate_image` の説明を「Text-to-image and reference-image editing with Gemini」に更新。
- 冒頭 Project Overview や Configuration の `editImage` 言及を削除。`generateImage` の設定キー説明から `numberOfImages` / `outputMimeType` を削除。
- Authentication/Models 記述で Imagen に触れている箇所を整理。

- [ ] **Step 5: README.md を更新**

- `edit_image` / Imagen の記述を削除・更新（grep: `grep -n "imagen\|Imagen\|edit_image" README.md` で確認）。
- ツール一覧から `edit_image` を削除し、`generate_image` に編集用途を追記。

- [ ] **Step 6: コード内コメントの Imagen 言及を整理**

`src/google_genmedia_mcp/auth/manager.py` のコメント `Phase 1 全ツール（Imagen / Gemini Image / Veo）で使用する。` を `Phase 1 全ツール（Gemini Image / Veo）で使用する。` に修正する。

- [ ] **Step 7: 残存参照がないか確認**

Run: `grep -rn "edit_image\|imagen_edit\|EditImage\|imagen-4" src/ docs/ CLAUDE.md README.md config.example.yaml`
Expected: コード/設定に実体参照が残っていないこと（docs 内で「Imagen は廃止された」等の説明文として残すのは可。ただし本方針では完全削除のため、原則ヒットなし）

- [ ] **Step 8: コミット**

```bash
git add docs/ CLAUDE.md README.md src/google_genmedia_mcp/auth/manager.py
git commit -m "docs: Imagen 削除・edit_image 統合・Veo GA 化を反映"
```

---

## Task 9: 最終検証

**Files:** なし（検証のみ）

- [ ] **Step 1: lint**

Run: `uv run ruff check src/ tests/`
Expected: All checks passed

- [ ] **Step 2: 型チェック**

Run: `uv run mypy src/`
Expected: Success

- [ ] **Step 3: 全テスト + カバレッジ**

Run: `uv run pytest --cov`
Expected: PASS（失敗 0 件）

- [ ] **Step 4: サーバー起動・ツール登録確認**

Run: `uv run python -c "from google_genmedia_mcp.mcp.server import _register_tools; _register_tools(); from google_genmedia_mcp.mcp.server import mcp; import asyncio; print('registered')"`
Expected: `registered`（import / 登録エラーなし）

- [ ] **Step 5: 不要 import / デッドコードの最終 grep**

Run: `grep -rn "\.imagen\b\|imagen_edit\|ImagenService\|ImagenEditService\|EditImageToolConfig" src/`
Expected: ヒットなし

- [ ] **Step 6: 完了コミット（必要なら）**

検証で軽微な修正が出た場合のみコミット:

```bash
git add -A
git commit -m "chore: 最終検証の微修正"
```

---

## Self-Review メモ（計画作成者による確認）

- 仕様 A（Veo 更新）→ Task 1, 7, 8
- 仕様 B（Imagen 削除）→ Task 3, 5, 6, 7, 8
- 仕様 C（edit_image 統合）→ Task 2, 3, 4, 8
- 仕様 D（周辺更新）→ Task 4, 7, 8
- 仕様 E（テスト）→ 各タスクに内包
- 検証 → Task 9

依存順序: Task 2/3（Gemini 化）を Imagen 削除（Task 5）より先に行い、generate_image が imagen サービスに依存しない状態を作ってから削除する。server_info / edit_image の config 参照（Task 4）を EditImageToolConfig 削除（Task 6）より先に除去する。

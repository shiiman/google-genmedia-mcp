# 設計: モデル更新 + Imagen 廃止 + edit_image 統合

- 日付: 2026-05-29
- ステータス: 承認済み（実装待ち）
- 種別: 破壊的変更を含むモデル定義・ツール再構成

## 背景

Google の生成メディアモデルの更新に伴い、以下の対応が必要になった。

- **Veo**: preview ID が GA（`-001`）へ移行。`veo-3.1-generate-preview` 系は 2026-04-02 にシャットダウン済み。新モデル `veo-3.1-lite-generate-001`（preview, 最安）が追加された。
- **Imagen**: Imagen 4 ファミリー全て（`imagen-4.0-generate-001` / `-ultra-` / `-fast-`）が **2026-06-24 にシャットダウン**予定（本日から約4週間）。Google は Gemini 画像モデル（Nano Banana 系）への移行を推奨。
- **edit_image**: 現状 Imagen 専用ツール。Imagen 廃止により利用不能になるため、Gemini ベースへ移行する必要がある。

ユーザー決定事項:
1. Veo の正規 ID を preview → GA へ切替（OK）
2. 廃止予定モデルは注記保持ではなく**削除**
3. edit_image は Gemini へ移行し、**generate_image に統合**（edit_image ツールは廃止）
4. Imagen サービスコード（`imagen.py`）も完全削除
5. Gemini で無視される未使用パラメータ（`negative_prompt` / `output_mime_type` / `number_of_images`）は削除

## ゴール

- Veo モデル定義を GA ID 中心に更新し、`veo-3.1-lite` を追加、廃止 ID を削除する。
- Imagen を完全に削除する（モデル定義・サービス・ツール・設定・ドキュメント）。
- 画像編集機能を `generate_image` の `reference_image`（Gemini 編集）に一本化する。
- テスト・型チェック・lint を全て通す。

## 非ゴール

- Veo の `SupportsExtend`（動画延長）機能の実装。`veo-3.1-lite` は extend 対応だが、本プロジェクトに extend 機能は存在しないため対象外。
- Gemini によるマスクベースのインペイント/アウトペイント/背景置換の精密再現。Gemini は指示ベース編集のみ対応のため、これらの構造化編集機能は廃止する。
- 料金情報の精緻化（参考値のまま）。

## 設計詳細

### A. Veo モデル定義更新

対象: `src/google_genmedia_mcp/core/models.py` の `_default_veo_models()`。

更新後の正規 ID とエイリアス:

| 正規 ID | エイリアス | 備考 |
|---------|-----------|------|
| `veo-3.1-generate-001` | `Veo 3.1`, `veo-3.1` | デフォルト（preview→GA） |
| `veo-3.1-fast-generate-001` | `Veo 3.1 Fast`, `veo-3.1-fast` | preview→GA |
| `veo-3.1-lite-generate-001` | `Veo 3.1 Lite`, `veo-3.1-lite` | 新規（preview, 最安） |
| `veo-3.0-generate-001` | `Veo 3`, `veo-3.0` | preview→GA |
| `veo-3.0-fast-generate-001` | `Veo 3 Fast`, `veo-3.0-fast` | preview→GA |
| `veo-2.0-generate-001` | `Veo 2`, `veo-2.0` | 据置 |

**削除する ID**（preview 文字列はエイリアスとしても残さない）:
- `veo-3.1-generate-preview`, `veo-3.1-fast-generate-preview`（2026-04-02 シャットダウン済み）
- `veo-3.0-generate-preview`, `veo-3.0-fast-generate-preview`
- `veo-2.0-generate-exp`, `veo-2.0-generate-preview`

`GenerateVideoToolConfig` / `GenerateVideoFromImageToolConfig` の `defaultModel` は `"Veo 3.1"`（エイリアス）のままで、解決先が GA ID になる。

`VEO_MODEL_CONSTRAINTS` は変更不要。`get_veo_constraints()` のプレフィックスマッチで `veo-3.1-lite-generate-001` は `veo-3.1` 制約（durations `[4,6,8]`, max 4, `16:9`/`9:16`, audio あり）に解決される。

### B. Imagen 完全削除

1. `_default_image_models()`（`models.py`）から Imagen の3エントリ（`imagen-4.0-ultra/generate/fast-generate-001`）を削除し、**Gemini モデルのみ**にする。
2. `_default_imagen_edit_models()` と `EditImageToolConfig` を削除。`ToolsConfig.edit_image` フィールドを削除。
3. `GenerateImageToolConfig` から未使用フィールドを削除:
   - `number_of_images`（`numberOfImages`）
   - `output_mime_type`（`outputMimeType`）
   - 残すもの: `aspect_ratio`, `default_model`, `models`, `allow_unregistered`
4. サービス削除:
   - `src/google_genmedia_mcp/services/imagen.py` を削除
   - `src/google_genmedia_mcp/services/imagen_edit.py` を削除
   - `service.py` の `imagen` / `imagen_edit` プロパティとインスタンス変数・TYPE_CHECKING import を削除
5. `generate_image` ツール（`mcp/tools/image.py`）から `imagen-` プレフィックスのルーティング分岐を削除し、常に Gemini パスを使う。

### C. edit_image 統合（C案）

1. `src/google_genmedia_mcp/mcp/tools/image_edit.py` を削除。
2. `mcp/server.py` の edit_image ツール登録（import）を削除。
3. `GeminiImageService.generate`（`services/gemini_image.py`）を拡張し、**ローカルパスと GCS URI の両方**を参照画像として受け付ける:
   - GCS URI（`gs://`）: 現状どおり `types.Part.from_uri`
   - ローカルパス: `imagen_edit._validate_local_path` 相当の検証を行い、`types.Part.from_bytes(data=..., mime_type=...)` で渡す（パストラバーサル対策の検証を移植）
   - MIME 判定は拡張子（`.png` → `image/png`、それ以外 → `image/jpeg`）
4. `generate_image` ツール（`mcp/tools/image.py`）の最終シグネチャ:
   - `prompt: str`
   - `model: str | None = None`
   - `aspect_ratio: str | None = None`
   - `reference_image: str | None = None`（ローカル/GCS、編集兼用）
   - 削除: `number_of_images`, `negative_prompt`, `output_mime_type`
   - docstring を「テキスト生成 + 参照画像による編集」を兼ねる旨に更新。
5. 画像編集は「`reference_image` + 指示テキスト（`prompt`）」で `generate_image` から実行する。

### D. 周辺更新

- `mcp/tools/server_info.py`: ツール一覧から `edit_image` を除去、モデル一覧（Veo/画像）を更新。`imagen` 参照を削除。
- `config.example.yaml`: `editImage` セクション削除、`generateImage` の `models`（Gemini のみ）と未使用フィールド削除、`generateVideo` / `generateVideoFromImage` の `models` を GA ID へ更新。
- ドキュメント:
  - `docs/MODELS.md`: Imagen セクション削除、Gemini Image を画像生成・編集の主役に、Veo 表を GA ID へ更新、エイリアス例の更新。
  - `docs/TOOLS.md`: `edit_image` 記述削除、`generate_image` に編集用途（reference_image）を追記。
  - `docs/SETUP.md`: Imagen / edit_image 関連記述の削除・更新。
  - `CLAUDE.md`: MCP Tools の `edit_image` 行を削除、`generate_image` 説明を更新、Imagen 言及を整理。
  - `README.md`: 同様に edit_image / Imagen 記述を更新。

### E. テスト

- `tests/test_models.py`: Imagen / edit_image / 削除フィールド関連のアサーションを削除。Veo の GA ID・`veo-3.1-lite` 追加・廃止 ID 削除を検証。
- `tests/test_services.py`: `imagen` / `imagen_edit` サービステストを削除。`GeminiImageService` のローカル参照画像対応テストを追加。
- `tests/test_tools.py`: `edit_image` ツールテストを削除。`generate_image` の reference_image（ローカル/GCS）編集パスのテストを追加・更新。

## 影響範囲・破壊的変更

- **破壊的**: `edit_image` ツールが廃止される。既存利用者は `generate_image` の `reference_image` へ移行が必要。
- **破壊的**: Imagen モデル（`imagen-*`）が利用不可になる。ただし 2026-06-24 に API 側でシャットダウンされるため、いずれにせよ利用不能。
- **破壊的**: `generate_image` の `number_of_images` / `negative_prompt` / `output_mime_type` パラメータが削除される（Gemini では元々無視されていた）。
- **破壊的**: Veo の `*-preview` ID 文字列が解決不能になる（既に API 側で停止済みの ID を含む）。

## 検証手順

1. `uv run ruff check src/ tests/`
2. `uv run mypy src/`
3. `uv run pytest --cov`
4. `uv run google-genmedia-mcp` でサーバー起動確認、`server_info` の出力にツール/モデルが正しく反映されることを確認。

## 参照

- [Imagen 4.0 deprecation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/release-notes)
- [Veo 3.1 Lite on Vertex AI](https://cloud.google.com/blog/products/ai-machine-learning/veo-3-1-lite-and-a-new-veo-upscaling-capability-on-vertex-ai)
- [Nano Banana image generation/editing](https://ai.google.dev/gemini-api/docs/image-generation)

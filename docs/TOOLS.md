# ツール詳細仕様

google-genmedia-mcp が提供する全 8 ツールの詳細仕様です。

---

## 認証方式による利用可否

| ツール | API Key | Vertex AI ADC | OAuth |
|--------|---------|---------------|-------|
| `generate_image` | ✅ | ✅ | ✅ |
| `edit_image` | ✅ | ✅ | ✅ |
| `generate_video` | ✅ | ✅ | ✅ |
| `generate_video_from_image` | ✅ | ✅ | ✅ |
| `generate_speech` | ❌ | ✅ | ✅ |
| `generate_music` | ❌ | ✅ | ✅ |
| `combine_audio_video` | ✅ | ✅ | ✅ |
| `server_info` | ✅ | ✅ | ✅ |

> ❌ は API Key 方式で利用不可（Cloud 認証情報が必要）

---

## generate_image

テキストから画像を生成します。Imagen または Gemini モデルを自動切り替えします。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `prompt` | string | ✅ | — | 生成する画像の説明テキスト |
| `model` | string | — | Gemini デフォルト (Nano Banana 2) | モデル名またはエイリアス（Imagen/Gemini どちらも指定可） |
| `aspect_ratio` | string | — | `"16:9"` | アスペクト比（`1:1` / `16:9` / `9:16` / `4:3` / `3:4`） |
| `number_of_images` | integer | — | `1` | 生成枚数（1〜4）。Gemini 使用時は無視 |
| `negative_prompt` | string | — | null | 除外したい要素。Gemini 使用時は無視 |
| `output_mime_type` | string | — | `"image/png"` | 出力形式（`image/png` / `image/jpeg`）。Gemini 使用時は無視 |
| `reference_image` | string | — | null | 参照画像（GCS URI: `gs://...` またはローカルパス）。指定すると Gemini モードに切り替わる |

### モデル選択ロジック

- `model` が `imagen-` で始まる、または Imagen エイリアスの場合 → Imagen API を使用
- それ以外（未指定含む）→ Gemini API を使用（デフォルト: Nano Banana 2）
- `reference_image` を指定した場合 → Gemini 参照画像付き生成モード

### 戻り値

```json
{
  "images": [
    {
      "file_path": "/path/to/output/image_20241201_120000.png",
      "mime_type": "image/png",
      "model": "gemini-3.1-flash-image-preview"
    }
  ],
  "model": "gemini-3.1-flash-image-preview"
}
```

エラー時:

```json
{
  "error": "エラーメッセージ",
  "code": "ERROR_CODE",
  "hint": "対処方法のヒント"
}
```

### 使用例

```
# デフォルト（Nano Banana 2）でシンプルな画像生成
prompt: "富士山の夕暮れ、水彩画スタイル"

# デフォルトは 16:9。正方形にしたい場合は明示指定
prompt: "かわいい猫のイラスト"
aspect_ratio: "1:1"

# Imagen を明示的に指定（複数枚生成対応）
prompt: "都市の夜景、サイバーパンク"
model: "Imagen 4 Fast"
number_of_images: 4

# Nano Banana Pro で高品質生成
prompt: "プロフェッショナルな製品写真"
model: "Nano Banana Pro"

# 参照画像を使った Gemini 生成
prompt: "この画像をアニメ風に変換して"
reference_image: "gs://my-bucket/photo.jpg"
```

---

## edit_image

Imagen モデルで画像を編集します（インペインティング、アウトペインティング、背景置換など）。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `prompt` | string | ✅ | — | 編集内容の説明テキスト |
| `reference_image` | string | ✅ | — | 編集対象画像（GCS URI またはローカルパス） |
| `edit_mode` | string | — | `"inpaint_insertion"` | 編集モード（下記参照） |
| `mask_image` | string | — | null | マスク画像（inpaint 系で必須） |
| `model` | string | — | `imagen-4.0-generate-001` | モデル名またはエイリアス |
| `number_of_images` | integer | — | `1` | 生成枚数 |
| `negative_prompt` | string | — | null | 除外したい要素 |

### 編集モード

| モード | 説明 | mask_image |
|--------|------|-----------|
| `inpaint_insertion` | マスク領域にオブジェクトを追加 | 必須 |
| `inpaint_removal` | マスク領域のオブジェクトを除去 | 必須 |
| `outpaint` | 画像の外側を拡張 | 不要 |
| `background_replacement` | 背景を置換 | 不要 |

### 戻り値

`generate_image` と同じ形式。

---

## generate_video

Veo モデルでテキストから動画を生成します（Text-to-Video）。

**注意**: 動画生成には数分かかる場合があります（内部でポーリング処理を行います）。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `prompt` | string | ✅ | — | 生成する動画の説明テキスト |
| `model` | string | — | Veo デフォルト | モデル名またはエイリアス |
| `aspect_ratio` | string | — | `"16:9"` | アスペクト比（`16:9` / `9:16`） |
| `duration_seconds` | integer | — | `5` | 動画の長さ（秒、5〜8） |
| `number_of_videos` | integer | — | `1` | 生成本数 |

### 戻り値

```json
{
  "videos": [
    {
      "file_path": "/path/to/output/video_20241201_120000.mp4",
      "model": "veo-3.1-generate-preview",
      "duration_seconds": 5.0
    }
  ],
  "model": "veo-3.1-generate-preview"
}
```

---

## generate_video_from_image

Veo モデルで画像から動画を生成します（Image-to-Video）。

**注意**: GCS 上の画像が必要です（ローカルパス不可）。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `prompt` | string | ✅ | — | 動画の動きや内容を説明するテキスト |
| `image_gcs_uri` | string | ✅ | — | 参照画像の GCS URI（例: `gs://bucket/image.jpg`） |
| `model` | string | — | Veo デフォルト | モデル名またはエイリアス |
| `aspect_ratio` | string | — | `"16:9"` | アスペクト比（`16:9` / `9:16`） |
| `duration_seconds` | integer | — | `5` | 動画の長さ（秒） |

### 戻り値

`generate_video` と同じ形式。

---

## generate_speech

Chirp 3 HD でテキストを音声に変換します（Text-to-Speech）。

**注意**: Vertex AI または OAuth 認証方式でのみ利用可能です。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `text` | string | ✅ | — | 音声に変換するテキスト |
| `voice` | string | — | `"Kore"` | ボイス名（Aoede / Kore / Leda / Zephyr / Puck / Charon / Fenrir / Orus） |
| `language` | string | — | `"ja-JP"` | 言語コード（`ja-JP`, `en-US` 等） |
| `audio_encoding` | string | — | `"mp3"` | 出力フォーマット（`mp3` / `ogg_opus` / `pcm`） |

### 戻り値

```json
{
  "audio": {
    "file_path": "/path/to/output/speech_20241201_120000.mp3"
  },
  "model": "Chirp 3 HD",
  "voice": "ja-JP-Chirp3-HD-Kore"
}
```

---

## generate_music

Lyria モデルでテキストから音楽を生成します。

**注意**:
- Vertex AI または OAuth 認証方式でのみ利用可能です。
- 生成される音楽はインストゥルメンタルのみ（ボーカルなし）、30 秒固定です。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `prompt` | string | ✅ | — | 生成する音楽の説明（例: `"穏やかなピアノ曲、ジャズ風"`） |
| `model` | string | — | `lyria-002` | モデル名またはエイリアス |
| `negative_prompt` | string | — | null | 除外したい要素 |
| `seed` | integer | — | null | 再現性用シード値（0〜2147483647） |

### 戻り値

```json
{
  "audio": {
    "file_path": "/path/to/output/music_20241201_120000.wav"
  },
  "model": "lyria-002"
}
```

---

## combine_audio_video

動画ファイルと音声ファイルを ffmpeg で合成します。

**前提**: システムに `ffmpeg` がインストールされている必要があります。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `video_path` | string | ✅ | — | 動画ファイルのローカルパス |
| `audio_path` | string | ✅ | — | 音声ファイルのローカルパス |
| `output_path` | string | — | 自動生成 | 出力ファイルパス（省略時は出力ディレクトリに自動生成） |

### 戻り値

```json
{
  "output_path": "/path/to/output/combined_20241201_120000.mp4",
  "video_path": "/path/to/video.mp4",
  "audio_path": "/path/to/audio.mp3"
}
```

---

## server_info

MCP サーバーの情報と利用可能なツール・モデルの一覧を返します。

### パラメータ

なし

### 戻り値

```json
{
  "server": "google-genmedia-mcp",
  "version": "0.1.0",
  "auth": {
    "method": "vertex_ai",
    "has_cloud_credentials": true,
    "gcs_enabled": false
  },
  "available_tools": [
    "generate_image",
    "generate_video",
    "generate_video_from_image",
    "server_info",
    "edit_image",
    "generate_speech",
    "generate_music",
    "combine_audio_video"
  ],
  "unavailable_tools": [],
  "unavailable_reason": null,
  "models": {
    "imagen": { "default": "...", "available": [...] },
    "gemini": { "default": "...", "available": [...] },
    "veo": { "default": "...", "available": [...] },
    "lyria": { "default": "...", "available": [...] }
  },
  "chirp": {
    "default_voice": "Kore",
    "default_language": "ja-JP",
    "voices": [...]
  }
}
```

---

## エラーレスポンス形式

全ツールは失敗時に以下の形式でエラーを返します（例外を throw しません）。

```json
{
  "error": "ユーザー向けのエラーメッセージ",
  "code": "ERROR_CODE",
  "hint": "対処方法のヒント（省略される場合あり）"
}
```

### 主なエラーコード

| コード | 説明 |
|--------|------|
| `AUTH_ERROR` | 認証エラー |
| `CONFIG_ERROR` | 設定ファイルエラー |
| `MODEL_NOT_FOUND` | 指定したモデルが見つからない |
| `GENERATION_ERROR` | 生成 API エラー |
| `STORAGE_ERROR` | ファイル保存エラー |
| `UNSUPPORTED_AUTH_METHOD` | 認証方式が対応していない |
| `INTERNAL_ERROR` | 予期しない内部エラー |

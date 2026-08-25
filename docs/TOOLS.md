# ツール詳細仕様

google-genmedia-mcp が提供する全 7 ツールの詳細仕様です。

---

## 認証方式による利用可否

| ツール | API Key | Vertex AI ADC | OAuth |
|--------|---------|---------------|-------|
| `generate_image` | ✅ | ✅ | ✅ |
| `generate_video` | ✅ | ✅ | ✅ |
| `generate_video_from_image` | ✅ | ✅ | ✅ |
| `generate_speech` | ❌ | ✅ | ✅ |
| `generate_music` | ❌ | ✅ | ✅ |
| `combine_audio_video` | ✅ | ✅ | ✅ |
| `server_info` | ✅ | ✅ | ✅ |

> ❌ は API Key 方式で利用不可（Cloud 認証情報が必要）

---

## generate_image

テキストから画像を生成します。`reference_image` を指定すると参照画像編集（スタイル変換・加工等）も可能です。Gemini モデルを使用します。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `prompt` | string | ✅ | — | 生成する画像の説明テキスト |
| `model` | string | — | Nano Banana 2 (`gemini-3.1-flash-image`) | モデル名またはエイリアス |
| `aspect_ratio` | string | — | `"16:9"` | アスペクト比。Gemini 3.x 系は 15 種対応（`1:1` / `3:2` / `2:3` / `3:4` / `4:3` / `4:5` / `5:4` / `1:4` / `4:1` / `1:8` / `8:1` / `9:16` / `16:9` / `21:9` / `9:21`）。モデルにより対応値が異なる |
| `reference_image` | string | — | null | 参照画像（GCS URI: `gs://...` またはローカルパス）。指定すると参照画像付き生成モードで動作 |

### 戻り値

```json
{
  "images": [
    {
      "file_path": "/path/to/output/image_20241201_120000.png",
      "mime_type": "image/png",
      "model": "gemini-3.1-flash-image"
    }
  ],
  "model": "gemini-3.1-flash-image"
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

# Nano Banana Pro で高品質生成
prompt: "プロフェッショナルな製品写真"
model: "Nano Banana Pro"

# 参照画像を使った画像編集（スタイル変換・加工）
prompt: "この画像をアニメ風に変換して"
reference_image: "gs://my-bucket/photo.jpg"

# ローカルファイルを参照画像に使用
prompt: "この人物を宇宙飛行士の格好にして"
reference_image: "/Users/me/photo.jpg"
```

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
| `duration_seconds` | integer | — | `8` | 動画の長さ（秒）。Veo 3.x 系は `4` / `6` / `8`、Veo 2 は `5`〜`8` |
| `number_of_videos` | integer | — | `1` | 生成本数 |

### 戻り値

```json
{
  "videos": [
    {
      "file_path": "/path/to/output/video_20241201_120000.mp4",
      "model": "veo-3.1-generate-001",
      "duration_seconds": 8.0
    }
  ],
  "model": "veo-3.1-generate-001"
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
| `duration_seconds` | integer | — | `8` | 動画の長さ（秒）。Veo 3.x 系は `4` / `6` / `8`、Veo 2 は `5`〜`8` |

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
| `voice` | string | — | `"Kore"` | ボイス名（全 30 種。一覧は [MODELS.md](MODELS.md#利用可能ボイス全-30-種) 参照） |
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

**注意**: Lyria 2 は Vertex AI または OAuth 認証方式でのみ利用可能です。Lyria 3 は API Key 方式でも利用可能です。

### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `prompt` | string | ✅ | — | 生成する音楽の説明。Lyria 3 では歌詞や `[Verse]`/`[Chorus]` タグも指定可能 |
| `model` | string | — | Lyria 3 Pro (`lyria-3-pro-preview`) | モデル名またはエイリアス |
| `negative_prompt` | string | — | null | 除外したい要素（Lyria 2 のみ有効） |
| `seed` | integer | — | null | 再現性用シード値（0〜2147483647、Lyria 2 のみ有効） |

### モデル別の動作

| | Lyria 3 Pro | Lyria 3 Clip | Lyria 2 |
|---|---|---|---|
| 長さ | 最大約 184 秒（プロンプトで指定） | 30 秒固定 | 30 秒固定 |
| ボーカル | 対応 | 対応 | なし（インストのみ） |
| 歌詞指定 | `[Verse]`, `[Chorus]` 等で制御 | 同左 | 不可 |
| BPM | プロンプトで指定（例: "120 BPM"） | 同左 | 不可 |
| 出力形式 | MP3 | MP3 | WAV |
| API | generateContent (Gemini SDK) | 同左 | Predict (AI Platform) |

### 戻り値

```json
{
  "audios": [
    {
      "file_path": "/path/to/output/lyria3_20241201_120000.mp3",
      "audio_encoding": "mp3",
      "model": "lyria-3-pro-preview"
    }
  ],
  "text": "[Verse] 生成された歌詞...",
  "model": "lyria-3-pro-preview"
}
```

> `text` フィールドには Lyria 3 が生成した歌詞や楽曲構造が含まれます（Lyria 2 では null）。

### 使用例

```
# デフォルト（Lyria 3 Pro）でボーカル付き楽曲を生成
prompt: "明るいポップソング、120 BPM、日本語の歌詞付き"

# セクション構成を指定して生成
prompt: "[Intro] 静かなピアノ [Verse] 春の風が吹く街角で [Chorus] 未来へ続く道"

# インストのみ
prompt: "穏やかなピアノ曲、ジャズ風、Instrumental only, no vocals"

# 30 秒クリップ
prompt: "エレクトロニカ、ダンスミュージック"
model: "Lyria 3 Clip"

# Lyria 2（旧モデル）を明示指定
prompt: "壮大なオーケストラ曲"
model: "Lyria 2"
negative_prompt: "ドラム、パーカッション"
seed: 42
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
  "config_diagnostics": {
    "config_file_path": "~/.google-genmedia-mcp/config.yaml",
    "config_file_found": true,
    "home_directory": "/Users/you"
  },
  "auth": {
    "method": "vertex_ai",
    "has_cloud_credentials": true,
    "gcs_enabled": false
  },
  "available_tools": [
    "generate_image", "generate_video", "generate_video_from_image",
    "server_info", "generate_speech",
    "generate_music", "combine_audio_video"
  ],
  "unavailable_tools": [],
  "unavailable_reason": null,
  "tools_models": {
    "generate_image": {
      "default_model": "Nano Banana 2",
      "models": [
        { "id": "gemini-3.1-flash-image", "aliases": ["Nano Banana 2"] },
        { "id": "gemini-3-pro-image", "aliases": ["Nano Banana Pro"] }
      ]
    },
    "generate_video": { "default_model": "Veo 3.1", "models": [...] },
    "generate_video_from_image": { "default_model": "Veo 3.1", "models": [...] },
    "generate_music": { "default_model": "Lyria 3 Pro", "models": [...] }
  },
  "chirp": {
    "default_voice": "Kore",
    "default_language": "ja-JP",
    "voices": [{ "name": "Kore", "gender": "female" }, ...]
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
| `INVALID_GCS_URI` | GCS URI の形式が不正（`gs://` で始まっていない） |
| `INVALID_PARAMETER` | パラメータの値が不正（アスペクト比、秒数等） |
| `INTERNAL_ERROR` | 予期しない内部エラー |

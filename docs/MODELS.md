# 対応モデル一覧

google-genmedia-mcp がサポートするモデルの一覧と料金参考情報です。

---

## Gemini Image（画像生成・編集）

Gemini モデルを使用した画像生成・編集。`generate_image` ツールで使用。`model` 未指定時のデフォルトは Nano Banana 2。`reference_image` パラメータで参照画像を指定すると画像編集（スタイル変換・加工等）も可能。

| モデル ID | エイリアス | 特徴 | 対応解像度 | 参考料金 (Vertex AI) |
|-----------|-----------|------|-----------|---------------------|
| `gemini-3.1-flash-image` | `Nano Banana 2` | 高速・高品質（**デフォルト**） | 512 / 1K / 2K / 4K | $0.045〜$0.151 / 枚 ※解像度による |
| `gemini-3-pro-image` | `Nano Banana Pro` | 高品質・Pro グレード | 1K / 2K / 4K | $0.134〜$0.24 / 枚 ※解像度による |
| `gemini-3.1-flash-lite-image` | `Nano Banana 2 Lite`, `gemini-3.1-flash-lite` | 最速・最安 | 1K のみ | 最安（公式料金ページ参照） |
| `gemini-2.5-flash-image` | `Nano Banana`, `gemini-2.5-flash-preview-image-generation` | 旧世代 Flash | 指定不可 | $0.039 / 枚 |

> `allowUnregistered: true` が有効な場合、上記以外の Gemini モデル ID も指定可能です。
> ※ `gemini-2.5-flash-preview-image-generation` は旧 preview ID。現在は `gemini-2.5-flash-image` が正式 ID。
>
> **⚠️ Vertex AI のエンドポイント要件**: Gemini 3.x 系の 3 モデルは **global エンドポイント専用**です
> （`us-central1` 等のリージョン指定では 404）。本サーバーは `global: true` の設定に従って自動で切り替えます。
>
> **⚠️ 廃止予定**: `gemini-2.5-flash-image` は **2026-10-02 に廃止**予定です。
> 唯一リージョンエンドポイントに対応するモデルのため、以降は global エンドポイントが必須になります。

### 主な機能

- テキストから画像を生成（Text-to-Image）
- 参照画像を使用した画像編集・生成（`reference_image` 指定時）
- アスペクト比指定（Gemini 3.x 系は 15 種:
  `1:1` `3:2` `2:3` `3:4` `4:3` `4:5` `5:4` `1:4` `4:1` `1:8` `8:1` `9:16` `16:9` `21:9` `9:21`
  ※ `gemini-3.1-flash-lite-image` は `9:21` 非対応、`gemini-2.5-flash-image` は 10 種）

---

## Veo（動画生成）

テキストや画像から動画を生成するモデル。`generate_video` / `generate_video_from_image` ツールで使用。

| モデル ID | エイリアス | 特徴 | 参考料金 (Vertex AI) |
|-----------|-----------|------|---------------------|
| `veo-3.1-generate-001` | `Veo 3.1`, `veo-3.1` | 最新・高品質（**デフォルト**） | $0.35 / 秒 |
| `veo-3.1-fast-generate-001` | `Veo 3.1 Fast`, `veo-3.1-fast` | 最新・高速 | $0.35 / 秒 |
| `veo-3.1-lite-generate-001` | `Veo 3.1 Lite`, `veo-3.1-lite` | 最新・軽量 | $0.35 / 秒 |
| `veo-3.0-generate-001` | `Veo 3`, `veo-3.0` | 高品質 | $0.35 / 秒 |
| `veo-3.0-fast-generate-001` | `Veo 3 Fast`, `veo-3.0-fast` | 高速 | $0.35 / 秒 |
| `veo-2.0-generate-001` | `Veo 2`, `veo-2.0` | 旧世代 | $0.35 / 秒 |

> ※ 料金は生成された動画の秒数に応じた従量課金です。参考値のため最新の公式料金ページをご確認ください。

### 主な機能

- テキストから動画生成（Text-to-Video）
- 画像から動画生成（Image-to-Video）
- アスペクト比指定（16:9 / 9:16）
- 動画長指定（5〜8 秒）
- 非同期ポーリング処理（生成に数分かかる場合あり）

---

## Chirp 3 HD（音声合成 TTS）

テキストを音声に変換するモデル。`generate_speech` ツールで使用。

**注意**: Vertex AI または OAuth 認証方式でのみ利用可能。API Key 方式では使用できません。

| サービス | 料金 |
|---------|------|
| Cloud Text-to-Speech | 標準料金に準拠（公式ページ参照） |

### 利用可能ボイス（全 30 種）

実際のボイス名は `<ロケール>-Chirp3-HD-<ボイス名>` として合成されます（例: `ja-JP-Chirp3-HD-Kore`）。

| ボイス名 | 性別 |
|---------|------|
| Achernar | 女性 |
| Achird | 男性 |
| Algenib | 男性 |
| Algieba | 男性 |
| Alnilam | 男性 |
| Aoede | 女性 |
| Autonoe | 女性 |
| Callirrhoe | 女性 |
| Charon | 男性 |
| Despina | 女性 |
| Enceladus | 男性 |
| Erinome | 女性 |
| Fenrir | 男性 |
| Gacrux | 女性 |
| Iapetus | 男性 |
| Kore | 女性（**デフォルト**） |
| Laomedeia | 女性 |
| Leda | 女性 |
| Orus | 男性 |
| Pulcherrima | 女性 |
| Puck | 男性 |
| Rasalgethi | 男性 |
| Sadachbia | 男性 |
| Sadaltager | 男性 |
| Schedar | 男性 |
| Sulafat | 女性 |
| Umbriel | 男性 |
| Vindemiatrix | 女性 |
| Zephyr | 女性 |
| Zubenelgenubi | 男性 |

### 主な機能

- テキストから音声生成
- 言語コード指定（デフォルト: `ja-JP`）
- 出力フォーマット: MP3 / OGG Opus / PCM

---

## Lyria（音楽生成）

テキストから音楽を生成するモデル。`generate_music` ツールで使用。

**注意**: Vertex AI または OAuth 認証方式でのみ利用可能。API Key 方式では使用できません。

| モデル ID | エイリアス | 特徴 | 参考料金 |
|-----------|-----------|------|---------|
| `lyria-3-pro-preview` | `Lyria 3 Pro`, `lyria-3-pro` | 最大 184 秒、ボーカル・歌詞対応（**デフォルト**） | 要確認 |
| `lyria-3-clip-preview` | `Lyria 3 Clip`, `lyria-3-clip` | 30 秒クリップ、ボーカル対応 | 要確認 |
| `lyria-002` | `Lyria 2`, `lyria2` | インストゥルメンタル音楽生成 | 要確認 |

### Lyria 3 の機能（Pro / Clip 共通）

- テキストから音楽生成（ボーカル付き・インスト両対応）
- 歌詞指定: プロンプトに歌詞を含めるとボーカル付き楽曲を生成
- セクション制御: `[Verse]`, `[Chorus]`, `[Bridge]`, `[Intro]`, `[Outro]` タグで構成を指定
- BPM 制御: プロンプト内で自然言語指定（例: "120 BPM"）
- 言語: プロンプトの言語でボーカルを生成
- インストのみ: "Instrumental only, no vocals" と指定
- **Pro**: 最大約 184 秒、MP3 出力、タイムスタンプで長さ制御可能
- **Clip**: 30 秒固定、MP3 出力

### Lyria 2 の機能

- テキストからインストゥルメンタル音楽を生成（30 秒固定）
- ネガティブプロンプト対応
- シード値指定による再現性サポート
- WAV 形式で出力

---

## モデルエイリアスの使用方法

各ツールの `model` パラメータには、モデル ID またはエイリアスを指定できます。

```
# 例: generate_image でエイリアスを使用
model: "Nano Banana 2"      # -> gemini-3.1-flash-image  ← デフォルト
model: "Nano Banana Pro"    # -> gemini-3-pro-image
model: "Nano Banana 2 Lite" # -> gemini-3.1-flash-lite-image
model: "Nano Banana"        # -> gemini-2.5-flash-image
model: "Veo 3.1"            # -> veo-3.1-generate-001
model: "Veo 3.1 Fast"       # -> veo-3.1-fast-generate-001
model: "Veo 3.1 Lite"       # -> veo-3.1-lite-generate-001
model: "Veo 3"              # -> veo-3.0-generate-001
model: "Lyria 3 Pro"        # -> lyria-3-pro-preview
model: "Lyria 3 Clip"       # -> lyria-3-clip-preview
model: "Lyria 2"            # -> lyria-002
```

`generate_image` で `model` を省略した場合は config の `defaultModel`（デフォルト: Nano Banana 2）が使用されます。

### config.yaml でのモデルカスタマイズ

各ツールの `defaultModel` と `models` リストは `config.yaml` の `tools` セクションで変更可能です:

```yaml
tools:
  generateImage:
    defaultModel: "Nano Banana 2"
    models:
      - id: "gemini-3.1-flash-image"
        aliases: ["Nano Banana 2"]
        global: true    # Gemini 3.x 系は global エンドポイント専用
      - id: "gemini-3-pro-image"
        aliases: ["Nano Banana Pro"]
        global: true
```

> `allowUnregistered: true`（`generateImage` のデフォルト）を設定すると、`models` リストに未登録のモデル ID も直接指定可能です。

---

## 料金に関する注意

- 上記料金はすべて参考値です。実際の料金は [Google Cloud 料金ページ](https://cloud.google.com/vertex-ai/pricing) をご確認ください。
- Vertex AI の従量課金は、プロジェクト・リージョン・利用量に応じて異なります。
- 無料枠が適用される場合があります。

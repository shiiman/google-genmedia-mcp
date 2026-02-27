# 対応モデル一覧

google-genmedia-mcp がサポートするモデルの一覧と料金参考情報です。

---

## Imagen（画像生成）

テキストから画像を生成するモデル。`generate_image` ツールで使用。

| モデル ID | エイリアス | 特徴 | 参考料金 (Vertex AI) |
|-----------|-----------|------|---------------------|
| `imagen-4.0-ultra-generate-001` | `Imagen 4 Ultra`, `imagen-4.0-ultra` | 最高品質 | $0.06 / 枚 |
| `imagen-4.0-generate-001` | `Imagen 4`, `imagen-4.0` | 標準品質（`edit_image` **デフォルト**） | $0.04 / 枚 |
| `imagen-4.0-fast-generate-001` | `Imagen 4 Fast`, `imagen-4.0-fast` | 高速・低コスト | $0.02 / 枚 |

### 主な機能

- テキストから画像を生成（Text-to-Image）
- アスペクト比指定（1:1 / 16:9 / 9:16 / 4:3 / 3:4）
- 複数枚同時生成（1〜4 枚）
- ネガティブプロンプト対応
- PNG / JPEG 出力

---

## Gemini Image（画像生成・編集）

Gemini モデルを使用した画像生成。`generate_image` ツールで model 未指定時のデフォルト（Nano Banana 2）として使用。`model` パラメータで明示的に指定することも可能。参照画像付き生成も対応。

| モデル ID | エイリアス | 特徴 | 参考料金 (Vertex AI) |
|-----------|-----------|------|---------------------|
| `gemini-3.1-flash-image-preview` | `Nano Banana 2`, `gemini-3.1-flash-image` | 高速・高品質（**デフォルト**） | $0.045〜$0.151 / 枚 ※解像度による |
| `gemini-3-pro-image-preview` | `Nano Banana Pro`, `gemini-3-pro-image` | 高品質・Pro グレード | $0.134〜$0.24 / 枚 ※解像度による |
| `gemini-2.5-flash-image` | `Nano Banana`, `gemini-2.5-flash-preview-image-generation` | 旧世代 Flash | $0.039 / 枚 |

> `allowUnregistered: true` が有効な場合、上記以外の Gemini モデル ID も指定可能です。
> ※ `gemini-2.5-flash-preview-image-generation` は旧 preview ID。現在は `gemini-2.5-flash-image` が正式 ID。
> ※ `gemini-3.1-flash-image` は AI Studio での旧表記。正式 ID は `gemini-3.1-flash-image-preview`。

### 主な機能

- テキストから画像を生成（Text-to-Image）
- 参照画像を使用した画像生成（reference_image 指定時）
- アスペクト比指定

---

## Veo（動画生成）

テキストや画像から動画を生成するモデル。`generate_video` / `generate_video_from_image` ツールで使用。

| モデル ID | エイリアス | 特徴 | 参考料金 (Vertex AI) |
|-----------|-----------|------|---------------------|
| `veo-3.1-generate-preview` | `Veo 3.1`, `veo-3.1`, `veo-3.1-generate-001` | 最新・高品質（**デフォルト**） | $0.35 / 秒 |
| `veo-3.1-fast-generate-preview` | `Veo 3.1 Fast`, `veo-3.1-fast`, `veo-3.1-fast-generate-001` | 最新・高速 | $0.35 / 秒 |
| `veo-3.0-generate-preview` | `Veo 3`, `veo-3.0`, `veo-3.0-generate-001` | 高品質 | $0.35 / 秒 |
| `veo-3.0-fast-generate-preview` | `Veo 3 Fast`, `veo-3.0-fast`, `veo-3.0-fast-generate-001` | 高速 | $0.35 / 秒 |
| `veo-2.0-generate-001` | `Veo 2`, `veo-2.0` | 旧世代 | $0.35 / 秒 |

> ※ Vertex AI では `-001`（GA版）、AI Studio では `-preview`（プレビュー版）の ID が使われる場合があります。両方のエイリアスに対応しています。

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

### 利用可能ボイス

| ボイス名 | 性別 |
|---------|------|
| Aoede | 女性 |
| Kore | 女性（**デフォルト**） |
| Leda | 女性 |
| Zephyr | 女性 |
| Puck | 男性 |
| Charon | 男性 |
| Fenrir | 男性 |
| Orus | 男性 |

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
| `lyria-002` | `Lyria 2`, `lyria2` | インストゥルメンタル音楽生成（**デフォルト**） | 要確認 |

### 主な機能

- テキストから音楽生成（30 秒固定、インストゥルメンタルのみ）
- ネガティブプロンプト対応
- シード値指定による再現性サポート
- WAV 形式で出力

---

## モデルエイリアスの使用方法

各ツールの `model` パラメータには、モデル ID またはエイリアスを指定できます。

```
# 例: generate_image でエイリアスを使用
model: "Imagen 4 Ultra"    # -> imagen-4.0-ultra-generate-001
model: "Nano Banana 2"      # -> gemini-3.1-flash-image-preview  ← デフォルト
model: "Nano Banana"        # -> gemini-2.5-flash-image
model: "Veo 3.1"            # -> veo-3.1-generate-preview
model: "Veo 3"              # -> veo-3.0-generate-preview
model: "Lyria 2"            # -> lyria-002
```

`generate_image` で `model` を省略した場合は config の `defaultModel`（デフォルト: Nano Banana 2）が使用されます。
Imagen を使いたい場合は明示的にモデル名を指定してください（例: `model: "Imagen 4 Fast"`）。

### config.yaml でのモデルカスタマイズ

各ツールの `defaultModel` と `models` リストは `config.yaml` の `tools` セクションで変更可能です:

```yaml
tools:
  generateImage:
    defaultModel: "Imagen 4 Fast"   # デフォルトを Imagen に変更
    models:
      - id: "imagen-4.0-fast-generate-001"
        aliases: ["Imagen 4 Fast", "imagen-4.0-fast"]
      - id: "gemini-3.1-flash-image-preview"
        aliases: ["Nano Banana 2", "gemini-3.1-flash-image"]
```

> `allowUnregistered: true`（`generateImage` のデフォルト）を設定すると、`models` リストに未登録のモデル ID も直接指定可能です。

---

## 料金に関する注意

- 上記料金はすべて参考値です。実際の料金は [Google Cloud 料金ページ](https://cloud.google.com/vertex-ai/pricing) をご確認ください。
- Vertex AI の従量課金は、プロジェクト・リージョン・利用量に応じて異なります。
- 無料枠が適用される場合があります。

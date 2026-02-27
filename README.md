# google-genmedia-mcp

Google の生成メディア API（Imagen, Gemini Image, Veo, Chirp, Lyria）を提供する MCP サーバー。

Python + FastMCP + hatchling で実装。`uvx` でワンコマンドインストール可能。

---

## 特徴

- **モデルを設定ファイルで管理** — `config.yaml` でモデル追加・変更が可能（再ビルド不要）
- **3 つの認証方式** — API Key / Vertex AI / OAuth に対応
- **uvx でインストール** — `pip install` 不要、`uvx` で直接実行
- **Phase 1 / Phase 2** — 画像・動画生成（Phase 1）+ 画像編集・TTS・音楽生成（Phase 2）

---

## インストール

GitHub から直接インストールできます（リポジトリの clone は不要）。

### CLI で追加

通常運用では `--reinstall` なしを推奨します。
追加コマンドは次の「設定の追加・削除（再インストールとは別）」を参照してください。

### 設定の追加・削除（再インストールとは別）

**Claude**

```bash
# 追加（--reinstall なし）
claude mcp add --scope user google-genmedia-mcp -- uvx --from git+https://github.com/shiiman/google-genmedia-mcp google-genmedia-mcp

# 削除
claude mcp remove google-genmedia-mcp
```

**Codex**

```bash
# 追加（--reinstall なし）
codex mcp add google-genmedia-mcp -- uvx --from git+https://github.com/shiiman/google-genmedia-mcp google-genmedia-mcp

# 削除
codex mcp remove google-genmedia-mcp
```

### 設定ファイルに直接記述

**グローバル設定** (`~/.claude.json`):

```json
{
  "mcpServers": {
    "google-genmedia-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/shiiman/google-genmedia-mcp",
        "google-genmedia-mcp"
      ]
    }
  }
}
```

**プロジェクト設定** (`.mcp.json` をプロジェクトルートに作成):

```json
{
  "mcpServers": {
    "google-genmedia-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/shiiman/google-genmedia-mcp",
        "google-genmedia-mcp"
      ]
    }
  }
}
```

### 自動更新について

`--reinstall` オプションを付けると、起動時に毎回 GitHub から最新版を再インストールします。

> **Note**: `--refresh` オプションでは Git リポジトリのキャッシュが効いたままになり、更新が反映されないことがあります。確実に最新版を使用するには `--reinstall` を推奨します。

`--reinstall` なし運用で更新したい場合は、次の「必要なときだけ再インストールする手順」を実行してください。

**必要なときだけ再インストールする手順（Claude/Codex 共通）**:

```bash
# 1) 1回だけ再インストール（通常運用では毎回不要）
uv tool install --force --from git+https://github.com/shiiman/google-genmedia-mcp google-genmedia-mcp

# 2) 使用中のクライアントを再起動して MCP を再接続
# - Claude を使っている場合: Claude を再起動
# - Codex を使っている場合: Codex を再起動

# 3) 反映確認（使用クライアントに応じて実行）
claude mcp list
codex mcp get google-genmedia-mcp

# 4) 反映されない場合のみキャッシュクリア
uv cache clean google-genmedia-mcp
```

### 設定の確認

```bash
claude mcp list
codex mcp list
```

---

## 設定

設定ファイル: `~/.google-genmedia-mcp/config.yaml`

`config.example.yaml` をコピーして編集してください:

```bash
mkdir -p ~/.google-genmedia-mcp
cp config.example.yaml ~/.google-genmedia-mcp/config.yaml
```

---

## 認証設定

### 方式 1: API Key（最も簡単、Phase 1 のみ）

[Google AI Studio](https://aistudio.google.com/) で API Key を取得してください。

```yaml
auth:
  method: "api_key"
  apiKey: "YOUR_API_KEY"
```

または環境変数:

```bash
export GENMEDIA_API_KEY="YOUR_API_KEY"
```

**制限:** API Key 方式では Chirp TTS と Lyria 音楽生成は利用できません。

---

### 方式 2: Vertex AI（全機能対応）

```bash
gcloud auth application-default login
```

```yaml
auth:
  method: "vertex_ai"
  vertexAi:
    project: "your-project-id"
    location: "us-central1"

gcs:
  enabled: true
  bucket: "your-gcs-bucket"
```

---

### 方式 3: OAuth（全機能対応）

OAuth クライアント ID が必要です（[Google Cloud Console](https://console.cloud.google.com/) で作成）。

```yaml
auth:
  method: "oauth"
  oauth:
    clientId: "YOUR_CLIENT_ID"
    clientSecret: "YOUR_CLIENT_SECRET"
```

初回認証:

```bash
uvx --from git+https://github.com/shiiman/google-genmedia-mcp google-genmedia-mcp auth login
```

---

## 利用可能ツール

### Phase 1: 画像・動画生成

| ツール | 説明 | 認証 |
|--------|------|------|
| `generate_image` | Imagen / Gemini でテキストから画像を生成 | 全方式 |
| `generate_video` | Veo でテキストから動画を生成 | 全方式 |
| `generate_video_from_image` | Veo で画像から動画を生成 | 全方式 |
| `server_info` | サーバー情報・利用可能ツール一覧 | 全方式 |

### Phase 2: 画像編集・音声・音楽

| ツール | 説明 | 認証 |
|--------|------|------|
| `edit_image` | Imagen で画像を編集（インペインティング等） | 全方式 |
| `generate_speech` | Chirp 3 HD でテキストを音声に変換 | Vertex AI / OAuth |
| `generate_music` | Lyria で音楽を生成（30 秒） | Vertex AI / OAuth |
| `combine_audio_video` | ffmpeg で動画と音声を合成 | 全方式 |

---

## モデル設定

`config.yaml` でモデルを追加・変更できます:

```yaml
models:
  imagen:
    default: "imagen-4.0-fast-generate-001"
    available:
      - id: "imagen-4.0-ultra-generate-001"
        aliases: ["Imagen 4 Ultra"]
      - id: "imagen-4.0-generate-001"
        aliases: ["Imagen 4"]

  veo:
    default: "veo-3.0-generate-preview"
    available:
      - id: "veo-3.0-generate-preview"
        aliases: ["Veo 3"]
      - id: "veo-2.0-generate-001"
        aliases: ["Veo 2"]
```

---

## 出力先

デフォルト: `~/.google-genmedia-mcp/output/`

変更方法:

```yaml
output:
  directory: "/path/to/your/output"
```

---

## 開発

```bash
# リポジトリをクローン
git clone https://github.com/shiiman/google-genmedia-mcp
cd google-genmedia-mcp

# 依存関係インストール（Phase 2 含む）
uv sync --extra phase2 --extra dev

# テスト
uv run pytest --cov

# リント
uv run ruff check src/ tests/

# 型チェック
uv run mypy src/

# サーバー起動
uv run google-genmedia-mcp
```

---

## ライセンス

MIT

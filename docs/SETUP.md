# セットアップガイド

google-genmedia-mcp のインストールと設定手順です。

---

## 必要条件

- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/) または pip
- Google Cloud アカウント（Vertex AI 機能を使用する場合）
- ffmpeg（`combine_audio_video` ツールを使用する場合）

---

## インストール

### uvx でインストール（推奨）

```bash
uvx --from git+https://github.com/your-org/google-genmedia-mcp google-genmedia-mcp
```

### pip でインストール

```bash
pip install git+https://github.com/your-org/google-genmedia-mcp
```

### ソースからインストール

```bash
git clone https://github.com/your-org/google-genmedia-mcp.git
cd google-genmedia-mcp
uv sync
uv run google-genmedia-mcp
```

---

## 設定ファイル

### 配置場所

設定ファイルは以下の場所に配置します。

```
~/.google-genmedia-mcp/config.yaml
```

### 環境変数でパスを変更

```bash
export GENMEDIA_CONFIG_PATH=/path/to/my/config.yaml
```

### サンプル設定

`config.example.yaml` をコピーして編集します。

```bash
mkdir -p ~/.google-genmedia-mcp
cp config.example.yaml ~/.google-genmedia-mcp/config.yaml
```

---

## 認証方式ごとのセットアップ

### 1. API Key 方式（最も簡単）

Google AI Studio で API Key を取得し、設定ファイルに記載します。

**対応ツール**: `generate_image`, `edit_image`, `generate_video`, `generate_video_from_image`, `combine_audio_video`, `server_info`
**非対応**: `generate_speech`, `generate_music`（Cloud 認証情報が必要）

**設定例**:

```yaml
auth:
  method: "api_key"
  apiKey: "AIzaSy..."   # AI Studio の API Key
```

**環境変数でも設定可能**:

```bash
export GENMEDIA_API_KEY="AIzaSy..."
```

#### API Key の取得

1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. 右上の「Get API key」をクリック
3. 「Create API key」でキーを発行

---

### 2. Vertex AI ADC 方式（全機能対応）

Google Cloud SDK の Application Default Credentials（ADC）を使用します。

**対応ツール**: 全ツール（`generate_speech`, `generate_music` を含む）

#### 手順

1. Google Cloud SDK をインストール

   ```bash
   # macOS (Homebrew)
   brew install google-cloud-sdk

   # または公式インストーラー
   # https://cloud.google.com/sdk/docs/install
   ```

2. ADC を設定

   ```bash
   gcloud auth application-default login
   ```

3. プロジェクトを設定

   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

4. 必要な API を有効化

   ```bash
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable texttospeech.googleapis.com
   ```

5. 設定ファイルを編集

   ```yaml
   auth:
     method: "vertex_ai"
     vertexAi:
       project: "your-project-id"
       location: "us-central1"
   ```

**環境変数でも設定可能**:

```bash
export GENMEDIA_PROJECT="your-project-id"
export GENMEDIA_LOCATION="us-central1"
```

---

### 3. OAuth 方式（ブラウザ認証）

Google OAuth 2.0 でブラウザ認証を行います。

**対応ツール**: 全ツール

#### 手順

1. Google Cloud Console で OAuth クライアントを作成
   - [API とサービス > 認証情報](https://console.cloud.google.com/apis/credentials) にアクセス
   - 「認証情報を作成 > OAuth クライアント ID」を選択
   - アプリケーションの種類: 「デスクトップアプリ」
   - クライアント ID とクライアントシークレットをメモ

2. 設定ファイルを編集

   ```yaml
   auth:
     method: "oauth"
     oauth:
       clientId: "YOUR_CLIENT_ID.apps.googleusercontent.com"
       clientSecret: "YOUR_CLIENT_SECRET"
   ```

3. ログイン実行（ブラウザが開きます）

   ```bash
   google-genmedia-mcp auth login
   ```

   認証後、トークンが `~/.google-genmedia-mcp/oauth_token.json` に保存されます。

---

## config.yaml 設定項目

```yaml
# ===== 認証 =====
auth:
  method: "vertex_ai"       # "api_key" | "vertex_ai" | "oauth"
  apiKey: ""                # API Key 方式用
  vertexAi:
    project: "your-project" # GCP プロジェクト ID
    location: "us-central1" # リージョン
  oauth:
    clientId: ""            # OAuth クライアント ID
    clientSecret: ""        # OAuth クライアントシークレット

# ===== 出力ディレクトリ =====
output:
  directory: ".google-genmedia-mcp/output"  # 生成ファイルの保存先

# ===== GCS（Vertex AI 方式のみ）=====
gcs:
  enabled: false            # GCS へのアップロードを有効化
  bucket: "your-bucket"     # GCS バケット名

# ===== サーバー設定 =====
server:
  transport: "stdio"        # "stdio" | "sse" | "streamable-http"
  host: "127.0.0.1"        # SSE/HTTP 時のホスト
  port: 8000               # SSE/HTTP 時のポート
  logLevel: "INFO"         # ログレベル

# ===== モデル定義 =====
models:
  imagen:
    default: "imagen-4.0-fast-generate-001"
    available:
      - id: "imagen-4.0-ultra-generate-001"
        aliases: ["Imagen 4 Ultra", "imagen-4.0-ultra"]
      # ...
  gemini:
    default: "gemini-3.1-flash-image-preview"
    allowUnregistered: true  # 未登録 Gemini モデルの使用を許可
    available:
      # ...
  # 以下同様: veo, lyria

# ===== Chirp TTS ボイス設定 =====
chirp:
  defaultVoice: "Kore"
  defaultLanguage: "ja-JP"
  voices:
    - name: "Kore"
      gender: "female"
    # ...

# ===== Veo ポーリング設定 =====
veo:
  pollInterval: 15    # ポーリング間隔（秒）
  pollTimeout: 600    # タイムアウト（秒）
```

---

## GCS バケットの準備

Veo の動画生成や GCS 保存機能を使用する場合、GCS バケットが必要です。

```bash
# バケットの作成
gcloud storage buckets create gs://your-bucket-name \
  --location=us-central1 \
  --project=your-project-id

# 必要な権限の付与（サービスアカウントを使用する場合）
gcloud storage buckets add-iam-policy-binding gs://your-bucket-name \
  --member="serviceAccount:your-sa@your-project.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

設定ファイルでバケットを有効化:

```yaml
gcs:
  enabled: true
  bucket: "your-bucket-name"
```

---

## Claude Desktop への設定

`~/.claude/claude_desktop_config.json` に追記します。

### stdio モードで使用する場合

```json
{
  "mcpServers": {
    "google-genmedia": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/your-org/google-genmedia-mcp",
        "google-genmedia-mcp"
      ],
      "env": {
        "GENMEDIA_CONFIG_PATH": "/path/to/your/config.yaml"
      }
    }
  }
}
```

### ローカル開発版を使用する場合

```json
{
  "mcpServers": {
    "google-genmedia": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/google-genmedia-mcp",
        "run",
        "google-genmedia-mcp"
      ]
    }
  }
}
```

---

## ffmpeg のインストール

`combine_audio_video` ツールを使用する場合に必要です。

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

---

## トラブルシューティング

### 「設定ファイルが見つからない」

`~/.google-genmedia-mcp/config.yaml` が存在するか確認してください。

```bash
ls ~/.google-genmedia-mcp/
```

### 「API Key が無効」

`config.yaml` の `auth.apiKey` または環境変数 `GENMEDIA_API_KEY` を確認してください。

### 「認証情報が見つからない」（Vertex AI 方式）

```bash
gcloud auth application-default login
gcloud config list  # project が設定されているか確認
```

### 「generate_speech / generate_music が利用不可」

これらのツールは API Key 方式では利用できません。Vertex AI または OAuth 方式に切り替えてください。

### 「ffmpeg が見つからない」

ffmpeg をインストールし、PATH に含まれているか確認してください。

```bash
which ffmpeg
ffmpeg -version
```

### 本番環境でのログ設定

デフォルトの logLevel は INFO ですが、プロンプト内容の一部がログに記録されます。
機密情報を含むプロンプトを使用する場合は、logLevel を WARNING 以上に設定してください。

```yaml
server:
  logLevel: "WARNING"
```

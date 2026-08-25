---
name: update-models
description: Google 生成メディアモデル（Gemini Image, Veo, Chirp, Lyria）の最新情報を調査し、プロジェクトのモデル定義・設定・ドキュメントを更新する。「モデル更新」「最新モデル確認」「update models」「モデルチェック」「新しいモデルあるか確認」「公式リポ確認」などで起動。
allowed-tools: [Read, Bash, Glob, Grep, Edit, Write, Agent, WebFetch, WebSearch]
argument-hint: "[--check|--update|--help]"
context: fork
---

# Update Models — Google 生成メディアモデル更新スキル

Google の生成メディアモデル（Gemini Image, Veo, Chirp, Lyria）の最新状態を調査し、
Imagen は全生成エンドポイントが廃止済み（Vertex: 2026-06-30 / Gemini API: 2026-08-17）のため、
本プロジェクトからは削除されている。調査対象に含めない。
このプロジェクトのコード・設定・ドキュメントを最新に保つためのスキル。

## Help

`$ARGUMENTS` に `--help` が含まれる場合、以下を表示して終了:

```text
/update-models - モデル更新スキル

概要:
  Google 生成メディアモデルの最新情報を調査し、プロジェクトを更新する。
  公式リポジトリと Google ドキュメントの両方から情報を収集する。

使用方法:
  /update-models [オプション]

オプション:
  --help     このヘルプを表示
  --check    調査のみ（変更なし）。差分レポートを出力
  --update   調査後、ユーザー確認を経てコード・ドキュメントを更新（デフォルト）

デフォルト動作:
  引数なしの場合は --update（調査 → 確認 → 更新 → 検証）

例:
  /update-models              # 調査 → 確認 → コード更新 → ドキュメント更新 → 検証
  /update-models --check      # 調査のみ（差分レポート表示）
  /update-models --update     # 明示的に更新モード
```

## モード判定

- `$ARGUMENTS` に `--check` が含まれる場合: **調査モード**（Phase 1〜3 のみ）
- `$ARGUMENTS` に `--update` が含まれる場合、または引数なし: **更新モード**（Phase 1〜7）

---

## Phase 1: 公式リポジトリの確認

Google 公式 MCP リポジトリから最新のモデル定義を取得する。

> **注意**: GitHub URL の取得には `gh` CLI を優先的に使用する。
> WebFetch は GitHub URL に対して失敗しやすいため、フォールバックとしてのみ使用する。
>
> **⚠️ パスは移動しうる**: 以前 `mcp-genmedia/mcp-common/` だったものが
> `mcp-genmedia/mcp-genmedia-go/mcp-common/` へ移動した（2026-08 時点）。
> 404 が返ったら Phase 1-2 のツリー取得で `models.go` の現在位置を探すこと。

### 1-1. models.go の取得

Bash で `gh api` を使用して取得:

```bash
gh api repos/GoogleCloudPlatform/vertex-ai-creative-studio/contents/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common/models.go --jq '.content' | base64 -d
```

`gh` CLI が使えない場合のフォールバック（WebFetch）:

```
https://raw.githubusercontent.com/GoogleCloudPlatform/vertex-ai-creative-studio/main/experiments/mcp-genmedia/mcp-genmedia-go/mcp-common/models.go
```

### 1-2. リポジトリツリーの確認

Bash で `gh api` を使用してツリーを取得し、新しいファイル・ディレクトリの追加を検出:

```bash
gh api 'repos/GoogleCloudPlatform/vertex-ai-creative-studio/git/trees/main?recursive=1' --jq '.tree[].path' | grep 'experiments/mcp-genmedia'
```

`experiments/mcp-genmedia` 配下のファイル一覧を抽出し、前回との差異を確認する。

### 1-3. models.go のパース

Go コードから以下を抽出:

- モデル ID（文字列リテラル）
- モデルカテゴリ（Veo / Gemini Image / Chirp / Lyria）
- 制約情報（aspect ratio, duration など）
- 新しい定数・構造体

---

## Phase 2: Web 検索による最新モデル調査

公式リポだけでは最新情報が不十分（かつ古い場合もある）ため、Google ドキュメントを直接検索する。

> **⚠️ ドキュメントのドメイン移行済み（2026-08 時点）**
> `cloud.google.com/vertex-ai/generative-ai/docs/*` は
> `docs.cloud.google.com/vertex-ai/generative-ai/docs/*` へ 301 リダイレクトする。
> さらにモデルカードは `docs.cloud.google.com/gemini-enterprise-agent-platform/models/*`
> へ再配置され、"Gemini Enterprise Agent Platform" へリブランド中。
> 古い URL をハードコードしても 301 で追えるが、検索は新ドメインで行うこと。

### 2-1. モデル別検索

WebSearch で以下のクエリを**並列実行**（Agent ツールでサブエージェントを活用可能）:

- `site:docs.cloud.google.com Veo model latest`
- `site:docs.cloud.google.com Gemini image generation model`
- `site:docs.cloud.google.com Chirp 3 HD voices`
- `site:docs.cloud.google.com Lyria music generation model`
- `site:ai.google.dev gemini image generation models`

### 2-2. リリースノート・廃止情報の確認

**重要**: メディアモデルの廃止情報は専用の deprecations ページには載らない。
`deprecations` ページには Vertex AI SDK の項目しかないため、**リリースノートを直接読む**こと。

- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/release-notes （Vertex 側の廃止告知の本体）
- https://ai.google.dev/gemini-api/docs/deprecations （Gemini API 側。シャットダウン日が明記される）
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions （モデルのライフサイクル表）

### 2-3. 有用なページの詳細取得

検索結果から関連度の高いページを WebFetch で詳細取得する。特に:

- モデル一覧ページ
- API リファレンス
- リリースノート

> **⚠️ モデルカードは WebFetch では読めない**
> 個別モデルカード（`.../models/veo/3-1-generate`、`.../models/lyria/lyria-3` 等）と
> REST リファレンスは client-side rendering のため、WebFetch はナビゲーションのシェルしか返さない
> （`?hl=en` を付けても同じ）。仕様表を読むには以下のいずれかが必要:
>
> 1. **Playwright MCP で実ブラウザ描画**（`mcp__plugin_playwright_playwright__browser_navigate`）
> 2. **ライブ API で実測**（下記 2-5。最も強い証拠）
> 3. 検索インデックスのスニペット（弱い証拠。矛盾しうるので断定に使わない）

### 2-4. ライブ API による実機検証（最優先の証拠）

ドキュメントよりも実測が確実。`vertex_ai` 認証が設定済みなら、モデル ID の有効性を直接確認する。
プロジェクトの `AuthManager` がそのまま使える（`create_genai_client` = リージョン、
`create_genai_client_global` = global エンドポイント）:

```bash
uv run python - <<'EOF'
from google_genmedia_mcp.auth.manager import AuthManager
from google_genmedia_mcp.utils.config import get_config

config = get_config()
am = AuthManager()

CANDIDATES = [
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
    "gemini-3.1-flash-lite-image",
    "gemini-2.5-flash-image",
]

for label, client in (("region", am.create_genai_client(config)),
                      ("global", am.create_genai_client_global(config))):
    for model_id in CANDIDATES:
        try:
            # count_tokens は課金されず、シャットダウン済み ID では 404 になる
            client.models.count_tokens(model=model_id, contents="ping")
            print(f"{label:6} {model_id:32} OK")
        except Exception as e:
            print(f"{label:6} {model_id:32} {type(e).__name__}: {str(e)[:80]}")
EOF
```

注意点:

- `models.get` は**シャットダウン済み preview ID でも解決してしまう**ことがある。
  有効性の判定には `count_tokens` か `generate_content` を使う（画像は生成されないので課金なし）。
- Gemini 3.x 画像モデルは **global エンドポイント専用**。`us-central1` では 404 になる。
  リージョンで 404 だからといって「存在しない」と判断しないこと。

### 2-5. 結果の整理

検索結果から以下を抽出:

- 新しいモデル ID
- 既存モデルの名称変更・廃止
- 新しいパラメータ・機能・制約
- 料金変更

---

## Phase 3: 差分レポートの生成

### 3-1. 現在のモデル一覧の読み取り

以下のファイルを Read で確認:

- `src/google_genmedia_mcp/core/models.py` — `_default_*_models()` 関数群、`VEO_MODEL_CONSTRAINTS`
- `config.example.yaml` — ツール別モデルリスト
- `docs/MODELS.md` — ドキュメントのモデル一覧

**さらに、実際に稼働している設定も確認する**（gitignore 対象だが影響は最大）:

- `~/.google-genmedia-mcp/config.yaml` — 実行時に読まれる設定（`GENMEDIA_CONFIG_PATH` で上書き可）
- `./config.yaml` — プロジェクト直下のローカル設定

> **⚠️ 最重要**: `models:` リストは**既定値を完全に上書きする**（マージではない）。
> つまりコード（`_default_*_models()`）を直しても、これらの設定に古い ID が書かれていれば
> **サーバーは壊れたままになる**。「モデル ID が死んでいる」系の問題では必ず両方を確認し、
> レポートに「稼働中設定も要更新」と明記すること。

### 3-2. 差分分析・レポート出力

以下の形式でレポートを出力:

```
📊 モデル更新レポート
=====================

🔍 調査ソース:
  - 公式リポジトリ (mcp-genmedia): ✅ 取得成功 / ❌ 取得失敗
  - Google ドキュメント検索: ✅ N 件の関連情報

🆕 新規モデル（追加が必要）:
  - [Gemini Image] model-id — 説明
  - [Veo] model-id — 説明

🔄 更新されたモデル（変更が必要）:
  - [カテゴリ] model-id — 変更内容（制約変更、名称変更など）

⚠️ 廃止予定モデル:
  - [カテゴリ] model-id — 廃止情報

✅ 最新状態のモデル（変更不要）:
  - [Gemini Image] gemini-3.1-flash-image, ...
  - [Veo] veo-3.1-generate-001, ...

📝 その他の変更:
  - 新しいパラメータ、制約変更、料金変更など

📋 推奨アクション:
  1. [具体的な更新内容]
  2. ...
```

### 3-3. モード分岐

- **調査モード** (`--check`): レポートを表示して**終了**
- **更新モード** (`--update`): レポートを表示し、ユーザーに確認を求めてから Phase 4 へ進む

**重要**: 更新モードでも、Phase 4 に入る前に必ずユーザーに確認を求める。
「上記の更新を実施してよいですか？」と質問し、承認を得てから進む。

---

## Phase 4: コード更新（`--update` のみ）

ユーザーの承認後、以下のファイルを更新する。

### 4-1. models.py の更新

対象: `src/google_genmedia_mcp/core/models.py`

更新箇所（該当する場合のみ）:

- `_default_image_models()` — Gemini Image モデルの追加・変更（生成・参照画像編集の両方を担う）
- `_default_veo_models()` — Veo モデルの追加・変更
- `_default_lyria_models()` — Lyria モデルの追加・変更
- `_default_chirp_voices()` — Chirp ボイスの追加・変更
- `VEO_MODEL_CONSTRAINTS` — Veo 制約の追加・変更

更新ルール:

- 既存の `ModelEntry` パターンに従う（`id`, `aliases`, `global_` フィールド）
- エイリアスは「人間が読みやすい名前」+「短縮 ID」の 2 つ以上を含める
- 新しいモデルを既存リストの**先頭**に追加（最新 = 最上位）
- Gemini Image で Vertex AI グローバルエンドポイントが必要なものは `global_=True`
  （Gemini 3.x 系は**全て** global 専用）
- **有効なエイリアスは削除しない**（互換性維持）
- ただし**シャットダウン済み ID はエイリアスとしても残さず削除する**。
  残すと壊れた設定を温存し、ユーザーが 404 の原因に気付けなくなる
  （Veo の preview ID 削除、および Gemini Image の `-preview` 削除がこの前例）

### 4-2. config.example.yaml の更新

対象: `config.example.yaml`

- models.py と同期して、各ツールの `models:` リストを更新
- 新しいモデルのエイリアスを追加
- `defaultModel` は破壊的変更になるため、明確な理由がない限り変更しない

### 4-3. サービス実装の確認・更新

新しいモデルに固有の API パラメータや制約がある場合のみ:

- `src/google_genmedia_mcp/services/gemini_image.py`
- `src/google_genmedia_mcp/services/veo.py`
- `src/google_genmedia_mcp/services/chirp.py`
- `src/google_genmedia_mcp/services/lyria.py`

### 4-4. MCP ツール定義の確認・更新

新しいパラメータが追加された場合のみ:

- `src/google_genmedia_mcp/mcp/tools/image.py`
- `src/google_genmedia_mcp/mcp/tools/veo.py`
- `src/google_genmedia_mcp/mcp/tools/chirp.py`
- `src/google_genmedia_mcp/mcp/tools/lyria.py`

---

## Phase 5: ドキュメント更新（`--update` のみ）

### 5-1. docs/MODELS.md（必ず更新）

- 新しいモデルをテーブルに追加
- 料金情報の更新
- エイリアス一覧の更新
- 廃止モデルの注記
- 「モデルエイリアスの使用方法」セクションの例を更新

### 5-2. docs/TOOLS.md（パラメータ変更時のみ）

- 新しいパラメータの追加
- モデルデフォルト値が変更された場合の記述更新
- 新しい制約（アスペクト比、秒数など）の反映

### 5-3. docs/SETUP.md（認証要件変更時のみ）

- 新しい API 有効化が必要な場合に手順を追加
- 認証方式の変更がある場合のみ

### 5-4. README.md（大きな機能追加時のみ）

- MCP ツール一覧が変更された場合
- 新しいサービスが追加された場合

### 5-5. CLAUDE.md（アーキテクチャ変更時のみ）

- ディレクトリ構造が変更された場合
- ツール一覧が変更された場合

---

## Phase 6: 検証

### 6-1. テスト実行

```bash
uv run pytest --cov
```

### 6-2. Lint 実行

```bash
uv run ruff check src/ tests/
```

### 6-3. 型チェック

```bash
uv run mypy src/
```

### 6-4. 検証失敗時

エラー内容を報告し、修正を実施してから再検証する。
3 回以上失敗する場合はユーザーに報告して判断を仰ぐ。

---

## Phase 7: 完了レポート

最終レポートを表示:

```
📊 モデル更新完了レポート
========================

更新されたファイル:
  - src/google_genmedia_mcp/core/models.py
  - config.example.yaml
  - docs/MODELS.md
  - （その他変更されたファイル）

追加されたモデル:
  - [カテゴリ] モデルID — エイリアス

変更されたモデル:
  - [カテゴリ] モデルID — 変更内容

検証結果:
  - テスト: ✅ PASSED / ❌ FAILED
  - Lint: ✅ PASSED / ❌ FAILED
  - 型チェック: ✅ PASSED / ❌ FAILED

次のステップ:
  - `git diff` で変更内容を確認してください
  - 問題なければコミットしてください
```

---

## 注意事項

- **破壊的変更の回避**: 既存ユーザーの `config.yaml` を壊さないよう、デフォルト値の変更は慎重に行う
- **エイリアス互換性**: 既存エイリアスは削除しない（非推奨としてマークするだけ）
- **公式リポとの差異**: このプロジェクトは公式 Go 実装の制限を補うために作られたものであり、公式リポの変更を「そのまま」取り込むのではなく、このプロジェクトの設計方針に合わせて反映する
- **⚠️ 公式 Go リポは Google ドキュメントより古いことがある**:
  `models.go` は `veo-3.0` を「`16:9` のみ / 最大 2 本」としているが、
  Google ドキュメントは 9:16 対応・最大 4 本を明記している（本プロジェクトの
  `VEO_MODEL_CONSTRAINTS` が正しい）。公式リポと Google ドキュメントが食い違う場合、
  **Google ドキュメントまたはライブ API を優先**し、リポの値で上書きしないこと
- **証拠の強さの順序**: ライブ API 実測 > 実ブラウザで描画したモデルカード >
  リリースノート > 検索スニペット。スニペットだけを根拠に制約値をハードコードしない
  （Veo 3.1 の `durationSeconds` は `4,6,8` と `5,6,7,8` の 2 通りのスニペットが存在する）
- **WebFetch / WebSearch の失敗**: ネットワークエラー時はエラーメッセージを表示し、利用可能な情報のみでレポートを生成する
- **models.py が source of truth**: コードの変更を先に行い、ドキュメントはコードに合わせて更新する

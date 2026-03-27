---
name: update-models
description: Google 生成メディアモデル（Imagen, Veo, Gemini Image, Chirp, Lyria）の最新情報を調査し、プロジェクトのモデル定義・設定・ドキュメントを更新する。「モデル更新」「最新モデル確認」「update models」「モデルチェック」「新しいモデルあるか確認」「公式リポ確認」などで起動。
allowed-tools: [Read, Bash, Glob, Grep, Edit, Write, Agent, WebFetch, WebSearch]
argument-hint: "[--check|--update|--help]"
context: fork
---

# Update Models — Google 生成メディアモデル更新スキル

Google の生成メディアモデル（Imagen, Veo, Gemini Image, Chirp, Lyria）の最新状態を調査し、
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

### 1-1. models.go の取得

Bash で `gh api` を使用して取得:

```bash
gh api repos/GoogleCloudPlatform/vertex-ai-creative-studio/contents/experiments/mcp-genmedia/mcp-common/models.go --jq '.content' | base64 -d
```

`gh` CLI が使えない場合のフォールバック（WebFetch）:

```
https://raw.githubusercontent.com/GoogleCloudPlatform/vertex-ai-creative-studio/main/experiments/mcp-genmedia/mcp-common/models.go
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
- モデルカテゴリ（Imagen / Veo / Gemini / Chirp / Lyria）
- 制約情報（aspect ratio, duration など）
- 新しい定数・構造体

---

## Phase 2: Web 検索による最新モデル調査

公式リポだけでは最新情報が不十分な場合があるため、Google ドキュメントを直接検索する。

### 2-1. モデル別検索

WebSearch で以下のクエリを**並列実行**（Agent ツールで Explore サブエージェントを活用可能）:

- `site:cloud.google.com Imagen model latest 2025 2026`
- `site:cloud.google.com Veo model latest 2025 2026`
- `site:cloud.google.com Gemini image generation model 2025 2026`
- `site:cloud.google.com Chirp text-to-speech model 2025 2026`
- `site:cloud.google.com Lyria music generation model 2025 2026`

### 2-2. リリースノート確認

WebSearch で以下も検索:

- `site:cloud.google.com/vertex-ai/docs release notes generative AI`
- `site:ai.google.dev generative media models new`

### 2-3. 有用なページの詳細取得

検索結果から関連度の高いページを WebFetch で詳細取得する。特に:

- モデル一覧ページ
- API リファレンス
- リリースノート

### 2-4. 結果の整理

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

### 3-2. 差分分析・レポート出力

以下の形式でレポートを出力:

```
📊 モデル更新レポート
=====================

🔍 調査ソース:
  - 公式リポジトリ (mcp-genmedia): ✅ 取得成功 / ❌ 取得失敗
  - Google ドキュメント検索: ✅ N 件の関連情報

🆕 新規モデル（追加が必要）:
  - [Imagen] model-id — 説明
  - [Veo] model-id — 説明

🔄 更新されたモデル（変更が必要）:
  - [カテゴリ] model-id — 変更内容（制約変更、名称変更など）

⚠️ 廃止予定モデル:
  - [カテゴリ] model-id — 廃止情報

✅ 最新状態のモデル（変更不要）:
  - [Imagen] imagen-4.0-ultra-generate-001, ...
  - [Gemini Image] gemini-3.1-flash-image-preview, ...
  - [Veo] veo-3.1-generate-preview, ...

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

- `_default_image_models()` — Imagen / Gemini Image モデルの追加・変更
- `_default_imagen_edit_models()` — 画像編集モデルの追加・変更
- `_default_veo_models()` — Veo モデルの追加・変更
- `_default_lyria_models()` — Lyria モデルの追加・変更
- `_default_chirp_voices()` — Chirp ボイスの追加・変更
- `VEO_MODEL_CONSTRAINTS` — Veo 制約の追加・変更

更新ルール:

- 既存の `ModelEntry` パターンに従う（`id`, `aliases`, `global_` フィールド）
- エイリアスは「人間が読みやすい名前」+「短縮 ID」の 2 つ以上を含める
- 新しいモデルを既存リストの**先頭**に追加（最新 = 最上位）
- Gemini Image で Vertex AI グローバルエンドポイントが必要なものは `global_=True`
- **既存エイリアスは削除しない**（互換性維持）

### 4-2. config.example.yaml の更新

対象: `config.example.yaml`

- models.py と同期して、各ツールの `models:` リストを更新
- 新しいモデルのエイリアスを追加
- `defaultModel` は破壊的変更になるため、明確な理由がない限り変更しない

### 4-3. サービス実装の確認・更新

新しいモデルに固有の API パラメータや制約がある場合のみ:

- `src/google_genmedia_mcp/services/imagen.py`
- `src/google_genmedia_mcp/services/gemini_image.py`
- `src/google_genmedia_mcp/services/veo.py`
- `src/google_genmedia_mcp/services/chirp.py`
- `src/google_genmedia_mcp/services/lyria.py`

### 4-4. MCP ツール定義の確認・更新

新しいパラメータが追加された場合のみ:

- `src/google_genmedia_mcp/mcp/tools/image.py`
- `src/google_genmedia_mcp/mcp/tools/image_edit.py`
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
- 新しいサービス（Imagen, Veo 以外）が追加された場合

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
- **WebFetch / WebSearch の失敗**: ネットワークエラー時はエラーメッセージを表示し、利用可能な情報のみでレポートを生成する
- **models.py が source of truth**: コードの変更を先に行い、ドキュメントはコードに合わせて更新する

# study_supportAI

授業プリント・スライド（PDF / HEIC / JPEG）や過去問を **OCR** で取り込み、
OpenAI 互換 API（OpenRouter 等）の LLM を使って **予想問題・クイズ・
忘却曲線（FSRS）ベースのフラッシュカード** を生成・学習できる、
セルフホスト前提の学習支援 Web アプリです。操作はすべてブラウザ上で完結します。

## 主な機能

- **教材取り込み / OCR**: PDF・JPEG・PNG・HEIC をアップロードすると、
  vision 対応 LLM が構造を保った Markdown（数式は LaTeX）に文字起こし。
  ページごとに画像とテキストを並べて確認・手修正でき、失敗ページは個別に再 OCR。
- **フラッシュカード（Anki 風 + FSRS）**: 教材からカードを自動生成し、
  取捨選択してデッキへ追加。復習は Again / Hard / Good / Easy の 4 段階で、
  各ボタンに次回間隔を予測表示。忘却曲線は現行 Anki と同じ **FSRS** で計算。
  - **途中再開**: 評価のたびにサーバー DB へ即保存し、キューも毎回サーバー側で
    再計算するため、途中でブラウザを閉じても・別端末からでも続きから再開できます。
- **クイズ**: 選択式・正誤・短答を自動生成。選択式/正誤は自動採点、短答は LLM 判定。
  1 問ごとに解答を保存するので、中断しても続きから解けます。
- **予想問題**: 過去問・資料の傾向を踏まえた試験形式の問題を模範解答つきで生成。
  追加指示による改訂（チャット的な履歴）と、印刷 / PDF 出力に対応。

## 技術構成

| 層 | 技術 |
|---|---|
| バックエンド | Python 3.12 / FastAPI / SQLAlchemy + SQLite |
| ファイル変換 | pypdfium2（PDF）/ pillow-heif + Pillow（HEIC・画像） |
| OCR・生成 | OpenAI SDK（base_url 差し替えで OpenAI 互換 API に接続） |
| 忘却曲線 | fsrs（py-fsrs） |
| フロントエンド | React + TypeScript + Vite + Tailwind CSS + KaTeX |

データ（SQLite DB・アップロード原本・ページ画像）はすべて `./data/` 配下に保存されます。

## セットアップ

### Docker Compose（推奨）

```bash
cp .env.example .env      # LLM 接続情報を編集（後から画面でも変更可）
docker compose up --build
```

ブラウザで <http://localhost:8000> を開きます。

まず外部 API なしで動作を確認したい場合は、モックモードで起動できます:

```bash
LLM_MOCK=1 docker compose up --build
```

### ローカル実行（開発）

```bash
# バックエンド
cd backend
pip install -r requirements.txt
DATA_DIR=../data uvicorn app.main:app --reload --port 8000

# フロントエンド（別ターミナル、開発サーバは /api を 8000 にプロキシ）
cd frontend
npm install
npm run dev        # http://localhost:5173
```

本番相当で 1 プロセスに固めるには、フロントをビルドして配信ディレクトリへ置きます:

```bash
cd frontend && npm run build
cp -r dist ../backend/frontend_dist
cd ../backend && uvicorn app.main:app --port 8000   # http://localhost:8000
```

## LLM の設定

起動後、画面右下の **設定** から接続先を設定します（`.env` の値が初期値）。

- **ベース URL**: 例 OpenRouter は `https://openrouter.ai/api/v1`
- **API キー**: 各プロバイダのキー
- **Vision モデル**: OCR 用の画像対応モデル（例 `google/gemini-2.5-flash`）
- **テキストモデル**: 問題・カード生成用（例 `google/gemini-2.5-flash`）

「接続テスト」で `/models` を取得し、疎通を確認できます。

> **認証について**: このアプリ自体にログイン機能はありません。自宅 LAN など
> クローズドな環境での利用を想定しています。外部公開する場合はリバースプロキシ等で
> 保護してください。

## 開発・テスト

```bash
# バックエンドのテスト（モック LLM で全機能を統合テスト）
cd backend && python -m pytest

# フロントエンドの型チェック + ビルド
cd frontend && npm run build
```

## ディレクトリ

```
backend/app/        FastAPI アプリ（routers/ に各 API）
frontend/src/       React（pages/ に各画面, components/ に共通部品）
data/               SQLite DB・アップロード・ページ画像（git 管理外）
Dockerfile          フロントをビルドしてバックエンドで配信する 2 段ビルド
docker-compose.yml  ボリューム・環境変数つきの起動定義
```

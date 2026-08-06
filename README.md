# D-chan

D-chan は、D最適化などの基準を用いて実験計画の候補点を生成するツールです。FastAPIによるAPIと、React／ViteによるWeb画面を提供します。

## 動作環境

- Python 3.11 または 3.12
- Node.js と npm
- Windowsでまとめて起動する場合はPowerShellが利用可能であること

プロジェクトの既定Pythonバージョンは `.python-version` で3.12に設定しています。

## Python環境のセットアップ

依存関係は `pyproject.toml` で管理しています。

### uvを使う場合（推奨）

```bash
uv sync --extra dev
```

### venvとpipを使う場合

Windowsでは次のように環境を作成できます。

```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

ランタイム依存関係のみ必要な場合は、従来どおり次のコマンドも利用できます。`requirements.txt` は `pyproject.toml` を参照します。

```bash
pip install -r requirements.txt
```

## Reactフロントエンドのセットアップ

```bash
cd frontend
npm install
```

APIのURLを手動で設定する場合は、`frontend/.env.example` を `.env.local` にコピーして `VITE_API_URL` を変更します。

## WindowsでWebアプリをまとめて起動

リポジトリ直下の `start_web.bat` をダブルクリックすると、FastAPIとReactフロントエンドを別ウィンドウで起動できます。

- FastAPI: `http://127.0.0.1:8000`
- APIドキュメント: `http://127.0.0.1:8000/docs`
- React: `http://localhost:5173`
- Health check: `http://127.0.0.1:8000/health`

ランチャーはFastAPIの起動完了を最大60秒待ってからReactを起動します。`frontend/node_modules` がない場合は `npm install` を自動実行します。

Pythonコマンドは次の順序で選択します。

1. リポジトリ直下の `.venv\Scripts\python.exe`
2. `uv run python`
3. Windows Python Launcherの `py -3`
4. PATH上の `python`

## 個別に起動する場合

### FastAPI

```bash
uv run python -m uvicorn application.main:app --reload --host 127.0.0.1 --port 8000
```

実験計画の候補点は `POST /optimal-design/candidate` で生成します。

### Reactフロントエンド

APIを起動した状態で、別のターミナルから次を実行します。

```bash
cd frontend
npm run dev
```

`http://localhost:5173` で因子の設定、候補点の生成、結果のCSV保存ができます。

## テストと静的チェック

バックエンド:

```bash
uv run pytest
uv run ruff check application tests
```

フロントエンド:

```bash
cd frontend
npm run lint
npm run build
```

Pull Requestでは `.github/workflows/ci.yml` により、Python 3.11／3.12のAPIテストと、フロントエンドのLint／Buildを実行します。

## 主な設定ファイル

- `pyproject.toml`: Pythonパッケージ、依存関係、pytest、coverage、Ruffの設定
- `.python-version`: uvなどが使用する既定Pythonバージョン
- `.editorconfig`: 文字コード、改行、インデントの共通設定
- `.gitignore`: Python、仮想環境、フロントエンド生成物の除外設定
- `frontend/.env.example`: フロントエンドのAPI接続先設定例
- `.github/workflows/ci.yml`: バックエンドとフロントエンドのCI

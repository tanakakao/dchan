# D-chan

D-chan は、D最適化などの基準を用いて実験計画の候補点を生成するツールです。FastAPIによるAPIと、React／ViteによるWeb画面を提供します。

## 動作環境

- Python 3.11 または 3.12
- Node.js 22以上
- pnpm 11（`frontend/package.json` の `packageManager` でバージョンを固定）
- Windowsでまとめて起動する場合はPowerShellが利用可能であること

プロジェクトの既定Pythonバージョンは `.python-version` で3.12に設定しています。

## 使用ポート

bochan、malchan、cauchanとの競合を避けるため、dchanでは次の専用ポートを使用します。

| アプリ | Backend | Frontend |
| --- | ---: | ---: |
| bochan | 8000 | 5173 |
| malchan | 8001 | 5174 |
| cauchan | — | 5175 |
| dchan | 8002 | 5176 |

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

Windowsでpnpmが未導入の場合は、Node.js 22以上を導入した後に次を実行します。

```bash
npx get-pnpm
pnpm --version
```

`winget` を使う場合は `winget install -e --id pnpm.pnpm` でも導入できます。

依存関係はlockfileを使ってインストールします。

```bash
cd frontend
pnpm install --frozen-lockfile
```

APIのURLを手動で設定する場合は、`frontend/.env.example` を `.env.local` にコピーして `VITE_API_URL` を変更します。

## WindowsでWebアプリをまとめて起動

リポジトリ直下の `start_web.bat` をダブルクリックすると、FastAPIとReactフロントエンドを別ウィンドウで起動します。

- FastAPI: `http://127.0.0.1:8002`
- APIドキュメント: `http://127.0.0.1:8002/docs`
- React: `http://127.0.0.1:5176`
- Health check: `http://127.0.0.1:8002/health`

ランチャーは次の順序で処理します。

1. Python、pnpm、必要なPythonパッケージを確認
2. 8002番と5176番ポートが空いていることを確認
3. FastAPIを起動し、`/health` の応答を待機
4. React／Viteを起動し、画面のHTTP応答を待機
5. 起動成功後、`http://127.0.0.1:5176` を既定ブラウザで自動的に開く

`frontend/node_modules/.pnpm` がない場合は `pnpm install --frozen-lockfile` を自動実行します。npm由来の既存 `node_modules` があっても、pnpm管理でなければ再インストールされるため、手動削除は不要です。起動に失敗した場合は、バックエンドまたはフロントエンドのコマンドウィンドウにエラーを残します。

Pythonコマンドは次の順序で選択します。

1. リポジトリ直下の `.venv\Scripts\python.exe`
2. `uv run python`
3. Windows Python Launcherの `py -3`
4. PATH上の `python`

## 個別に起動する場合

### FastAPI

```bash
uv run python -m uvicorn application.main:app --reload --host 127.0.0.1 --port 8002
```

実験計画の候補点は `POST /optimal-design/candidate` で生成します。

### Reactフロントエンド

APIを起動した状態で、別のターミナルから次を実行します。

```bash
cd frontend
pnpm run dev
```

Viteの既定URLは `http://127.0.0.1:5176` です。因子の設定、候補点の生成、結果のCSV保存ができます。

## テストと静的チェック

バックエンド:

```bash
uv run pytest
uv run ruff check application tests
```

フロントエンド:

```bash
cd frontend
pnpm run lint
pnpm run build
```

Pull Requestでは `.github/workflows/ci.yml` により、Python 3.11／3.12のAPIテストと、フロントエンドのLint／Buildを実行します。

## 主な設定ファイル

- `pyproject.toml`: Pythonパッケージ、依存関係、pytest、coverage、Ruffの設定
- `.python-version`: uvなどが使用する既定Pythonバージョン
- `.editorconfig`: 文字コード、改行、インデントの共通設定
- `.gitignore`: Python、仮想環境、フロントエンド生成物の除外設定
- `frontend/.env.example`: フロントエンドのAPI接続先設定例
- `frontend/package.json`: フロントエンド依存関係とpnpmバージョン
- `frontend/pnpm-lock.yaml`: フロントエンド依存関係のlockfile
- `frontend/pnpm-workspace.yaml`: pnpm workspaceと依存パッケージbuild policy
- `.github/workflows/ci.yml`: バックエンドとフロントエンドのCI

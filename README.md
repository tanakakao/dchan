# ベイズ最適化ツール

このプロジェクトは、D最適化などによる実験計画法を行うためのツールを提供します。

## 概要

このツールは、以下の目的で使用します：
- 実験計画点の算出

より少ない回数で効果的な実験を行うための候補点を算出します。

## インストール方法

依存関係をインストールするには、以下のコマンドを実行してください。

```bash
pip install -r requirements.txt
```

React フロントエンドの依存関係は次のコマンドでインストールします。

```bash
cd frontend
npm install
```

## Windows で Web アプリをまとめて起動

リポジトリ直下の `start_web.bat` をダブルクリックすると、FastAPI と React フロントエンドを別ウィンドウで起動できます。

- FastAPI: `http://127.0.0.1:8000`
- React: `http://localhost:5173`
- Health check: `http://127.0.0.1:8000/health`

ランチャーは FastAPI の起動完了を最大 60 秒待ってから React を起動します。`frontend/node_modules` がない場合は `npm install` を自動実行します。

Python はリポジトリ直下の `.venv` を優先し、存在しない場合は Windows の `py -3` または `python` を使用します。必要な Python パッケージがない場合は、表示されたコマンドで `requirements.txt` をインストールしてください。

## FastAPI の起動

```bash
uvicorn application.main:app --host 0.0.0.0 --port 8000
```

起動後は `http://localhost:8000/docs` から API の仕様確認と実行ができます。
実験計画の候補点は `POST /optimal-design/candidate` で生成します。

## React フロントエンドの起動

API を起動した状態で、別のターミナルから次を実行します。

```bash
cd frontend
npm run dev
```

`http://localhost:5173` で因子の設定、候補点の生成、結果の CSV 保存ができます。API の URL を変更する場合は `VITE_API_URL` 環境変数を指定してください。

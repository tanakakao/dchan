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

## FastAPI の起動

```bash
uvicorn application.main:app --host 0.0.0.0 --port 8000
```

起動後は `http://localhost:8000/docs` から API の仕様確認と実行ができます。
実験計画の候補点は `POST /optimal-design/candidate` で生成します。

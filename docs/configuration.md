# 設定リファレンス（環境変数）

最終更新: 2026-07-06（masterブランチ基準）

設定は `src/asobann/config_common.py` + 環境別ファイル（`config_dev.py` / `config_production.py` / `config_test.py`）で読み込まれる。
どのファイルが読まれるかは **`FLASK_ENV`** で決まる（`test` / `production` / それ以外→dev）。

> 注意: `app.config["ENV"]`（=FLASK_ENV）はFlask 2.3で廃止されたAPI。slowness_issueブランチでは独自の `ASOBANN_ENV` に置き換えられている。マージ時はデプロイ側（asobann_deploy）が渡す環境変数と必ず整合させること（未設定だとdevelopment扱いになり、本番でCORS全開+debugエンドポイント有効という事故になる）。

## 必須（環境による）

| 環境変数 | dev | production | 説明 |
|---|---|---|---|
| `FLASK_ENV` | 任意 | `production` を明示 | 環境選択 |
| `MONGODB_URI` | 省略可（localhost:27017/ex2dev） | **必須**。`retryWrites=false` が自動付与される | MongoDB接続文字列。`mongodb+srv://` 可 |
| `PUBLIC_HOSTNAME` | 省略可（localhost:5000） | **必須** | `https://<値>` がBASE_URLになり、socket.ioのCORS許可オリジンに使われる（devは`*`） |
| `GOOGLE_ANALYTICS_ID` | 省略可 | **必須**（不要なら`NotAvailable`等のダミー） | GAタグ |

## 任意

| 環境変数 | デフォルト | 説明 |
|---|---|---|
| `REDIS_URI` | なし（メッセージキューなし） | 複数プロセス時のsocket.ioメッセージキュー。`redis+srv://`（SRVレコード解決）対応 |
| `UPLOADED_IMAGE_STORE` | `local` | `local`（/tmp/asobann/images）or `s3` |
| `AWS_KEY` / `AWS_SECRET` / `AWS_REGION` / `AWS_S3_IMAGE_BUCKET_NAME` | — | `UPLOADED_IMAGE_STORE=s3` のとき必須 |
| `AWS_COGNITO_USER_POOL_ID` / `AWS_COGNITO_CLIENT_ID` | なし | 設定すると `/config` がクライアントへ返す（認証機能は未完成） |
| `ASOBANN_ACCESS_LOG` | 未設定=off | 設定するとアクセスログ出力（productionは常にon） |

## デバッグ用（dev/testのみ）

| 環境変数 | 説明 |
|---|---|
| `ASOBANN_DEBUG_OPTS` | カンマ区切り。`PERFORMANCE_RECORDING`（トレースをmongoのtracesへ記録、/debug/tracesで閲覧）、`ORDER_OF_UPDATES`（更新順ログ）、`LOG`（socketio詳細ログ） |
| `ASOBANN_DEBUG_HANDLER_WAIT` | `come by table` 処理に指定秒のsleepを入れる（遅延の再現用） |

## ハードコードされている値（要注意）

| 場所 | 値 | 問題 |
|---|---|---|
| `app/__init__.py` | `SECRET_KEY='secret!'` | 全環境で固定。要環境変数化 |
| `config_test.py` | `mongodb://admin:password@mongo:27017/test` | 環境変数分岐の直後に無条件上書きしており、test環境のMONGODB_URIは実質固定 |
| `config_test.py` | `PORT = 10011` | テストサーバのポート |

## ローカル開発（docker compose）で設定される値

`deploy/localdev/docker-compose.yml` が app_1〜3 に `MONGODB_URI=mongodb://admin:password@mongo:27017` と `REDIS_URI=redis://redis:6379` を設定する。ポートは 8000/8001/8002 → コンテナ5000。

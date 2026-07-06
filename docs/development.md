# 開発ガイド

最終更新: 2026-07-06（masterブランチ基準）

## セットアップ

必要なもの: Python（Pipfile準拠）、pipenv、Node.js、Docker。e2eテストにはFirefox + geckodriver。

```shell
npm i -d            # JS依存
pipenv sync --dev   # Python依存
npx webpack         # フロントエンドビルド（src/js → src/asobann/app/static/main.js）
```

JSを変更したら `npx webpack` の再実行が必要（watchモード: `npx webpack --watch`）。

## ローカル起動

```shell
docker compose -f deploy/localdev/docker-compose.yml up --build
```

- http://localhost:8000/ でアクセス。app_1〜app_3 の3プロセス + mongo + redis が起動する（複数プロセスでの同期挙動を確認できる）
- ソースはボリュームマウントされるが、**Pythonプロセスの自動リロードはない**。サーバコード変更時はコンテナ再起動が必要

## テスト

### 種類と場所

| 種類 | 場所 | 前提 | 内容 |
|---|---|---|---|
| unit (JS) | tests/unit/*.test.js | なし（jsdom） | 更新キュー（Level A/B/C）、送信バッファ等。`npm test` |
| unit (Python) | tests/unit/*.py | **一部は実MongoDBが必要**（store/test_tables.py） | 設定、store層 |
| functional | tests/functional/ | MongoDB + テストサーバ（conftestが自動起動） | HTTPエンドポイント |
| api | tests/api/ | 同上 | キットアップロードAPI |
| e2e | tests/e2e/ | 同上 + Firefox/geckodriver | Seleniumでの実ブラウザ操作。2ブラウザ同期検証を含む |
| performance | tests/performance/ | 対象サーバ | 負荷計測フレームワーク（pytestではなくcli.pyから実行） |

### 実行

```shell
npm test                                   # JS unit
pipenv run pytest -m quick                 # 高速なテストのみ（@pytest.mark.quick）
pipenv run pytest tests/unit tests/functional
pipenv run pytest tests/e2e                # 重い。Firefox+geckodriverが必要
pipenv run pytest tests/path/to/test.py::test_name -v   # 単一テスト
```

- Pythonテストは `tests/conftest.py` の `TestServerProvider` がテストサーバ（port 10011）を都度起動する。**pipenvのパスが `/usr/local/bin/pipenv` にハードコードされている**点に注意（環境が違うと失敗する）
- e2eはgeckodriverがPATHにあること。`tests/geckodriver.example` 参照
- コンテナ内でテストを回す仕組みは `tests/entry_for_test_container.sh`（slowness_issueブランチ）を参照

### 性能計測（tests/performance/）

slowness問題の再現・計測に使う。シナリオ例: `move_single_card_each.py`（複数プレイヤーが各自カードを動かす）、`move_stack_of_cards.py` など。`cli.py` がエントリポイントで、`remote_runner.py` によりリモートホストでの分散実行もできる。

## ディレクトリ早見

```
src/asobann/       # Pythonバックエンド（→ docs/architecture.md）
src/js/            # フロントエンド（webpackでバンドル）
src/asobann/app/static/main.js   # webpackの出力（コミットしない・直接編集しない）
deploy/localdev/   # ローカル用docker compose
scripts/           # 補助スクリプト
tests/             # 上記テスト群
```

## コーディング規約

- Python: PEP 8、型アノテーション推奨、snake_case / PascalCase
- JavaScript: ES6+、camelCase / PascalCase
- テストには適切なマーク（例: `@pytest.mark.quick`）を付ける

## 落とし穴メモ

- feats配列の先頭は必ず `basic`（feat.js）。feat間に暗黙の依存があるため、featの追加・変更時は architecture.md の「featシステム」を先に読むこと
- `table.data` がサーバ状態、`component.*` はビュー状態のキャッシュ。receiveDataで受信した `data` を書き換えないこと
- socket.ioまわりのバージョンはサーバ（python-socketio）とクライアント（socket.io-client）の互換表を確認してから上げること

# asobann アーキテクチャ概要

最終更新: 2026-07-06（masterブランチのコードに基づく）

## 全体像

```
ブラウザ (複数)                        サーバ (複数プロセス可)
┌──────────────────────┐   socket.io   ┌──────────────────────────┐
│ play_session.js      │◄─────────────►│ Flask + Flask-SocketIO   │
│  ├ table.js (表示)    │   HTTP        │  (eventlet)              │
│  ├ feat.js (能力)     │◄─────────────►│  ├ blueprints/ (API)     │
│  ├ sync_table.js     │               │  └ store/ (永続化)        │
│  └ menu.js ほか       │               └────────┬────────┬────────┘
└──────────────────────┘                        │        │
                                          MongoDB      Redis
                                        (テーブル状態)  (プロセス間pubsub)
```

- 1つの「テーブル」（ゲーム卓）にプレイヤーがURL共有で集まり、socket.ioのroom単位で状態を同期する
- テーブル状態はMongoDBに **1テーブル=1ドキュメント** で保存される
- サーバプロセスが複数ある場合、Flask-SocketIOのmessage queue（Redis）でブロードキャストを中継する

## バックエンド構成（src/asobann/）

| モジュール | 責務 |
|---|---|
| `app/__init__.py` | アプリファクトリ（create_app）。設定読み込み、Mongo/Redis接続、画像アップローダ選択 |
| `app/blueprints/table.py` | socket.ioイベントハンドラ（同期の中心）とテーブル関連HTTP |
| `app/blueprints/kit.py` | キット一覧・取得・アップロード（POST /kits/create） |
| `app/blueprints/component.py` | キットに属するコンポーネント定義の取得 |
| `app/blueprints/debug.py` | デバッグ用（development/test環境のみ登録） |
| `store/tables.py, kits.py, components.py` | MongoDBアクセス層。`connect(mongo)` でコレクション参照をモジュールグローバルに設定 |
| `config_common/dev/production/test.py` | 環境別設定。環境変数から読む（→ configuration.md） |
| `deploy.py` | 初期データ（kit/コンポーネント定義）の投入 |
| `wsgi.py` | エントリポイント |

### データモデル（MongoDBコレクション）

| コレクション | 内容 |
|---|---|
| `tables` | `{tablename, table: {components: {componentId: {...}}, kits: [...], players: {...}}}` |
| `table_metas` | `{tablename, created_at, updated_at}` |
| `kits` | `{kit: {name, ...}, version}` — キット定義（ゲームのテンプレート） |
| `components` | `{component: {name, ...}}` — コンポーネント定義（キットが参照） |
| `traces` | デバッグ用パフォーマンストレース（DEBUG_PERFORMANCE_RECORDING時のみ） |

「kit/component定義」はカタログ（テンプレート）で、テーブルに追加するとインスタンス（componentId付与）が `tables` 内にコピーされる。

## フロントエンド構成（src/js/）

| モジュール | 責務 |
|---|---|
| `play_session.js` | エントリポイント。全体の組み立て、kit追加のレイアウト、プレイヤー状態（sessionStorage） |
| `table.js` | 表示モデル。`Table`（全体）と `Component`（個々の部品）、更新キュー（QueueForUpdatingView） |
| `feat.js` | **featシステム**（後述）。基本描画+ 標準featを含む |
| `feats/*.js` | 追加feat（counter, glued, overlaid_controls） |
| `sync_table.js` | socket.io通信層。送信バッファ（75ms間隔で `update many components` にまとめる） |
| `menu.js` | 画面右のメニューUI |
| `craft_box.js` | テーブル上でキットを自作する機能 |
| `cardistry.js` | カード束の一括操作（spread out / collect / shuffle / flip all等） |
| `i18n.js` / `names.js` | 日英切替（`_()` と `プロパティ名_ja` 規約）/ プレイヤー名の候補 |
| `dev_inspector.js` | パフォーマンストレース送信（デバッグ設定時のみ有効化） |

### featシステム

コンポーネントの「能力」をプラグインとして追加する仕組み。各featは次のインターフェースを持つ（feat.jsロード時にassertで検査される）:

```js
const myFeat = {
    install(component, data) {},    // Component生成時に1回。DOM/リスナー設置
    isEnabled(component, data) {},  // このコンポーネントで有効か（dataのプロパティで判定）
    receiveData(component, data) {},// サーバ状態(data)をビュー状態(component.*)へ反映
    updateView(component, data) {}, // DOMへ反映
    uninstall(component) {},        // Component削除時
};
addFeat(myFeat);  // feats/counter.js 等を参照
```

- 標準feat: `basic`（描画の基本。**必ずfeats配列の先頭**）, `within`（内包判定）, `draggability`, `flippability`, `resizability`, `rollability`（ダイス）, `traylike`（トレイ: 上に載せたものが一緒に動く）, `handArea`（手札エリア）, `ownership`（手札の所有）, `touchToRaise`（クリックで最前面）, `stowage`, `cardistry`
- feat間の連携は `featsContext.addEventListener / fireEvent` のコンポーネント単位イベントで行う（例: `within` の内包開始/終了イベントを `traylike` と `ownership` が購読）
- 注意: feat間には暗黙の順序・相互依存がある（basicが先頭必須、flippabilityとrollabilityのdblclick競合など）。変更時は既存featの挙動確認が必要

### 更新レベル（QueueForUpdatingView / Level A/B/C）

ユーザー操作からのビュー更新を3レベルで制御する（table.js）:

- **Level A**: 即時反映（例: ドラッグ中の自分の操作）
- **Level B**: トップレベルなら即時、ネスト中は合流キューへ
- **Level C**: 合流キュー行き。50ms間隔でまとめて描画（例: within判定などの連鎖更新）

`component.applyUserAction(Level.X, () => {...})` で囲んだ処理の中の `propagate()` がこの制御を受ける。この機構は `tests/unit/table.test.js` にテストがある。

## 同期の流れ

詳細は [sync-protocol.md](sync-protocol.md)。要点:

1. 操作 → featが `component.propagate(diff)` → sync_table.jsの送信バッファへ
2. 75msごとに `update many components` としてサーバへ送信
3. サーバはMongoDBを更新し、同じroomの全クライアントへブロードキャスト
4. 受信側は自分発（originator）を無視し、diffを適用して該当コンポーネントのみ再描画

競合解決はlast-write-wins（クライアント時計の `lastUpdated.epoch` 比較）で、サーバは基本的に検証しないパススルー。

## 既知の設計上の課題

- テーブル全体の読み書きを行うサーバイベントが残っており、テーブル肥大で遅くなる（詳細: devenvの issues.20260706.md §2, §10）
- 揮発データ（マウスカーソル）と永続データが同じ経路を通る
- `players` から退室者が削除されない（disconnectハンドラなし）

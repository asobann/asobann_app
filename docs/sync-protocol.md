# 同期プロトコル仕様（現状）

最終更新: 2026-07-06（masterブランチのコードから逆引きで文書化）

socket.io（デフォルト設定: polling→websocketアップグレード）で、テーブル名をroomとして同期する。
本書は「現状の仕様」の記録であり、既知の問題点は末尾にまとめる。

## 識別子

- `tablename`: URLパスから取得（`/tables/<tablename>`）。**アクセス制御はこれを知っているかどうかのみ**
- `originator` / `client_connection_id`: クライアントが起動時に生成する12桁hexランダム値。自分発のブロードキャストを無視するために使う
- `componentId`: コンポーネント追加時にクライアントが生成する12桁hex
- `lastUpdated: {from: <connection_id>, epoch: <Date.now()>}`: 競合解決用。クライアント時計に基づくlast-write-wins

## クライアント → サーバ

| イベント | ペイロード | サーバの処理 |
|---|---|---|
| `come by table` | `{tablename}` | テーブルをget（なければ default_table.json から作成）、roomにjoin、送信者に `load table` を返す。**connect/再接続のたびに送られる** |
| `set player name` | `{tablename, player: {name, isHost}}` | `table.players[name]` に登録して全体保存。送信者に `confirmed player name` |
| `update single component` | `{tablename, originator, componentId, diff, volatile}` | volatileでなければテーブル全体を読み→diff適用→**全体書き戻し**。roomへそのまま再配信 |
| `update many components` | `{tablename, originator, diffs: [{componentId: diff}], componentIdsToRemove: []}` | 部分`$set`で更新、削除は全体読み書き。roomへそのまま再配信。**通常の操作はほぼ全部この経路**（75msバッファ経由） |
| `add component` | `{tablename, originator, component}` | テーブル全体読み→追加→全体書き戻し。roomへ `add component` |
| `add kit` | `{tablename, originator, kitData: {kit}, newComponents}` | `$push` + 部分`$set`。roomへ `add kit` |
| `remove component` | `{tablename, originator, componentId}` | 全体読み書き。roomへ **`refresh table`（テーブル全量）** |
| `remove kit` | `{tablename, originator, kitId}` | 全体読み書き。roomへ **`refresh table`（テーブル全量）** |
| `sync with me` | `{tablename, originator, tableData}` | **クライアントから送られたテーブル全体で上書き保存**。roomへ `refresh table`。クライアントのkit削除（removeKit）が使用 |
| `mouse movement` | `{tablename, playerName, mouseMovement: {mouseOnTableX, mouseOnTableY, mouseButtons}}` | 保存せずroomへそのまま再配信。**間引きなし（mousemoveイベントの頻度そのまま）** |

## サーバ → クライアント

| イベント | ペイロード | クライアントの処理 |
|---|---|---|
| `load table` | テーブル全体 | 初期化。players空なら自分がhostとしてjoin |
| `confirmed player name` | `{player: {name}}` | sessionStorageへ保存 |
| `update single component` | 送信ペイロードそのまま | originatorが自分なら無視。`lastUpdated` が古い更新は破棄。該当コンポーネント再描画（※現状は全体 `table.update()`） |
| `update many components` | 送信ペイロードそのまま | originatorが自分なら無視。diff適用+削除適用 |
| `add component` / `add kit` | 同上 | 追加を適用（add kitはoriginator自分なら無視） |
| `refresh table` | `{tablename, table}` | **テーブル全体を差し替え再描画** |
| `mouse movement` | 送信ペイロードそのまま | 他プレイヤーのカーソル表示を移動（自分のplayerNameなら無視） |

## クライアント側の送信制御（sync_table.js）

- コンポーネント更新は直接emitせず `ComponentUpdateBuffer` に蓄積し、**75ms間隔**で `update many components` 1通にまとめる。同一コンポーネントへの連続diffはマージされる（最新値のみ送る）
- `volatile: true` の更新（ドラッグ中の位置など）はサーバで保存されない（配信のみ）
- マウスカーソルはバッファを通らず即時emit（間引きなし）

## 権威と競合解決

- サーバは検証しないパススルー。**権威はクライアント側**にあり、`lastUpdated.epoch`（クライアント時計）のlast-write-winsで競合を解決する
- カードの裏表・手札の所有もすべて全クライアントにデータとして届く。手札が見えないのは表示制御のみ（データは取得可能）

## 既知の問題点（変更時の参考）

詳細は devenv の issues.20260706.md §2, §10 を参照。

1. `update single component` / `add,remove component` / `remove kit` はテーブル全体の読み書き — テーブル肥大で遅くなる主因候補
2. `mouse movement` が無間引き・送信者含む全員再配信 — 人数の2乗でメッセージが増える
3. `refresh table` / `sync with me` の全量転送
4. disconnectハンドラがなく `players` に退室者が残る
5. 競合解決がクライアント時計依存（時計ズレで更新破棄・巻き戻りが起きうる）
6. 順序保証・ack・再送なし

プロトコルを再設計する場合は、揮発チャネル（カーソル・ドラッグ中位置）と永続チャネル（確定状態）の分離、コンポーネント単位の粒度、サーバ採番のシーケンス番号を軸にする（issues.20260706.md §10.3）。

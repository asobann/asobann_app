# 同期プロトコル仕様（現状）

最終更新: 2026-08-13（lastUpdated撤去後のmasterブランチから逆引きで文書化）

socket.io（デフォルト設定: polling→websocketアップグレード）で、テーブル名をroomとして同期する。
本書は「現状の仕様」の記録であり、既知の問題点は末尾にまとめる。

## 識別子

- `tablename`: URLパスから取得（`/tables/<tablename>`）。**アクセス制御はこれを知っているかどうかのみ**
- `originator` / `client_connection_id`: クライアントが起動時に生成する12桁hexランダム値。自分発のブロードキャストを無視するために使う
- `componentId`: コンポーネント追加時にクライアントが生成する12桁hex

## クライアント → サーバ

| イベント | ペイロード | サーバの処理 |
|---|---|---|
| `come by table` | `{tablename}` | テーブルをget（なければ default_table.json から作成）、roomにjoin、送信者に `load table` を返す。**connect/再接続のたびに送られる** |
| `set player name` | `{tablename, player: {name, isHost}}` | `table.players[name]` に登録して全体保存。送信者に `confirmed player name` |
| `update many components` | `{tablename, originator, diffs: [{componentId: diff}], componentIdsToRemove: [], volatileKeys: {componentId: [key, ...]}}` | `volatileKeys` に列挙されたキーを除いて部分`$set`で更新（配信は`diffs`全体をそのまま）。削除は全体読み書き。roomへそのまま再配信。**通常のコンポーネント更新はこの経路**（75msバッファ経由）。新規追加は `add component` / `add kit` が別経路 |
| `add component` | `{tablename, originator, component}` | テーブル全体読み→追加→全体書き戻し。roomへ `add component` |
| `add kit` | `{tablename, originator, kitData: {kit}, newComponents}` | `$push` + 部分`$set`。roomへ `add kit` |
| `sync with me` | `{tablename, originator, tableData}` | **クライアントから送られたテーブル全体で上書き保存**。roomへ `refresh table`。クライアントのkit削除（removeKit）が使用 |
| `mouse movement` | `{tablename, playerName, mouseMovement: {mouseOnTableX, mouseOnTableY, mouseButtons}}` | 保存せずroomへそのまま再配信。**間引きなし（mousemoveイベントの頻度そのまま）** |

## サーバ → クライアント

| イベント | ペイロード | クライアントの処理 |
|---|---|---|
| `load table` | テーブル全体 | 初期化。players空なら自分がhostとしてjoin |
| `confirmed player name` | `{player: {name}}` | sessionStorageへ保存 |
| `update many components` | 送信ペイロードそのまま | originatorが自分なら無視。diff適用+削除適用。**新旧比較は無い**（到着順そのまま適用） |
| `add component` / `add kit` | 同上 | 追加を適用（add kitはoriginator自分なら無視） |
| `refresh table` | `{tablename, table}` | **テーブル全体を差し替え再描画** |
| `mouse movement` | 送信ペイロードそのまま | 他プレイヤーのカーソル表示を移動（自分のplayerNameなら無視） |

## クライアント側の送信制御（sync_table.js）

- コンポーネント更新は直接emitせず `ComponentUpdateBuffer` に蓄積し、**75ms間隔**で `update many components` 1通にまとめる。同一コンポーネントへの連続diffはマージされる（最新値のみ送る）
- マウスカーソルはバッファを通らず即時emit（間引きなし）
- `pushComponentUpdate()` の第4引数 `volatile`（ドラッグ中の位置など）が `true` のdiffで書き込まれたキーは、同じ75ms窓内で非volatileな書き込みが無ければ `volatileKeys` に載り、サーバでの保存対象から外れる（配信は従来どおり全キー）。窓内で同じキーに非volatile更新（ドロップ確定など）が1回でもあれば、順序に関わらずそのキーは保存される

## 権威と競合解決

- サーバは検証しないパススルー。**権威はクライアント側**にあり、サーバはテーブル状態をメモリに保持しない
- 競合解決は無い。同じフィールドへの更新は事実上「サーバに最後に届いた方が勝つ」（到着順）。かつてクライアント時計ベースの `lastUpdated`（`from`/`epoch`）による新旧比較があったが、実際には受信側で使われないまま放置されていたため撤去した。同一送信者からの更新が受信側で順序逆転するケースに対する保険がない状態
- カードの裏表・手札の所有もすべて全クライアントにデータとして届く。手札が見えないのは表示制御のみ（データは取得可能）

## 既知の問題点（変更時の参考）

1. `add component` / `set player name` / `sync with me` はテーブル全体の読み書き — read-modify-writeなので並行更新でロストアップデートが起きる。`update many components` はコンポーネント単位の `$set` で並行安全
2. `mouse movement` が無間引き・送信者含む全員再配信 — 人数の2乗でメッセージが増える
3. `refresh table`（`sync with me` の応答）の全量転送。kit削除がこの経路を使う
4. disconnectハンドラがなく `players` に退室者が残る
5. 競合解決・新旧比較が無い（上記）。同一送信者からの更新の順序逆転にも保険がない
6. `update_components()` が更新のたびにテーブル全体を1回読む（存在しないcomponentIdへの`$set`を避けるためだけ）
7. 順序保証・ack・再送なし

プロトコルを再設計する場合は、揮発チャネル（カーソル・ドラッグ中位置）と永続チャネル（確定状態）の分離、コンポーネント単位の粒度、サーバ採番のシーケンス番号を軸にする。

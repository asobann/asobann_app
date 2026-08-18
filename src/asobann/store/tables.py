import random
import json
from pathlib import Path
import datetime

tables = None
table_metas = None


def generate_new_tablename():
    return str(random.randint(0, 9999)) + ''.join([random.choice('abddefghijklmnopqrstuvwxyz') for i in range(3)])


async def get(tablename):
    data = await tables.find_one({"tablename": tablename})
    if not data:
        return None
    return data["table"]


async def create(tablename, prepared_table):
    if prepared_table is None:
        with open(str(Path(__file__).parent / "./default_table.json")) as f:
            table = json.load(f)
    elif prepared_table == '0':
        table = {'components': {}, 'kits': [], 'players': {}}

    await tables.insert_one({"tablename": tablename, "table": table})
    await table_metas.insert_one({"tablename": tablename, "created_at": datetime.datetime.now()})
    return table


async def store(tablename, table):
    table["tablename"] = tablename
    await tables.update_one(
        {"tablename": tablename},
        {"$set": {"table": table}},
        upsert=True)
    await table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


async def purge_all():
    await tables.delete_many({})


async def update_table(tablename, table):
    await tables.update_one({"tablename": tablename}, {"$set": {"table": table}})
    await table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


def connect(mongo_db):
    global tables, table_metas
    tables = mongo_db.tables
    table_metas = mongo_db.table_metas


class TableNotFound(Exception):
    pass


class InvalidComponentId(Exception):
    pass


def validate_component_id(component_id):
    """componentIdがドキュメント内のフィールド名として使える形か検査する。

    このstoreは componentId を `table.components.<id>` というドット記法のパスに
    埋め込む。パスの区切りは '.'、'$' は演算子や式の目印なので、それらを含むIDが
    通ると**意図しないフィールドを書き換えたり消したりできる**。

    '$' は位置を問わず不正とする。「先頭だけ」に緩めると、どこまでが安全かの
    判断が文脈（更新演算子か、集約式か、配列フィルタか）に依存してしまう。
    ID側を狭く保つほうが、後から使い方が増えても破綻しない。

    サニタイズ（黙って直す）はしない。componentIdは「フィールド名として使える
    文字列」であることがシステム全体の約束事であり、破っているのは呼び出し側の
    バグか、外から不正な値が来ているかのどちらか。どちらも黙って続けてはいけない。

    **生成規則そのものは条件にしない。** IDの形は実装の都合で変わりうるもので、
    ここで守るべきはパスの安全性だけ。いま生成しているIDの形（play_session.js の
    generateComponentId は12桁hex）に合わせると、その都合が変わるたびに既存データが
    通らなくなる。現に default_table.json は 'title' / 'usage' を使っている。
    """
    if not isinstance(component_id, str) or not component_id:
        raise InvalidComponentId(repr(component_id))
    if '.' in component_id or '$' in component_id or '\0' in component_id:
        raise InvalidComponentId(repr(component_id))
    return component_id


def _ensure_matched(result, tablename):
    """卓が見つからなかった書き込みを、黙って捨てずに落とす。

    卓全体を読んでから書き戻していた頃は、読んだ時点で存在しない卓が None として
    返り、その後のアクセスで必ず落ちていた。部分更新はフィルタが一致しなくても
    update_one が成功扱いで返るので、放っておくと「クライアントには配信されたのに
    DBには入っていない」状態を無言で作る（リロードで消える）。
    """
    if result.matched_count == 0:
        raise TableNotFound(tablename)


def collect_update_candidates(diff_of_components, volatile_keys):
    candidates = {}
    for diff in diff_of_components:
        for component_id in diff.keys():
            validate_component_id(component_id)
            skip_keys = volatile_keys.get(component_id, [])
            for key, value in diff[component_id].items():
                if key in skip_keys:
                    continue
                candidates.setdefault(component_id, {})[key] = value
    return candidates


def build_modification(candidates, existing_component_ids):
    modification = {}
    for component_id, diff in candidates.items():
        if component_id not in existing_component_ids:
            continue
        for key, value in diff.items():
            modification[f'table.components.{component_id}.{key}'] = value
    return modification


async def update_components(tablename, diff_of_components, volatile_keys=None):
    # volatileだけの更新（ドラッグ中の中間座標など）は、この時点で候補が空になる。
    # 卓の存在チェックのためだけに全文書readするのは、書くものが何も無いときは
    # 意味が無い。書くと決まってから読む。
    candidates = collect_update_candidates(diff_of_components, volatile_keys or {})
    if not candidates:
        return
    current_table = await get(tablename)
    if current_table is None:
        raise TableNotFound(tablename)
    modification = build_modification(candidates, current_table["components"])
    if not modification:
        return
    await tables.update_one({"tablename": tablename}, {"$set": modification})


async def add_new_kit_and_components(tablename, kitData, components):
    modification = {}
    for component_id in components.keys():
        validate_component_id(component_id)
        mod_key = f'table.components.{component_id}'
        modification[mod_key] = components[component_id]

    result = await tables.update_one({"tablename": tablename}, {"$push": {"table.kits": kitData}})
    _ensure_matched(result, tablename)
    if not modification:
        # update_one() will fail if $set is empty
        return
    result = await tables.update_one({"tablename": tablename}, {"$set": modification})
    _ensure_matched(result, tablename)


async def remove_components(tablename, component_ids_to_remove):
    # $unset はコンポーネント単位で消すので、卓を読んで丸ごと書き戻す必要がない。
    # 全体書き戻しだと、その間に届いた他プレイヤーの更新を巻き込んで消していた。
    # 存在しないパスへの $unset はエラーにならないので、事前の存在確認も要らない。
    modification = {f'table.components.{validate_component_id(component_id)}': ''
                    for component_id in component_ids_to_remove}
    if not modification:
        return
    result = await tables.update_one({"tablename": tablename}, {"$unset": modification})
    _ensure_matched(result, tablename)
    await table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})


async def add_component(tablename, component_data):
    component_id = validate_component_id(component_data["componentId"])
    result = await tables.update_one(
        {"tablename": tablename},
        {"$set": {f'table.components.{component_id}': component_data}})
    _ensure_matched(result, tablename)
    await table_metas.update_one(
        {"tablename": tablename},
        {"$set": {"updated_at": datetime.datetime.now()}})

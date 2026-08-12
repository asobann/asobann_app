import asyncio
import json
from codecs import open
from pathlib import Path

import asobann
import asobann.app
import asobann.store
import asobann.store.components
import asobann.store.kits
import asobann.store.tables


async def purge_all():
    for d in [asobann.store.tables, asobann.store.components, asobann.store.kits]:
        await d.purge_all()


async def purge_kits_and_components():
    for d in [asobann.store.components, asobann.store.kits]:
        await d.purge_all()


async def load_default():
    with open(Path(__file__).parent / "./initial_deploy_data.json", encoding='utf-8') as f:
        default_data = json.load(f)
    # purge_all()
    await purge_kits_and_components()
    await asobann.store.components.store_default(default_data["components"])
    await asobann.store.kits.store_default(default_data["kits"])


async def run(cmd):
    # store層を使う前にcreate_app()でDB接続を確立する必要がある。
    app = await asobann.app.create_app()
    try:
        if cmd == 'load_default':
            print("load default ...")
            await load_default()
        elif cmd == 'purge_kits_and_components':
            print("purge kits and components ...")
            await purge_kits_and_components()
        else:
            print("python deploy.py (load_default | purge_kits_and_components)")
            exit(1)
    finally:
        # 閉じないと、asyncio.run()が戻るときにクライアントのバックグラウンド
        # タスクが未完了のままループが閉じ、"Task was destroyed but it is pending"
        # が出る。Dockerfile.aws の CMD はこの直後にサーバを起動するので、
        # コンテナ起動ログの先頭が毎回それで汚れる。
        await app.mongo_client.aclose()


def main():
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'load_default'
    asyncio.run(run(cmd))


if __name__ == '__main__':
    main()

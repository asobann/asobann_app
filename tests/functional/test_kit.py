import os
import pytest_asyncio
import json

os.environ["FLASK_ENV"] = "test"

# pylint: disable=E402
import asobann.app
import asobann.deploy


@pytest_asyncio.fixture
async def app():
    # モジュールトップレベルではなくfixture内で設定する: create_app()はテスト実行時に
    # 呼ばれるため、他のテストファイルが実行順序次第でFLASK_ENVを書き換えている可能性がある。
    os.environ["FLASK_ENV"] = "test"
    return await asobann.app.create_app()


@pytest_asyncio.fixture
async def client(app):
    async with app.test_client() as client:
        yield client


@pytest_asyncio.fixture
async def default_kits(app):
    # 初期データを自分で投入する。以前は tests/api の no_kits_and_components が
    # teardownで load_default() を呼ぶのに乗っかっていたため、実行順序に依存して
    # いた(pytest-randomlyでapiより先に回ると空になって落ちる)。
    # appフィクスチャに依存するのは、create_app()がstore層のDB接続を張るため。
    await asobann.deploy.load_default()


async def test_get_kits(client, default_kits):
    resp = await client.get('/kits')
    data = json.loads(await resp.get_data())
    assert len(data) > 0
    assert data[0]['kit']['name'] == 'Note'

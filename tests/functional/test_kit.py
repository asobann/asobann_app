import os
import pytest
import pytest_asyncio
import json

os.environ["FLASK_ENV"] = "test"

# pylint: disable=E402
import asobann.app

pytestmark = [pytest.mark.quick]


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


async def test_get_kits(client):
    resp = await client.get('/kits')
    data = json.loads(await resp.get_data())
    assert len(data) > 0
    assert data[0]['kit']['name'] == 'Note'

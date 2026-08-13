import os
import pytest_asyncio

os.environ["FLASK_ENV"] = "test"

import asobann.app


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


async def test_index(client):
    resp = await client.get('/')
    assert "302 FOUND" == resp.status
    assert "/tables/" in resp.headers["Location"]


async def test_googleanalytics_unavailable_in_dev(client):
    resp = await client.get('/tables/0123abc')
    data = await resp.get_data()
    assert b'Google Analytics' not in data


async def test_googleanalytics_available_in_prod(app, client):
    app.config['GOOGLE_ANALYTICS_ID'] = 'dummy-id'
    resp = await client.get('/tables/0123abc')
    data = await resp.get_data()
    assert b'Google Analytics' in data
    assert b'UA-' not in data
    assert b'id=dummy-id' in data

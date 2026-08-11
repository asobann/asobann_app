import os
import pytest
import pytest_asyncio

os.environ['FLASK_ENV'] = 'test'
from asobann import deploy
import asobann.app


@pytest_asyncio.fixture(scope='session', autouse=True)
async def _connect_store():
    # store層(tables/components/kits)をこのテストプロセス自身からも直接触るため、
    # サブプロセスのテストサーバとは別に、ここでもDB接続を確立する。
    # モジュールトップレベルではなくfixture内で設定する: 実行順序次第で他のテスト
    # ファイルがFLASK_ENVを書き換えている可能性がある。
    os.environ['FLASK_ENV'] = 'test'
    await asobann.app.create_app()


@pytest_asyncio.fixture
async def no_kits_and_components():
    await deploy.purge_kits_and_components()
    yield
    await deploy.load_default()

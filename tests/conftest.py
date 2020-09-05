import os
import subprocess
import time

import pytest

debug_server_config = {}


def build_server_environ():
    server_environ = dict(os.environ)
    server_environ["FLASK_ENV"] = "test"
    for key, value in debug_server_config.items():
        server_environ[key] = value
    return server_environ


@pytest.fixture(scope='session')
def debug_handler_wait():
    debug_server_config['ASOBANN_DEBUG_HANDLER_WAIT'] = "1"


def do_deploy_data():
    server_environ = build_server_environ()
    subprocess.run(["/usr/local/bin/pipenv", "run", "python", "-m", "asobann.deploy"], env=server_environ)


@pytest.fixture
def deploy_data():
    do_deploy_data()


@pytest.fixture(scope='session')
def server():
    server_environ = build_server_environ()
    do_deploy_data()
    with subprocess.Popen(["/usr/local/bin/pipenv", "run", "python", "-m", "asobann.wsgi"], env=server_environ) as proc:
        time.sleep(1)
        yield
        proc.terminate()


@pytest.fixture
def base_url(server):
    return 'http://localhost:10011'

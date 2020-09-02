import os
import subprocess
import time

import pytest

debug_server_config = {}


@pytest.fixture(scope='session')
def debug_handler_wait():
    debug_server_config['ASOBANN_DEBUG_HANDLER_WAIT'] = "1"


@pytest.fixture(scope='session')
def server():
    server_environ = dict(os.environ)
    server_environ["FLASK_ENV"] = "test"
    for key, value in debug_server_config.items():
        server_environ[key] = value
    subprocess.run(["/usr/local/bin/pipenv", "run", "python", "-m", "asobann.deploy"], env=server_environ)
    with subprocess.Popen(["/usr/local/bin/pipenv", "run", "python", "-m", "asobann.wsgi"], env=server_environ) as proc:
        time.sleep(1)
        yield
        proc.terminate()


@pytest.fixture
def base_url(server):
    return 'http://localhost:10011'

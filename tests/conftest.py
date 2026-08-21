import os
import socket
import subprocess
import sys
import time
from typing import Optional, Dict

import pytest

debug_server_config = {}

# Launch the server with the interpreter that's already running the tests, rather than a
# hardcoded /usr/local/bin/pipenv. The e2e image (Dockerfile.e2e) is built on the
# production image, which installs dependencies with plain pip and has no pipenv at all.
# Using sys.executable also guarantees the server runs under exactly the interpreter and
# site-packages the tests were collected with.
SERVER_COMMAND = [sys.executable, "-m", "asobann.asgi"]
DEPLOY_COMMAND = [sys.executable, "-m", "asobann.deploy"]

# Must match config_test.py's PORT.
TEST_SERVER_PORT = 10011


def wait_for_server(port: int, timeout_seconds: int = 60) -> None:
    """
    Block until the test server accepts connections on `port`.

    Waiting a fixed amount instead (this used to be time.sleep(1)) races with the
    server's startup: connecting to mongo alone can take several seconds, so the
    browser would navigate before the socket was listening and the test failed with
    an opaque `Reached error page: about:neterror?e=connectionFailure`.
    """
    started_at = time.monotonic()
    while True:
        try:
            with socket.create_connection(('localhost', port), timeout=2):
                return
        except OSError:
            if time.monotonic() - started_at > timeout_seconds:
                raise TimeoutError(
                    f'test server did not start listening on port {port} '
                    f'within {timeout_seconds}s')
            time.sleep(0.2)


class TestServerProvider:
    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self.original_env = dict(os.environ)
        self.original_env["FLASK_ENV"] = "test"
        self.current_server_environ: Dict = {}
        self.env_to_apply: Dict = {}

    def set_env(self, name, value):
        self.env_to_apply[name] = value

    def get_env(self, name):
        return self.env_to_apply.get(name, self.original_env.get(name, None))

    def get_env_to_run(self):
        env_to_run = dict(self.original_env)
        env_to_run.update(self.env_to_apply)
        return env_to_run

    def provide_server(self):
        env_to_run = self.get_env_to_run()
        if env_to_run != self.current_server_environ:
            if self.proc:
                self.stop_server()

            self.current_server_environ = env_to_run
            self.start_server(env_to_run)
        self.env_to_apply = {}

    def start_server(self, env):
        do_deploy_data()
        self.proc = subprocess.Popen(SERVER_COMMAND, env=env)
        self.current_server_environ = env
        wait_for_server(TEST_SERVER_PORT)

    def stop_server(self):
        self.proc.terminate()


provider = TestServerProvider()


@pytest.fixture(scope='session')
def server_provider():
    yield provider
    provider.stop_server()


@pytest.fixture
def debug_handler_wait():
    provider.set_env('ASOBANN_DEBUG_HANDLER_WAIT', '1')


def do_deploy_data():
    server_environ = provider.get_env_to_run()
    subprocess.run(DEPLOY_COMMAND, env=server_environ)


@pytest.fixture
def deploy_data():
    do_deploy_data()


@pytest.fixture
def server(server_provider: TestServerProvider):
    server_provider.provide_server()


@pytest.fixture
def base_url(server):
    return f'http://localhost:{TEST_SERVER_PORT}'

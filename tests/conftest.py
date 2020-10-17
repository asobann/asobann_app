import os
import subprocess
import time
from typing import Optional, Dict

import pytest

debug_server_config = {}


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
        self.proc = subprocess.Popen(["/usr/local/bin/pipenv", "run", "python", "-m", "asobann.wsgi"], env=env)
        self.current_server_environ = env
        time.sleep(1)

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


@pytest.fixture
def debug_order_of_updates():
    debug_opts = provider.get_env('ASOBANN_DEBUG_OPTS') or ''
    debug_opts += ' ORDER_OF_UPDATES'
    provider.set_env('ASOBANN_DEBUG_OPTS', debug_opts.strip())


def do_deploy_data():
    server_environ = provider.get_env_to_run()
    subprocess.run(["/usr/local/bin/pipenv", "run", "python", "-m", "asobann.deploy"], env=server_environ)


@pytest.fixture
def deploy_data():
    do_deploy_data()


@pytest.fixture
def server(server_provider: TestServerProvider):
    server_provider.provide_server()


@pytest.fixture
def base_url(server):
    return 'http://localhost:10011'

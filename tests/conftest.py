import os
import subprocess
import time


import pytest


@pytest.fixture(scope='session')
def server():
    os.environ["FLASK_ENV"] = "test"
    subprocess.run(["/usr/local/bin/pipenv", "run", "python", "-m", "asobann.deploy"], env=os.environ)
    with subprocess.Popen(["/usr/local/bin/pipenv", "run", "python", "-m", "asobann.wsgi"], env=os.environ) as proc:
        time.sleep(1)
        yield
        proc.terminate()


@pytest.fixture
def base_url(server):
    return 'http://localhost:10011'

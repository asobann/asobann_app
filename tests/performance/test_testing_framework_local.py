from pathlib import Path
import subprocess
import  urllib.request
import time

from .cli import LocalContainers


def test_run_in_container(tmp_path):
    d = Path(tmp_path)
    (d / 'runner').mkdir()
    with open(d / 'runner' / 'run.py', 'w') as f:
        f.write(
            """
print('Hello, container!')\n
""")
    with open(d / 'Dockerfile', 'w') as f:
        f.write("""
FROM ubuntu:18.04
RUN apt-get -y update
RUN apt-get install -y python3
COPY runner/ .
CMD python3 run.py
""")
    proc = subprocess.run("docker build . -t test_run_in_container", shell=True, cwd=tmp_path, encoding='utf8')
    assert proc.returncode == 0
    proc = subprocess.run("docker run test_run_in_container", shell=True, stdout=subprocess.PIPE, cwd=tmp_path,
                          encoding='utf8')
    assert proc.returncode == 0
    output = proc.stdout
    assert output.strip() == 'Hello, container!'


def test_run_multiprocess_in_local_containers():
    env = LocalContainers()
    env.build_docker_images()
    env.start_workers()
    env.start_controller()
    result = env.run_test('tests.performance.say_hello')
    env.shutdown()

    assert result == ['Hello, container! from host.docker.internal:50000',
                      'Hello, container! from host.docker.internal:50001',
                      'Hello, container! from host.docker.internal:50002']


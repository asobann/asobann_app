from pathlib import Path
import re
import subprocess
from .cli import AwsContainers, LocalContainers, Logger


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
    env.start_workers(3)
    env.start_controller()
    result = env.run_test('tests.performance.say_hello')
    env.shutdown()

    assert result == ['Hello, container! from host.docker.internal:50000',
                      'Hello, container! from host.docker.internal:50001',
                      'Hello, container! from host.docker.internal:50002']


def test_run_multiprocess_in_aws():
    Logger.debug = True
    env = AwsContainers()
    env.build_docker_images()
    env.start_workers(5)
    env.start_controller()
    result = env.run_test('tests.performance.say_hello')
    env.shutdown()

    assert len(result) == 5
    for r in result:
        assert re.match('Hello, container! from [0-9.]*:50000', r)


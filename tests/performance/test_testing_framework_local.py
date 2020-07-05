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


def test_run_multiprocess_in_local_containers(tmp_path):
    LocalContainers.build_docker_images(tmp_path)

    ports = LocalContainers.start_workers(tmp_path).ports

    LocalContainers.start_controller(ports, tmp_path)

    result = LocalContainers.send_command('run')

    assert result == 'Hello, container!Hello, container!Hello, container!'

    LocalContainers.shutdown()

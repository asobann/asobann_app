from pathlib import Path
import re
import json
import os
import subprocess
import inspect
import pytest
import time
from pprint import pprint

from ..e2e import helper


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
    d = Path(tmp_path)
    (d / 'runner').mkdir()
    with open(d / 'runner' / 'run.py', 'w') as f:
        from . import remote_runner
        f.write(inspect.getsource(remote_runner))
    with open(d / 'Dockerfile_worker', 'w') as f:
        f.write("""
FROM ubuntu:18.04
EXPOSE 50000 50001 50002 50003 50004 50005 50006 50007 50008 50009
RUN apt-get -y update
RUN apt-get install -y python3
COPY runner/ .
CMD python3 run.py worker $PORT
""")
    with open(d / 'Dockerfile_controller', 'w') as f:
        f.write("""
FROM ubuntu:18.04
EXPOSE 8888
RUN apt-get -y update
RUN apt-get install -y python3
COPY runner/ .
CMD python3 run.py controller
""")
    proc = subprocess.run("docker build . -f Dockerfile_worker -t test_run_multiprocess_in_container_worker",
                          shell=True, cwd=tmp_path, encoding='utf8')
    assert proc.returncode == 0
    proc = subprocess.run("docker build . -f Dockerfile_worker -t test_run_multiprocess_in_container_controller",
                          shell=True, cwd=tmp_path, encoding='utf8')
    assert proc.returncode == 0

    ports = [50000, 50001, 50002]
    procs = []
    for port in ports:
        print(f'start worker container port {port}')
        procs.append(
            subprocess.run(f"docker run -d -p {port}:{port} -e PORT={port} test_run_multiprocess_in_container_worker",
                           shell=True,
                           stdout=subprocess.PIPE,
                           cwd=tmp_path,
                           encoding='utf8'))

    if os.name == 'posix':
        # see https://docs.docker.com/engine/reference/commandline/run/#add-entries-to-container-hosts-file-add-host
        proc = subprocess.run(
            "ip -4 addr show scope global dev docker0 | grep inet | awk '{print $2}' | cut -d / -f 1 | sed -n 1p",
            shell=True,
            stdout=subprocess.PIPE,
            cwd=tmp_path,
            encoding='utf8')
        host_access =  f"--add-host=host.docker.internal:{proc.stdout.strip()}"
    elif os.name == 'nt':
        # see https://docs.docker.com/docker-for-windows/networking/#per-container-ip-addressing-is-not-possible
        host_access = ''
    print(f'start controller container ports {ports}')
    proc = subprocess.run(f"docker run {host_access} -p 8888:8888 -d test_run_multiprocess_in_container_controller "
                          f"python3 run.py controller {','.join([f'host.docker.internal:{p}' for p in ports])}",
                          shell=True,
                          stdout=subprocess.PIPE,
                          cwd=tmp_path,
                          encoding='utf8')
    assert proc.returncode == 0

    import urllib.request
    print('send run command')
    req = urllib.request.Request('http://localhost:8888', data=b'run')
    res = urllib.request.urlopen(req)
    print('read response')
    result = res.read().decode('utf-8')
    print('send shutdown command')
    res = urllib.request.Request('http://localhost:8888', data=b'shutdown')

    assert result == 'Hello, container!\nHello, container!\nHello, container!'

    time.sleep(1)
    proc = subprocess.run("docker ps",
            stdout=subprocess.PIPE, shell=True, cwd=tmp_path, encoding='utf8')
    assert proc.returncode == 0
    assert len(proc.stdout.split('\n')) == 1, 'no process remains'

import os
import sys
import subprocess
from pathlib import Path
import tempfile
import urllib.request
import time
import shutil
import json
from pprint import pprint
from typing import Optional

import typer


class Logger:
    debug = False

    @staticmethod
    def log(*args):
        if Logger.debug:
            print(*args)


log = Logger.log


def system(cmd, capture=False, cwd=None):
    if capture:
        stdout = subprocess.PIPE
    else:
        if Logger.debug:
            stdout = None
        else:
            stdout = subprocess.DEVNULL
    proc = subprocess.run(cmd,
                          shell=True,
                          stdout=stdout,
                          stderr=subprocess.STDOUT,
                          cwd=cwd,
                          encoding='utf8')
    return proc


def do_run(name: str, tmpdir, env: 'AbstractContainers'):
    env.build_docker_images(tmpdir)
    env.start_workers()
    env.start_controller()
    result = env.run_test(name)
    env.shutdown()

    pprint(result)


def run(name: str, local: bool = False, aws: bool = False, debug: bool = False):
    Logger.debug = debug
    with tempfile.TemporaryDirectory() as tmpdir:
        if local:
            env = LocalContainers()
        elif aws:
            env = AwsContainers()
        else:
            print('Either --local or --aws option must be specified', file=sys.stderr)
            exit(1)
        do_run(name, tmpdir=tmpdir, env=env)


class AbstractContainers:
    controller_url = None

    class Workers:
        def __init__(self, ports):
            self.ports = ports

    def __init__(self):
        self._workers: 'Optional[AbstractContainers.Workers]' = None

    def build_docker_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            shutil.copytree(Path('./tests'), d / 'runner/tests')
            shutil.copytree(Path('./src'), d / 'runner/src')
            shutil.copy(Path('./Pipfile'), d / 'runner/')
            shutil.copy(Path('./Pipfile.lock'), d / 'runner/')
            with open(d / 'Dockerfile_worker', 'w') as f:
                f.write("""
FROM ubuntu:18.04
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PYTHONPATH=/runner
RUN apt-get -y update
RUN apt-get install -y python3 python3-pip firefox firefox-geckodriver
RUN pip3 install pipenv
WORKDIR /runner
COPY runner/ .
RUN pipenv install
EXPOSE 50000 50001 50002 50003 50004 50005 50006 50007 50008 50009
CMD pipenv run python tests/performance/remote_runner.py worker $PORT
    """)
            with open(d / 'Dockerfile_controller', 'w') as f:
                f.write("""
FROM ubuntu:18.04
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PYTHONPATH=/runner
RUN apt-get -y update
RUN apt-get install -y python3 python3-pip
RUN pip3 install pipenv
WORKDIR /runner
COPY runner/ .
EXPOSE 8888
RUN pipenv install
    """)
            proc = system("docker build . -f Dockerfile_worker -t test_run_multiprocess_in_container_worker",
                          cwd=tmpdir)
            assert proc.returncode == 0
            proc = system("docker build . -f Dockerfile_worker -t test_run_multiprocess_in_container_controller",
                          cwd=tmpdir)
            assert proc.returncode == 0

    def start_workers(self) -> 'AbstractContainers.Workers':
        ports = [50000, 50001, 50002]
        procs = []
        for port in ports:
            log(f'start worker container port {port}')
            procs.append(
                system(
                    f"docker run -d -p {port}:{port} -e PORT={port} test_run_multiprocess_in_container_worker",
                    capture=True,
                ))

        self._workers = AbstractContainers.Workers(ports=ports)
        return self._workers

    def start_controller(self):
        ports = self._workers.ports
        if os.name == 'posix':
            # see https://docs.docker.com/engine/reference/commandline/run/#add-entries-to-container-hosts-file-add-host
            proc = system(
                "ip -4 addr show scope global dev docker0 | grep inet | awk '{print $2}' | cut -d / -f 1 | sed -n 1p",
                capture=True,
            )
            host_access = f"--add-host=host.docker.internal:{proc.stdout.strip()}"
        elif os.name == 'nt':
            # see https://docs.docker.com/docker-for-windows/networking/#per-container-ip-addressing-is-not-possible
            host_access = ''
        else:
            raise RuntimeError()
        log(f'start controller container ports {ports}')
        proc = system(f"docker run {host_access} -p 8888:8888 -d test_run_multiprocess_in_container_controller "
                      f"pipenv run python tests/performance/remote_runner.py controller {','.join([f'host.docker.internal:{p}' for p in ports])}")
        assert proc.returncode == 0
        self._wait_for_controller_to_start()

    def _wait_for_controller_to_start(self):
        while True:
            try:
                req = urllib.request.Request(self.controller_url, method='HEAD')
                res = urllib.request.urlopen(req)
                if res.getcode() == 200:
                    break
            except ConnectionError:
                time.sleep(1)

    def _send_command(self, command: str):
        res = urllib.request.urlopen(self.controller_url, data=command.encode('utf8'))
        result = res.read().decode('utf-8')
        return result

    def shutdown(self):
        self._send_command('shutdown')
        time.sleep(1)
        proc = system("docker ps", capture=True)
        assert proc.returncode == 0
        assert len(proc.stdout.strip().split('\n')) == 1, 'no process remains'

    def run_test(self, filename):
        result = self._send_command(f'run {filename}')
        return json.loads(result)


class LocalContainers(AbstractContainers):
    controller_url = 'http://localhost:8888'


class AwsContainers(AbstractContainers):
    pass


if __name__ == '__main__':
    typer.run(run)

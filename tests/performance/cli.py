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
import re
from typing import Optional, Union

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
    if proc.returncode != 0:
        raise RuntimeError(f'external command "{cmd}" failed. output="{proc.stdout}"')
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

    def prepare_docker_contents(self, base_dir: Union[str, Path]):
        d = Path(base_dir)
        (d / 'runner').mkdir()
        shutil.copytree(Path('./tests'), d / 'runner/tests')
        shutil.copytree(Path('./src'), d / 'runner/src')
        shutil.copy(Path('./Pipfile'), d / 'runner/')
        shutil.copy(Path('./Pipfile.lock'), d / 'runner/')

    def build_docker_image_for_worker(self, base_dir):
        with open(Path(base_dir) / 'Dockerfile_worker', 'w') as f:
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
        proc = system("docker build . -f Dockerfile_worker -t test_run_multiprocess_in_container_worker",
                      cwd=base_dir)
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

    def start_controller(self) -> None:
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

    def _wait_for_controller_to_start(self) -> None:
        while True:
            try:
                req = urllib.request.Request(self.controller_url, method='HEAD')
                res = urllib.request.urlopen(req)
                if res.getcode() == 200:
                    break
            except ConnectionError:
                time.sleep(1)

    def _send_command(self, command: str) -> str:
        res = urllib.request.urlopen(self.controller_url, data=command.encode('utf8'))
        result = res.read().decode('utf-8')
        return result

    def shutdown(self) -> None:
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

    def build_docker_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.prepare_docker_contents(tmpdir)
            self.build_docker_image_for_worker(tmpdir)

            with open(Path(tmpdir) / 'Dockerfile_controller', 'w') as f:
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
            proc = system("docker build . -f Dockerfile_worker -t test_run_multiprocess_in_container_controller",
                          cwd=tmpdir)
            assert proc.returncode == 0


class Aws:
    class NonZeroExitError(RuntimeError):
        pass

    @staticmethod
    def get_ecr(name):
        proc = subprocess.run(f'aws ecr create-repository --repository-name {name}',
                              shell=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              encoding='utf8')
        assert proc.returncode == 0 or 'already exists' in proc.stdout
        if proc.returncode == 0:
            result = json.loads(proc.stdout)
            registryId = result['repository']['registryId']
            repositoryUri = result['repository']['repositoryUri']
        else:
            proc = subprocess.run(f'aws ecr describe-repositories --repository-names {name}',
                                  shell=True,
                                  stdout=subprocess.PIPE,
                                  encoding='utf8')
            assert proc.returncode == 0
            result = json.loads(proc.stdout)
            registryId = result['repositories'][0]['registryId']
            repositoryUri = result['repositories'][0]['repositoryUri']
        region = re.match('^[^.]*.dkr.ecr.([^.]*).amazonaws.com/.*$', repositoryUri).group(1)

        return (registryId, repositoryUri, region)

    @staticmethod
    def delete_ecr(name):
        proc = subprocess.run(f'aws ecr delete-repository --repository-name {name} --force',
                              shell=True,
                              stdout=subprocess.DEVNULL,
                              encoding='utf8')
        assert proc.returncode == 0

    @staticmethod
    def run(cmd):
        proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8')
        if not proc.returncode == 0:
            raise Aws.NonZeroExitError(f'aws command exit with code {proc.returncode}', proc.stdout)
        return proc.stdout


class Ecs:
    @staticmethod
    def create_cluster(cluster_name):
        try:
            output = Aws.run(
                f'aws ecs create-cluster --cluster-name {cluster_name} --tags key=Yattom:ProductName,value=asobann')
            return json.loads(output)['cluster']
        except Aws.NonZeroExitError as e:
            if 'inconsistent with arguments' in str(e):
                # cluster already exists; just describe it
                output = Aws.run(f'aws ecs describe-clusters --clusters {cluster_name}')
                return json.loads(output)['clusters'][0]
            else:
                raise

    @staticmethod
    def delete_cluster(cluster_name):
        Aws.run(f'aws ecs delete-cluster --cluster {cluster_name}')

    @staticmethod
    def build_task_definition_worker(execution_role_arn, image_uri, region):
        return {
            "containerDefinitions": [
                {
                    "name": "test_run_multiprocess_in_container_worker",
                    "image": image_uri,
                    "cpu": 0,
                    "portMappings": [
                        {
                            "containerPort": 50000,
                            "hostPort": 50000,
                            "protocol": "tcp"
                        },
                        {
                            "containerPort": 50000,
                            "hostPort": 50000,
                            "protocol": "udp"
                        }
                    ],
                    "essential": True,
                    "environment": [
                        {
                            "name": "PORT",
                            "value": "50000"
                        }
                    ],
                    "mountPoints": [],
                    "volumesFrom": [],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "/ecs/test_run_multiprocess_in_container_worker",
                            "awslogs-region": region,
                            "awslogs-stream-prefix": "ecs"
                        }
                    }
                }
            ],
            "family": "test_run_multiprocess_in_container_worker",
            "executionRoleArn": execution_role_arn,
            "networkMode": "awsvpc",
            "volumes": [],
            "placementConstraints": [],
            "requiresCompatibilities": [
                "FARGATE"
            ],
            "cpu": "256",
            "memory": "512"
        }

    @staticmethod
    def prepare_worker_task_def(base_dir, worker_ecr):
        registry_id, repository_uri, region = worker_ecr
        system(f'docker tag test_run_multiprocess_in_container_worker:latest {repository_uri}')
        system(
            f'aws ecr get-login-password | docker login --username AWS --password-stdin {registry_id}.dkr.ecr.{region}.amazonaws.com')
        system(f'docker push {repository_uri}')
        task_def = Ecs.build_task_definition_worker(f'arn:aws:iam::{registry_id}:role/ecsTaskExecutionRole',
                                                    repository_uri,
                                                    region)
        task_def_file = base_dir / 'taskdef_worker.json'
        with open(task_def_file, 'w') as f:
            json.dump(task_def, f)
        registered = Aws.run(f'aws ecs register-task-definition --cli-input-json file://{task_def_file}')
        return json.loads(registered)


class AwsContainers(AbstractContainers):
    CLUSTER_NAME = 'asobann_tests'

    def __init__(self):
        super().__init__()
        self.cluster = None

    def build_docker_images(self) -> None:
        cluster = Ecs.create_cluster(self.CLUSTER_NAME)
        pass

    def shutdown(self):
        super().shutdown()
        if self.cluster:
            Ecs.delete_cluster(self.CLUSTER_NAME)


if __name__ == '__main__':
    typer.run(run)

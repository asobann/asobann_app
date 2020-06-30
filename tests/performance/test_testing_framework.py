from pathlib import Path
import re
import json
import os
import subprocess
import inspect
import pytest

from ..e2e import helper

def build_task_definition_controller(execution_role_arn, image_uri, region, workers):
    return {
        "containerDefinitions": [
            {
                "name": "test_run_multiprocess_in_container_controller",
                "image": image_uri,
                "cpu": 0,
                "portMappings": [],
                "essential": True,
                "command": [
                    "/usr/bin/python3",
                    "run.py",
                    "controller",
                    workers,
                ],
                "environment": [],
                "mountPoints": [],
                "volumesFrom": [],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/test_run_multiprocess_in_container_controller",
                        "awslogs-region": region,
                        "awslogs-stream-prefix": "ecs"
                    }
                }
            }
        ],
        "family": "test_run_multiprocess_in_container_controller",
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
    proc = subprocess.run(f"docker run {host_access} test_run_multiprocess_in_container_controller "
                          f"python3 run.py controller {','.join([f'host.docker.internal:{p}' for p in ports])}",
                          shell=True,
                          stdout=subprocess.PIPE,
                          cwd=tmp_path,
                          encoding='utf8')
    assert proc.returncode == 0

    output = proc.stdout
    assert output.strip() == 'Hello, container!\nHello, container!\nHello, container!'


class Aws:
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
    def run(cmd):
        proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8')
        assert proc.returncode == 0, proc.stdout
        return proc.stdout


class TestRunInMultiprocessOnAws:
    @staticmethod
    @pytest.fixture
    def worker_ecr():
        ecr = Aws.get_ecr('test_run_multiprocess_in_container_worker')
        yield ecr
        # TODO
        # delete_ecr('test_run_multiprocess_in_container_worker')


    @staticmethod
    @pytest.fixture
    def controller_ecr():
        ecr = Aws.get_ecr('test_run_multiprocess_in_container_controller')
        yield ecr
        # TODO
        # delete_ecr('test_run_multiprocess_in_container_controller')

    @staticmethod
    def delete_ecr(name):
        proc = subprocess.run(f'aws ecr delete-repository --repository-name {name} --force',
                               shell=True,
                               encoding='utf8')
        assert proc.returncode == 0

    @staticmethod
    def prepare_docker_contents(tmp_path):
        with open(tmp_path / 'runner' / 'run.py', 'w') as f:
            from . import remote_runner
            f.write(inspect.getsource(remote_runner))

    @staticmethod
    def prepare_worker(tmp_path, worker_ecr):
        registryId, repositoryUri, region = worker_ecr

        # build docker image for worker
        with open(tmp_path / 'Dockerfile_worker', 'w') as f:
            f.write("""
FROM ubuntu:18.04
EXPOSE 50000 50001 50002 50003 50004 50005 50006 50007 50008 50009
RUN apt-get -y update
RUN apt-get install -y python3
COPY runner/ .
CMD python3 run.py worker $PORT
    """)
        # TODO
        # proc = subprocess.run("docker build . -f Dockerfile_worker -t test_run_multiprocess_in_container_worker",
        #                       shell=True, cwd=tmp_path, encoding='utf8')
        # assert proc.returncode == 0
        # proc = subprocess.run(f'docker tag test_run_multiprocess_in_container_worker:latest {repositoryUri}', shell=True, encoding='utf-8')
        # assert proc.returncode == 0
        # proc = subprocess.run(f'aws ecr get-login-password | docker login --username AWS --password-stdin {registryId}.dkr.ecr.{region}.amazonaws.com', shell=True, encoding='utf-8')
        # assert proc.returncode == 0
        # proc = subprocess.run(f'docker push {repositoryUri}', shell=True, encoding='utf-8')
        # assert proc.returncode == 0
        task_def = build_task_definition_worker(f'arn:aws:iam::{registryId}:role/ecsTaskExecutionRole', repositoryUri, region)
        task_def_file = tmp_path / 'taskdef_worker.json'
        with open(task_def_file, 'w') as f:
            json.dump(task_def, f)
        Aws.run(f'aws ecs register-task-definition --cli-input-json file://{task_def_file}')


    @staticmethod
    def prepare_controller(tmp_path, controller_ecr):
        # build docker image for controller
        registryId, repositoryUri, region = controller_ecr
        with open(tmp_path / 'Dockerfile_controller', 'w') as f:
            f.write("""
FROM ubuntu:18.04
RUN apt-get -y update
RUN apt-get install -y python3
COPY runner/ .
CMD python3 run.py controller
    """)
        # TODO
        # proc = subprocess.run("docker build . -f Dockerfile_worker -t test_run_multiprocess_in_container_controller",
        #                       shell=True, cwd=tmp_path, encoding='utf8')
        # assert proc.returncode == 0
        # proc = subprocess.run(f'docker tag test_run_multiprocess_in_container_controller:latest {repositoryUri}', shell=True, encoding='utf-8')
        # assert proc.returncode == 0
        # proc = subprocess.run(f'docker push {repositoryUri}', shell=True, encoding='utf-8')
        # assert proc.returncode == 0
        task_def = build_task_definition_controller(f'arn:aws:iam::{registryId}:role/ecsTaskExecutionRole', repositoryUri, region, 'host:50000')
        task_def_file = tmp_path / 'taskdef_controller.json'
        with open(task_def_file, 'w') as f:
            json.dump(task_def, f)
        Aws.run(f'aws ecs register-task-definition --cli-input-json file://{task_def_file}')


    def test_run_multiprocess_in_aws(self, tmp_path, worker_ecr, controller_ecr):
        d = Path(tmp_path)
        (d / 'runner').mkdir()
        self.prepare_docker_contents(d)
        self.prepare_worker(d, worker_ecr)
        self.prepare_controller(d, controller_ecr)

        assert False, 'stop here'

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
        proc = subprocess.run(f"docker run {host_access} test_run_multiprocess_in_container_controller "
                              f"python3 run.py controller {','.join([f'host.docker.internal:{p}' for p in ports])}",
                              shell=True,
                              stdout=subprocess.PIPE,
                              cwd=tmp_path,
                              encoding='utf8')
        assert proc.returncode == 0

        output = proc.stdout
        assert output.strip() == 'Hello, container!\nHello, container!\nHello, container!'

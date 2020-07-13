import json
import os
import sys
import re
import shutil
import subprocess
import tempfile
import time
import datetime
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Tuple, Dict


CONNECTION_RETRY_SECONDS = 20


class Logger:
    debug = False

    @staticmethod
    def log(*args):
        if Logger.debug:
            print(*args)
            sys.stdout.flush()


log = Logger.log


def system(cmd, capture=False, cwd=None, daemon=False):
    log(f'system command: {cmd}')
    if capture:
        stdout = subprocess.PIPE
    else:
        if Logger.debug:
            stdout = None
        else:
            stdout = subprocess.DEVNULL
    if daemon:
        proc = subprocess.Popen(cmd,
                                shell=True,
                                stdout=stdout,
                                stderr=subprocess.STDOUT,
                                cwd=cwd,
                                encoding='utf8')
        return proc
    else:
        proc = subprocess.run(cmd,
                              shell=True,
                              stdout=stdout,
                              stderr=subprocess.STDOUT,
                              cwd=cwd,
                              encoding='utf8')
        if proc.returncode != 0:
            raise RuntimeError(f'external command "{cmd}" failed. output="{proc.stdout}"')
        return proc


WORKER_NAME = 'test_run_multiprocess_in_container_worker'
CONTROLLER_NAME = 'test_run_multiprocess_in_container_controller'


class AbstractContainers:
    controller_url = None

    class Workers:
        def __init__(self, binds, tasks: Dict = None, procs: List = None):
            self.binds: List[Tuple[str, int]] = binds
            self.tasks: Dict = tasks
            self.procs = procs

    def __init__(self):
        self._workers: 'Optional[AbstractContainers.Workers]' = None

    def prepare_docker_contents(self, base_dir: Path):
        (base_dir / 'runner').mkdir()
        shutil.copytree('./tests', str(base_dir / 'runner/tests'))
        shutil.copytree('./src', str(base_dir / 'runner/src'))
        shutil.copy('./Pipfile', str(base_dir / 'runner/'))
        shutil.copy('./Pipfile.lock', str(base_dir / 'runner/'))

    def build_docker_images(self) -> None:
        raise NotImplementedError()

    def start_workers(self, worker_count) -> None:
        raise NotImplementedError()

    def start_controller(self) -> None:
        raise NotImplementedError()

    def remove_containers(self) -> None:
        raise NotImplementedError()

    def build_docker_image_for_worker(self, base_dir: Path):
        with open(str(base_dir / 'Dockerfile_worker'), 'w') as f:
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
        proc = system(f"docker build . -f Dockerfile_worker -t {WORKER_NAME}",
                      cwd=base_dir)
        assert proc.returncode == 0

    def build_docker_image_for_controller(self, base_dir):
        with open(Path(base_dir) / 'Dockerfile_controller', 'w') as f:
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
EXPOSE 8888
    """)
        proc = system(f"docker build . -f Dockerfile_controller -t {CONTROLLER_NAME}",
                      cwd=base_dir)
        assert proc.returncode == 0

    def _wait_for_controller_to_start(self) -> None:
        while True:
            try:
                req = urllib.request.Request(self.controller_url, method='HEAD')
                res = urllib.request.urlopen(req)
                if res.getcode() == 200:
                    break
            except (ConnectionError, urllib.error.URLError):
                time.sleep(1)

    def _send_command(self, command: str) -> str:
        log(f'send command url={self.controller_url}, data={command}')
        try:
            started_at = datetime.datetime.now()
            while True:
                try:
                    res = urllib.request.urlopen(self.controller_url, data=command.encode('utf8'))
                    break
                except ConnectionRefusedError:
                    if (datetime.datetime.now() - started_at).total_seconds() > CONNECTION_RETRY_SECONDS:
                        raise
                    log(f'connection to controller {self.controller_url} refused. Retrying ...')
                    time.sleep(1)
            result = res.read().decode('utf-8')
            return result
        except urllib.error.HTTPError as ex:
            log('http error', *ex.args)
            if ex.fp:
                result = ex.fp.read().decode('utf-8')
                log(result)
                return json.dumps({'error': result})
            else:
                return '{}'

    def shutdown(self) -> None:
        self._send_command('shutdown')
        time.sleep(1)

    def run_test(self, module_name, headless=True):
        result = self._send_command(f'headless {"true" if headless else "false"}')
        result = self._send_command(f'run {module_name}')
        return json.loads(result)


class LocalProcesses(AbstractContainers):
    controller_url = 'http://localhost:8888'

    def build_docker_images(self) -> None:
        # do nothing
        pass

    def start_workers(self, worker_count) -> None:
        assert worker_count <= 10, 'Local running permits only less than 10 workers for the time being'
        ports = [50000 + i for i in range(worker_count)]  # 50000-50009 is EXPOSEd in Dockerfile
        procs = []
        for port in ports:
            log(f'start worker container port {port}')
            procs.append(
                system(f"PYTHONPATH=. python tests/performance/remote_runner.py worker {port}",
                       capture=False, daemon=True))

        self._workers = AbstractContainers.Workers(binds=[('localhost', p) for p in ports], procs=procs)
        time.sleep(1)

    def start_controller(self) -> None:
        ports = [p for h, p in self._workers.binds]
        self._controller_proc = system(f"PYTHONPATH=. python tests/performance/remote_runner.py controller"
               f" {','.join([f'localhost:{p}' for p in ports])}",
               capture=False, daemon=True)
        self._wait_for_controller_to_start()

    def shutdown(self):
        try:
            super().shutdown()
        except:
            pass
        for proc in self._workers.procs + [self._controller_proc]:
            try:
                proc.wait(1)
            except subprocess.TimeoutExpired:
                proc.terminate()

    def remove_containers(self) -> None:
        # do nothing
        pass


class LocalContainers(AbstractContainers):
    controller_url = 'http://localhost:8888'

    def build_docker_images(self) -> None:
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            self.prepare_docker_contents(base_path)

            self.build_docker_image_for_worker(base_path)
            self.build_docker_image_for_controller(base_path)

    def start_workers(self, worker_count) -> None:
        assert worker_count < 10, 'Local running permits only less than 10 workers for the time being'
        ports = [50000 + i for i in range(worker_count)]  # 50000-50009 is EXPOSEd in Dockerfile
        procs = []
        for port in ports:
            log(f'start worker container port {port}')
            procs.append(
                system(
                    f"docker run -d -p {port}:{port} -e PORT={port} {WORKER_NAME}",
                    capture=True,
                ))

        self._workers = AbstractContainers.Workers(binds=[('localhost', p) for p in ports])

    def start_controller(self) -> None:
        ports = [p for h, p in self._workers.binds]
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
        system(f"docker run {host_access} -p 8888:8888 -d {CONTROLLER_NAME} "
               f"pipenv run python tests/performance/remote_runner.py controller {','.join([f'host.docker.internal:{p}' for p in ports])}")
        self._wait_for_controller_to_start()

    def shutdown(self) -> None:
        super().shutdown()
        proc = system("docker ps", capture=True)
        assert proc.returncode == 0
        assert len(proc.stdout.strip().split('\n')) == 1, 'no process remains'

    def remove_containers(self) -> None:
        raise NotImplementedError()


class Aws:
    class NonZeroExitError(RuntimeError):
        pass

    @staticmethod
    def get_ecr(name):
        try:
            output = Aws.run(f'aws ecr create-repository --repository-name {name}')
            result = json.loads(output)
            registry_id = result['repository']['registryId']
            repository_uri = result['repository']['repositoryUri']
        except Aws.NonZeroExitError as ex:
            if not any(['already exists' in a for a in ex.args]):
                raise
            output = Aws.run(f'aws ecr describe-repositories --repository-names {name}')
            result = json.loads(output)
            registry_id = result['repositories'][0]['registryId']
            repository_uri = result['repositories'][0]['repositoryUri']

        region = re.match('^[^.]*.dkr.ecr.([^.]*).amazonaws.com/.*$', repository_uri).group(1)

        return registry_id, repository_uri, region

    @staticmethod
    def delete_ecr(name):
        Aws.run(f'aws ecr delete-repository --repository-name {name} --force')

    @staticmethod
    def run(cmd):
        log(f'Aws.run cmd={cmd}')
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
                return Ecs.describe_cluster(cluster_name)
            else:
                raise

    @staticmethod
    def describe_cluster(cluster_name):
        output = Aws.run(f'aws ecs describe-clusters --clusters {cluster_name}')
        return json.loads(output)['clusters'][0]

    @staticmethod
    def delete_cluster(cluster_name):
        Aws.run(f'aws ecs delete-cluster --cluster {cluster_name}')

    @staticmethod
    def build_task_definition_worker(execution_role_arn, image_uri, region):
        return {
            "containerDefinitions": [
                {
                    "name": WORKER_NAME,
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
                            "awslogs-group": f"/ecs/{WORKER_NAME}",
                            "awslogs-region": region,
                            "awslogs-stream-prefix": "ecs"
                        }
                    }
                }
            ],
            "family": WORKER_NAME,
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
    def build_task_definition_controller(execution_role_arn, image_uri, region):
        return {
            "containerDefinitions": [
                {
                    "name": CONTROLLER_NAME,
                    "image": image_uri,
                    "cpu": 0,
                    "portMappings": [
                        {
                            "containerPort": 8888,
                            "hostPort": 8888,
                            "protocol": "tcp"
                        },
                    ],
                    "essential": True,
                    "environment": [],
                    "mountPoints": [],
                    "volumesFrom": [],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": f"/ecs/{CONTROLLER_NAME}",
                            "awslogs-region": region,
                            "awslogs-stream-prefix": "ecs"
                        }
                    }
                }
            ],
            "family": CONTROLLER_NAME,
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
    def prepare_worker_task_def(base_dir: Path, worker_ecr):
        registry_id, repository_uri, region = worker_ecr
        system(f'docker tag {WORKER_NAME}:latest {repository_uri}')
        system(
            f'aws ecr get-login-password | docker login --username AWS --password-stdin {registry_id}.dkr.ecr.{region}.amazonaws.com')
        system(f'docker push {repository_uri}')
        task_def = Ecs.build_task_definition_worker(f'arn:aws:iam::{registry_id}:role/ecsTaskExecutionRole',
                                                    repository_uri,
                                                    region)
        task_def_file = base_dir / 'taskdef_worker.json'
        with open(str(task_def_file), 'w') as f:
            json.dump(task_def, f)
        registered = Aws.run(f'aws ecs register-task-definition --cli-input-json file://{task_def_file}')
        return json.loads(registered)

    @staticmethod
    def prepare_controller_task_def(base_dir: Path, controller_ecr):
        # build docker image for controller
        registry_id, repository_uri, region = controller_ecr
        system(f'docker tag {CONTROLLER_NAME}:latest {repository_uri}')
        system(
            f'aws ecr get-login-password | docker login --username AWS --password-stdin {registry_id}.dkr.ecr.{region}.amazonaws.com')
        system(f'docker push {repository_uri}')
        task_def = Ecs.build_task_definition_controller(f'arn:aws:iam::{registry_id}:role/ecsTaskExecutionRole',
                                                        repository_uri, region)
        task_def_file = base_dir / 'taskdef_controller.json'
        with open(str(task_def_file), 'w') as f:
            json.dump(task_def, f)
        registered = Aws.run(f'aws ecs register-task-definition --cli-input-json file://{task_def_file}')
        return json.loads(registered)

    @staticmethod
    def run_task(cluster, task_def_name, subnet, security_group, override=None, count=1):
        cmd = f'aws ecs run-task --task-definition {task_def_name}'
        cmd += f' --cluster {cluster["clusterArn"]}'
        cmd += f' --network-configuration "awsvpcConfiguration={{subnets=[{subnet}],securityGroups=[{security_group}],assignPublicIp=ENABLED}}"'
        if override:
            cmd += f' --override \'{override}\''
        cmd += f' --launch-type FARGATE --count {count}'

        task = Aws.run(cmd)
        return json.loads(task)

    @staticmethod
    def run_worker(cluster, subnet, security_group, count=1):
        return Ecs.run_task(cluster, WORKER_NAME, subnet, security_group, count=count)

    @staticmethod
    def run_controller(cluster, subnet, security_group, arg_workers):
        override = {
            'containerOverrides': [
                {
                    "name": CONTROLLER_NAME,
                    "command": [
                        "/usr/local/bin/pipenv",
                        "run",
                        "python",
                        "tests/performance/remote_runner.py",
                        "controller",
                        arg_workers,
                    ],
                }
            ]
        }
        override_str = json.dumps(override)
        return Ecs.run_task(cluster, CONTROLLER_NAME, subnet, security_group, override=override_str, count=1)

    @staticmethod
    def describe_tasks(tasks, cluster):
        task_arns = [t['taskArn'] for t in tasks['tasks']]
        latest = Aws.run(f'aws ecs describe-tasks --tasks {" ".join(task_arns)} --cluster {cluster["clusterArn"]}')
        return json.loads(latest)

    @staticmethod
    def stop_task(task_arn, cluster):
        Aws.run(f'aws ecs stop-task --cluster {cluster["clusterArn"]} --task f{task_arn}')

class AwsContainers(AbstractContainers):
    CLUSTER_NAME = 'asobann_tests'

    def __init__(self):
        super().__init__()
        self.cluster = None
        self.worker_ecr = None
        self.controller_ecr = None

    def build_docker_images(self) -> None:
        self.cluster = Ecs.create_cluster(self.CLUSTER_NAME)
        self.worker_ecr = Aws.get_ecr(WORKER_NAME)
        self.controller_ecr = Aws.get_ecr(CONTROLLER_NAME)
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            self.prepare_docker_contents(base_path)
            self.build_docker_image_for_worker(base_path)
            Ecs.prepare_worker_task_def(base_path, self.worker_ecr)

            self.build_docker_image_for_controller(base_path)
            Ecs.prepare_controller_task_def(base_path, self.controller_ecr)

    def start_workers(self, worker_count) -> None:
        if not self.cluster:
            self.cluster = Ecs.describe_cluster(self.CLUSTER_NAME)
        log('starting workers ...')
        all_worker_tasks = {'tasks': []}
        while worker_count > 0:
            count_now = min(worker_count, 10)  # 10 is the limit of aws cli
            worker_tasks = Ecs.run_worker(self.cluster, "subnet-04d6ab48816d73c64", "sg-026a52f114ccf03f3",
                                          count=count_now)
            self._wait_for_tasks_to_be_running(worker_tasks)
            log(worker_tasks)
            all_worker_tasks['tasks'] += worker_tasks['tasks']
            log(all_worker_tasks)
            worker_count -= count_now

        worker_binds = []
        for t in Ecs.describe_tasks(all_worker_tasks, self.cluster)['tasks']:
            containers = t['containers']
            ip = containers[0]['networkInterfaces'][0]['privateIpv4Address']
            worker_binds.append((ip, 50000))

        self._workers = AbstractContainers.Workers(binds=worker_binds, tasks=all_worker_tasks)

    def start_controller(self) -> None:
        arg_worker = ','.join([f'{host}:{port}' for host, port in self._workers.binds])
        log(arg_worker)
        self.controller_task = Ecs.run_controller(self.cluster, "subnet-04d6ab48816d73c64", "sg-026a52f114ccf03f3",
                                                  arg_worker)

        log('starting controller ...')
        self._wait_for_tasks_to_be_running(self.controller_task)

        task_latest = Ecs.describe_tasks(self.controller_task, self.cluster)['tasks']
        self.controller_url = self._get_public_ip_of_controller(task_latest)

    def _wait_for_tasks_to_be_running(self, tasks):
        while True:
            time.sleep(5)
            task_latest = Ecs.describe_tasks(tasks, self.cluster)['tasks']
            statuses = [t['lastStatus'] for t in task_latest]
            log(statuses)
            if all([s == 'RUNNING' for s in statuses]):
                time.sleep(5)  # wait a bit more to avoid connection refused
                return
            if any([s == 'STOPPED' for s in statuses]):

                assert False, 'task is STOPPED unexpectedly while starting up'

    def _wait_for_tasks_to_stop(self, tasks):
        started_at = datetime.datetime.now()
        while True:
            time.sleep(5)
            task_latest = Ecs.describe_tasks(tasks, self.cluster)['tasks']
            statuses = [t['lastStatus'] for t in task_latest]
            log(statuses)
            if all([s == 'STOPPED' for s in statuses]):
                return
            if (datetime.datetime.now() - started_at).total_seconds() > 60 and \
                    any([s == 'RUNNING' for s in statuses]):
                log('force stop tasks')
                for task_arn in [t['taskArn'] for t in tasks['tasks']]:
                    Ecs.stop_task(task_arn, self.cluster)
                self._wait_for_tasks_to_stop(tasks)
                return

    def _get_public_ip_of_controller(self, task):
        eni_id = [d['value'] for d
                  in task[0]['attachments'][0]['details']
                  if d['name'] == 'networkInterfaceId'][0]
        eni = Aws.run(f'aws ec2 describe-network-interfaces --network-interface-ids {eni_id}')
        controller_ip = json.loads(eni)['NetworkInterfaces'][0]['Association']['PublicIp']
        log('controller IP address: ' + controller_ip)
        return f'http://{controller_ip}:8888'

    def shutdown(self):
        super().shutdown()
        self._wait_for_tasks_to_stop(self._workers.tasks)
        self._wait_for_tasks_to_stop(self.controller_task)

    def remove_containers(self) -> None:
        if self.cluster:
            Ecs.delete_cluster(self.CLUSTER_NAME)
        if self.worker_ecr:
            Aws.delete_ecr(WORKER_NAME)
        if self.controller_ecr:
            Aws.delete_ecr(CONTROLLER_NAME)

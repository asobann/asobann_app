import json
import os
import socket
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


CONNECTION_RETRY_SECONDS = 60


def wait_for_port(host: str, port: int, timeout_seconds: int = 30) -> None:
    """
    Block until a TCP connection to (host, port) succeeds, or raise TimeoutError.

    `docker run -d` returns as soon as the container is created, before the process
    inside it (here, remote_runner.py's multiprocessing.managers server) has actually
    started listening. Connecting before that point doesn't just fail cleanly - a
    half-ready listener can accept the TCP connection and then close it mid-handshake,
    which multiprocessing.managers surfaces as an opaque EOFError on the client side
    instead of a connection error. Waiting for the port to be genuinely acceptING
    connections avoids that race.
    """
    started_at = time.monotonic()
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            if time.monotonic() - started_at > timeout_seconds:
                raise TimeoutError(f'timed out waiting for {host}:{port} to accept connections')
            time.sleep(0.5)


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

# Extra `docker run` flags for worker/controller containers, e.g. `--network loadtest`
# to join a target app's docker-compose network, or `--cpuset-cpus=8-31` to keep them
# off the app's pinned cores (needed when measuring a CPU-constrained app locally: the
# load generators must not compete with the app for the same cores).
DOCKER_RUN_OPTS = os.environ.get('LOADTEST_DOCKER_RUN_OPTS', '')


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
        # uv.lock からの生成物(アプリ依存 + dev group)。scripts/build_e2e_image.sh 等で再生成される
        shutil.copy('./requirements-dev.txt', str(base_dir / 'runner/'))
        # pytest's whole configuration lives here (addopts, marker registration,
        # filterwarnings). Without it, running the e2e suite in this image silently
        # ignores `-m 'not loadtest'` and executes the tests that point at the long-dead
        # Heroku staging URL, which can never pass.
        shutil.copy('./pyproject.toml', str(base_dir / 'runner/'))

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
FROM python:3.14-slim-bookworm
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PYTHONPATH=/runner
RUN apt-get -y update && apt-get install -y --no-install-recommends firefox-esr curl ca-certificates && rm -rf /var/lib/apt/lists/*
RUN curl -L https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz | tar zx -C /usr/local/bin
WORKDIR /runner
COPY runner/requirements-dev.txt ./
RUN pip3 install --no-cache-dir -r requirements-dev.txt
COPY runner/ .
EXPOSE 50000 50001 50002 50003 50004 50005 50006 50007 50008 50009
CMD python tests/performance/remote_runner.py worker $PORT
    """)
        proc = system(f"docker build . -f Dockerfile_worker -t {WORKER_NAME}",
                      cwd=base_dir)
        assert proc.returncode == 0

    def build_docker_image_for_controller(self, base_dir):
        with open(Path(base_dir) / 'Dockerfile_controller', 'w') as f:
            f.write("""
FROM python:3.14-slim-bookworm
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PYTHONPATH=/runner
RUN apt-get -y update && apt-get install -y --no-install-recommends firefox-esr curl ca-certificates && rm -rf /var/lib/apt/lists/*
RUN curl -L https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz | tar zx -C /usr/local/bin
WORKDIR /runner
COPY runner/requirements-dev.txt ./
RUN pip3 install --no-cache-dir -r requirements-dev.txt
COPY runner/ .
EXPOSE 8888
    """)
        proc = system(f"docker build . -f Dockerfile_controller -t {CONTROLLER_NAME}",
                      cwd=base_dir)
        assert proc.returncode == 0

    def _wait_for_controller_to_start(self) -> None:
        started_at = time.monotonic()
        while True:
            try:
                req = urllib.request.Request(self.controller_url, method='HEAD')
                res = urllib.request.urlopen(req)
                if res.getcode() == 200:
                    break
            except (ConnectionError, urllib.error.URLError):
                if time.monotonic() - started_at > CONNECTION_RETRY_SECONDS:
                    raise TimeoutError(
                        f'controller at {self.controller_url} did not start within '
                        f'{CONNECTION_RETRY_SECONDS}s; it likely crashed on startup '
                        f'(check `docker logs` for the controller container)')
                time.sleep(1)

    def _send_command(self, command: str) -> str:
        log(f'send command url={self.controller_url}, data={command}')
        try:
            started_at = datetime.datetime.now()
            while True:
                try:
                    res = urllib.request.urlopen(self.controller_url, data=command.encode('utf8'))
                    break
                except (urllib.error.URLError, ConnectionError):
                    # A bare ConnectionError (e.g. http.client.RemoteDisconnected, raised
                    # when the controller closes the connection before sending a response -
                    # observed here right after the controller logged an internal scenario
                    # error) isn't wrapped into URLError by urllib in every code path, so it
                    # would otherwise escape this retry loop entirely and crash the caller
                    # (seen taking down shutdown() during a Step 4 run).
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

    def run_test(self, module_name, headless=True, url=None, params: Dict[str, str] = None):
        log('start controller')
        self._send_command(f'set headless {"true" if headless else "false"}')
        if url:
            self._send_command(f'set url {url}')
        for key, value in (params or {}).items():
            self._send_command(f'set {key} {value}')
        run_id = self._send_command(f'run {module_name}')
        log(f'run sent; run_id {run_id}')
        while True:
            time.sleep(5)
            result = self._send_command(f'query {run_id}')
            if result != 'still running':
                break
        log(f'result: {result}')
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
        for port in ports:
            wait_for_port('localhost', port)

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
        assert worker_count <= 10, 'Local running permits only less than 10 workers for the time being'
        ports = [50000 + i for i in range(worker_count)]  # 50000-50009 is EXPOSEd in Dockerfile
        binds = []
        for port in ports:
            log(f'start worker container port {port}')
            proc = system(
                f"docker run -d -p {port}:{port} -e PORT={port} {DOCKER_RUN_OPTS} {WORKER_NAME}",
                capture=True,
            )
            container_id = proc.stdout.strip()
            # Reach the worker via its container-internal IP, not host.docker.internal's
            # published-port hairpin route (container -> host -> back into another
            # container on the same bridge). That hairpin path is unreliable on some
            # Docker setups (observed on this machine's WSL2 docker: the controller
            # container's connection was accepted by the port-forward but then closed
            # mid-handshake, surfacing as an opaque EOFError in multiprocessing.managers).
            # Same-bridge container-to-container traffic by IP doesn't cross that path.
            ip_proc = system(
                f"docker inspect -f "
                f"'{{{{range .NetworkSettings.Networks}}}}{{{{.IPAddress}}}}{{{{end}}}}' {container_id}",
                capture=True,
            )
            internal_ip = ip_proc.stdout.strip()
            binds.append((internal_ip, port))

        self._workers = AbstractContainers.Workers(binds=binds)
        for internal_ip, port in binds:
            wait_for_port(internal_ip, port)

    def start_controller(self) -> None:
        log(f'start controller container workers {self._workers.binds}')
        arg_workers = ','.join([f'{ip}:{port}' for ip, port in self._workers.binds])
        system(f"docker run -p 8888:8888 -d {DOCKER_RUN_OPTS} {CONTROLLER_NAME} "
               f"python tests/performance/remote_runner.py controller {arg_workers}")
        self._wait_for_controller_to_start()

    def shutdown(self) -> None:
        super().shutdown()
        # Wait for the worker/controller containers specifically, not "docker ps is
        # empty" - a local run keeps a target app+mongo container up alongside the test,
        # so counting all containers never reaches zero and this used to hang forever.
        while True:
            proc = system(
                f"docker ps -q --filter ancestor={WORKER_NAME} --filter ancestor={CONTROLLER_NAME}",
                capture=True)
            assert proc.returncode == 0
            if not proc.stdout.strip():
                break
            time.sleep(1)

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
        try:
            super().shutdown()
        except:
            # force stop
            for task_arn in [t['taskArn'] for t in self._workers.tasks['tasks']]:
                Ecs.stop_task(task_arn, self.cluster)
            for task_arn in [t['taskArn'] for t in self.controller_task['tasks']]:
                Ecs.stop_task(task_arn, self.cluster)
        self._wait_for_tasks_to_stop(self._workers.tasks)
        self._wait_for_tasks_to_stop(self.controller_task)

    def remove_containers(self) -> None:
        if self.cluster:
            Ecs.delete_cluster(self.CLUSTER_NAME)
        if self.worker_ecr:
            Aws.delete_ecr(WORKER_NAME)
        if self.controller_ecr:
            Aws.delete_ecr(CONTROLLER_NAME)

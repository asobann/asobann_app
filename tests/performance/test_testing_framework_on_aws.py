from pathlib import Path
import re
import json
import os
import subprocess
import inspect
import pytest
import time
import urllib.request
from .cli import Aws, Ecs, AwsContainers, Logger
from pprint import pprint









class TestRunInMultiprocessOnAws:
    @staticmethod
    @pytest.fixture
    def worker_ecr():
        ecr = Aws.get_ecr('test_run_multiprocess_in_container_worker')
        yield ecr
        Aws.delete_ecr('test_run_multiprocess_in_container_worker')

    @staticmethod
    @pytest.fixture
    def controller_ecr():
        ecr = Aws.get_ecr('test_run_multiprocess_in_container_controller')
        yield ecr
        Aws.delete_ecr('test_run_multiprocess_in_container_controller')

    @staticmethod
    @pytest.fixture
    def cluster():
        yield Ecs.create_cluster('test-run-multiprocess-in-container')
        Ecs.delete_cluster('test-run-multiprocess-in-container')

    @staticmethod
    def run_worker(cluster, subnet, security_group, count=1):
        task = Ecs.run_task(cluster, 'test_run_multiprocess_in_container_worker', subnet, security_group, count)
        return json.loads(task)

    @staticmethod
    def run_controller(cluster, subnet, security_group):
        task = Ecs.run_task(cluster, 'test_run_multiprocess_in_container_controller', subnet, security_group, 1)
        return json.loads(task)

    @staticmethod
    def prepare_controller_task_def(tmp_path, controller_ecr, arg_worker):
        # build docker image for controller
        registryId, repositoryUri, region = controller_ecr
        proc = subprocess.run(f'docker tag test_run_multiprocess_in_container_controller:latest {repositoryUri}',
                              shell=True, encoding='utf-8')
        assert proc.returncode == 0
        proc = subprocess.run(f'docker push {repositoryUri}', shell=True, encoding='utf-8')
        assert proc.returncode == 0
        task_def = Ecs.build_task_definition_controller(f'arn:aws:iam::{registryId}:role/ecsTaskExecutionRole',
                                                    repositoryUri, region, arg_worker)
        task_def_file = tmp_path / 'taskdef_controller.json'
        with open(task_def_file, 'w') as f:
            json.dump(task_def, f)
        registered = Aws.run(f'aws ecs register-task-definition --cli-input-json file://{task_def_file}')
        return json.loads(registered)

    def test_run_multiprocess_in_aws(self, tmp_path, cluster, worker_ecr, controller_ecr):
        Logger.debug = True
        env = AwsContainers()
        worker_count = 5
        base_dir = Path(tmp_path)
        env.prepare_docker_contents(base_dir)
        env.build_docker_image_for_worker(base_dir)
        worker_task_def = Ecs.prepare_worker_task_def(base_dir, worker_ecr)

        worker_tasks = self.run_worker(cluster, "subnet-04d6ab48816d73c64", "sg-026a52f114ccf03f3", count=worker_count)
        print('starting workers ...')
        while True:
            time.sleep(5)
            statuses = [t['lastStatus'] for t in Ecs.get_tasks(worker_tasks, cluster)['tasks']]
            print(statuses)
            if all([s == 'RUNNING' for s in statuses]):
                break
            if any([s == 'STOPPED' for s in statuses]):
                assert False

        worker_ips = []
        for t in Ecs.get_tasks(worker_tasks, cluster)['tasks']:
            containers = t['containers']
            ip = containers[0]['networkInterfaces'][0]['privateIpv4Address']
            worker_ips.append(ip)

        arg_worker = ','.join([f'{ip}:50000' for ip in worker_ips])
        print(arg_worker)
        env.build_docker_image_for_controller(base_dir)
        self.prepare_controller_task_def(base_dir, controller_ecr, arg_worker)
        controller_task = self.run_controller(cluster, "subnet-04d6ab48816d73c64", "sg-026a52f114ccf03f3")

        print('starting controller ...')
        while True:
            time.sleep(5)
            statuses = [t['lastStatus'] for t in Ecs.get_tasks(controller_task, cluster)['tasks']]
            print(statuses)
            if all([s == 'RUNNING' for s in statuses]):
                break

        task = Ecs.get_tasks(controller_task, cluster)['tasks']
        print(f'controller task running: {task}')
        eni_id = [d['value'] for d in Ecs.get_tasks(controller_task, cluster)['tasks'][0]['attachments'][0]['details']
                  if d['name'] == 'networkInterfaceId'][0]
        eni = Aws.run(f'aws ec2 describe-network-interfaces --network-interface-ids {eni_id}')
        controller_ip = json.loads(eni)['NetworkInterfaces'][0]['Association']['PublicIp']
        print('send run command to ' + controller_ip)
        res = urllib.request.urlopen(f'http://{controller_ip}:8888', data=b'run tests.performance.say_hello')
        print('read response')
        result = res.read().decode('utf-8')
        print('send shutdown command')
        res = urllib.request.urlopen(f'http://{controller_ip}:8888', data=b'shutdown')

        assert result == 'Hello, container!' * worker_count

        while True:
            time.sleep(5)
            statuses = [t['lastStatus'] for t in Ecs.get_tasks(worker_tasks, cluster)['tasks']]
            if all([s == 'STOPPED' for s in statuses]):
                break
        while True:
            time.sleep(5)
            statuses = [t['lastStatus'] for t in Ecs.get_tasks(controller_task, cluster)['tasks']]
            if all([s == 'STOPPED' for s in statuses]):
                break


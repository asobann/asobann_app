from pathlib import Path
import re
import json
import os
import subprocess
import inspect
import pytest
import time
import urllib.request
from .cli import Aws, Ecs, AwsContainers, Logger, CONTROLLER_NAME, WORKER_NAME
from pprint import pprint









class TestRunInMultiprocessOnAws:
    @staticmethod
    @pytest.fixture
    def worker_ecr():
        ecr = Aws.get_ecr(WORKER_NAME)
        yield ecr
        # Aws.delete_ecr(WORKER_NAME)

    @staticmethod
    @pytest.fixture
    def controller_ecr():
        ecr = Aws.get_ecr(CONTROLLER_NAME)
        yield ecr
        # Aws.delete_ecr(CONTROLLER_NAME)

    @staticmethod
    @pytest.fixture
    def cluster():
        yield Ecs.create_cluster('test-run-multiprocess-in-container')
        # Ecs.delete_cluster('test-run-multiprocess-in-container')


    def test_run_multiprocess_in_aws(self, tmp_path, worker_ecr, controller_ecr):
        Logger.debug = True
        env = AwsContainers()
        env.build_docker_images()
        cluster = env.cluster

        env.start_workers(3)
        env.start_controller()

        print('send run command to ' + env.controller_url)
        result = env.run_test('tests.performance.say_hello')
        print('send shutdown command')
        env.shutdown()

        assert result == 'Hello, container!' * 5


import sys
from pprint import pprint

import typer

from .framework import Logger, AbstractContainers, LocalContainers, AwsContainers


def do_run(name: str, env: 'AbstractContainers'):
    env.build_docker_images()
    env.start_workers(3)
    env.start_controller()
    result = env.run_test(name)
    env.shutdown()

    pprint(result)


def run(name: str, local: bool = False, aws: bool = False, debug: bool = False):
    Logger.debug = debug
    if local:
        env = LocalContainers()
    elif aws:
        env = AwsContainers()
    else:
        print('Either --local or --aws option must be specified', file=sys.stderr)
        exit(1)
    do_run(name, env=env)


if __name__ == '__main__':
    typer.run(run)

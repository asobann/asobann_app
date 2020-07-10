import sys
from pprint import pprint

import typer

from .framework import Logger, AbstractContainers, LocalContainers, AwsContainers


app = typer.Typer()


def do_run(name: str, env: 'AbstractContainers'):
    env.start_workers(3)
    env.start_controller()
    result = env.run_test(name)
    env.shutdown()

    pprint(result)


def containers_instance(local, aws):
    if local:
        return LocalContainers()
    elif aws:
        return AwsContainers()
    else:
        print('Either --local or --aws option must be specified', file=sys.stderr)
        exit(1)


@app.command()
def run(name: str, local: bool = False, aws: bool = False, debug: bool = False, provision: bool = False):
    Logger.debug = debug
    env = containers_instance(local, aws)

    if provision:
        env.build_docker_images()
    do_run(name, env=env)


@app.command()
def provision(local: bool = False, aws: bool = False, debug: bool = False):
    Logger.debug = debug
    env = containers_instance(local, aws)
    env.build_docker_images()


@app.command()
def teardown(local: bool = False, aws: bool = False, debug: bool = False):
    Logger.debug = debug
    env = containers_instance(local, aws)
    env.remove_containers()


if __name__ == '__main__':
    app()

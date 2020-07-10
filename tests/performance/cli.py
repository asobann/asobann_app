import sys
from pprint import pprint

import typer

from .framework import Logger, AbstractContainers, LocalProcesses, LocalContainers, AwsContainers

app = typer.Typer()


def do_run(name: str, env: 'AbstractContainers', headless: bool):
    env.start_workers(3)
    env.start_controller()
    try:
        result = env.run_test(name, headless=headless)
    finally:
        env.shutdown()

    pprint(result)


def containers_instance(local, docker, aws):
    if local:
        return LocalProcesses()
    elif docker:
        return LocalContainers()
    elif aws:
        return AwsContainers()
    else:
        print('Either --local, --docker or --aws option must be specified', file=sys.stderr)
        exit(1)


@app.command()
def run(name: str, local: bool = False, docker: bool = False, aws: bool = False, debug: bool = False,
        provision: bool = False, headless: bool = True):
    Logger.debug = debug
    env = containers_instance(local, docker, aws)

    if provision:
        env.build_docker_images()
    do_run(name, env=env, headless=headless)


@app.command()
def provision(local: bool = False, docker: bool = False, aws: bool = False, debug: bool = False):
    Logger.debug = debug
    env = containers_instance(local, docker, aws)
    env.build_docker_images()


@app.command()
def teardown(local: bool = False, docker: bool = False, aws: bool = False, debug: bool = False):
    Logger.debug = debug
    env = containers_instance(local, docker, aws)
    env.remove_containers()


if __name__ == '__main__':
    app()

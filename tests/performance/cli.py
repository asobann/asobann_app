import sys
from pprint import pprint

import typer

from .framework import Logger, AbstractContainers, LocalProcesses, LocalContainers, AwsContainers

app = typer.Typer()


def do_run(name: str, workers: int, env: 'AbstractContainers', headless: bool, url: str):
    env.start_workers(workers)
    env.start_controller()
    try:
        result = env.run_test(name, headless=headless, url=url)
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
def run(name: str, workers:int, local: bool = False, docker: bool = False, aws: bool = False, debug: bool = False,
        provision: bool = False, headless: bool = True, url: str = None):
    Logger.debug = debug
    env = containers_instance(local, docker, aws)

    if provision:
        env.build_docker_images()
    do_run(name, workers=workers, env=env, headless=headless, url=url)


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

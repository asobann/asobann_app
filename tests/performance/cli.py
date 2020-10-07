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


def containers_instance(run_on):
    if run_on == 'local':
        return LocalProcesses()
    elif run_on == 'docker':
        return LocalContainers()
    elif run_on == 'aws':
        return AwsContainers()
    else:
        print('Either --local, --docker or --aws option must be specified', file=sys.stderr)
        exit(1)


@app.command()
def run(name: str = typer.Argument(..., help='Name of tests in package.subpackage.module format.'),
        workers: int = typer.Argument(...,
                                      help='Number of workers.  Effect of number of workers depends on what test to run.'),
        run_on: str = typer.Option(default='local',
                                   help='The environment where the test is run.  One of local / docker /aws. '),
        debug: bool = False,
        build_image: bool = False,
        headless: bool = True,
        url: str = typer.Option(default=None,
                                help="Target web application's base URL.  ex) https://dev.asobann.yattom.jp")
        ):
    """
    Run specified test.

    ex) python -m tests.performance.cli run tests.performance.move_and_remove_kit 3 --run-on local --build-image --url https://asobann.yattom.jp
    """
    Logger.debug = debug
    env = containers_instance(run_on)

    if build_image:
        env.build_docker_images()
    do_run(name, workers=workers, env=env, headless=headless, url=url)


@app.command()
def build_image(run_on: str = typer.Option(default='local',
                                         help='The environment where the test is run.  One of local / docker /aws. '),
              debug: bool = False):
    Logger.debug = debug
    env = containers_instance(run_on)
    env.build_docker_images()


@app.command()
def teardown(run_on: str = typer.Option(default='local',
                                        help='The environment where the test is run.  One of local / docker /aws. '),
             debug: bool = False):
    Logger.debug = debug
    env = containers_instance(run_on)
    env.remove_containers()


if __name__ == '__main__':
    app()

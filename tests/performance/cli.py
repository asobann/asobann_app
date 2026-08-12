import json
import sys
from pprint import pprint
from typing import List, Optional

import typer

from .framework import Logger, AbstractContainers, LocalProcesses, LocalContainers, AwsContainers

app = typer.Typer()


def parse_params(param: List[str]) -> dict:
    params = {}
    for entry in param:
        key, _, value = entry.partition('=')
        if not _:
            raise ValueError(f'--param must be in key=value format, got "{entry}"')
        params[key] = value
    return params


def do_run(name: str, workers: int, env: 'AbstractContainers', headless: bool, url: str,
           params: dict = None, output: str = None):
    env.start_workers(workers)
    env.start_controller()
    try:
        result = env.run_test(name, headless=headless, url=url, params=params or {})
    finally:
        try:
            env.shutdown()
        except Exception as shutdown_ex:
            # A run can complete and hand back a valid result even when the containers
            # end up in a state where tearing them down raises (observed: `shutdown`
            # racing the controller's own exit after a 30-minute run finished cleanly).
            # Letting that exception propagate from `finally` would silently discard an
            # already-obtained `result` - not worth 30 minutes of load data. Cleanup
            # failing is a real problem (containers may be left running) but a strictly
            # secondary one to losing the result, so just report it instead of raising.
            print(f'warning: env.shutdown() failed, containers may be left running: {shutdown_ex!r}',
                  file=sys.stderr)

    pprint(result)
    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)


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
                                help="Target web application's base URL.  ex) https://dev.asobann.yattom.jp"),
        param: List[str] = typer.Option(default=[],
                                        help="Extra key=value parameter passed to the scenario. May be repeated."),
        output: Optional[str] = typer.Option(default=None,
                                             help="Write the result JSON to this file, in addition to printing it.")
        ):
    """
    Run specified test.

    ex) python -m tests.performance.cli run tests.performance.move_and_remove_kit 3 --run-on local --build-image --url https://asobann.yattom.jp
    ex) python -m tests.performance.cli run tests.performance.sustained_load 10 --run-on docker --url https://staging.asobann.yattom.jp --param duration_seconds=1800 --param mousemove_hz=30 --output results/run.json
    """
    Logger.debug = debug
    env = containers_instance(run_on)

    if build_image:
        env.build_docker_images()
    do_run(name, workers=workers, env=env, headless=headless, url=url, params=parse_params(param), output=output)


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

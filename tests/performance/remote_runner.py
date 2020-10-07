import json
import sys
import datetime
import queue
from threading import Thread
from typing import Dict, Any

import random

random.seed()
AUTHKEY = b'noscret'


def log(*args):
    print(*args)
    sys.stdout.flush()


def worker_server(port):
    """
    This will run on remote host or container.
    """
    from multiprocessing.managers import BaseManager
    from multiprocessing import Queue
    command_queue = Queue()
    result_queue = Queue()

    class MyManager(BaseManager):
        pass

    log('running worker_server')
    MyManager.register('command_que', callable=lambda: command_queue)
    MyManager.register('result_que', callable=lambda: result_queue)
    mgr = MyManager(address=('', port), authkey=AUTHKEY)
    mgr.start()

    name = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(10)])
    while True:
        log('receiving cmd...')
        cmd = command_queue.get()
        log(f'received {cmd}')
        if cmd[0] == 'name':
            name = cmd[1]
        elif cmd[0] == 'run':
            module_name = cmd[1]
            parameters = cmd[2]
            import importlib
            mod = importlib.import_module(module_name, '.')
            try:
                mod.execute_worker(name, command_queue, result_queue, parameters)
            except Exception as ex:
                import traceback
                import io
                buf = io.StringIO()
                traceback.print_exc(file=buf)
                try:
                    result_queue.put({
                        'error': {
                            'worker_name': name,
                            'cause': buf.getvalue(),
                        }})
                except:
                    pass
                log(f'worker raised an exception: {ex} {ex.args}')
                mgr.shutdown()
                break
            log('worker is finished')
        elif cmd[0] == 'shutdown':
            log('shutting down ...')
            mgr.shutdown()
            break


def controller_client(workers):
    from multiprocessing.managers import BaseManager

    class MyManager(BaseManager):
        pass

    log('running controller_client')
    MyManager.register('command_que')
    MyManager.register('result_que')
    command_queues = []
    result_queues = []
    for host, port in workers:
        mgr = MyManager(address=(host, int(port)), authkey=AUTHKEY)
        mgr.connect()
        command_queues.append(mgr.command_que())
        result_queues.append(mgr.result_que())
        mgr.command_que().put(['name', f'{host}:{port}'])
    log(f'connected to {len(command_queues)} workers')

    httpd = None

    controller_status: Dict[str, Any] = {
        'status': 'not started',
        'module_name': None,
        'run_id': None,
        'started_at': None,
        'result': None,
    }

    def start_controller(module_name):
        def run():
            log('controller thread started')
            controller_status['started_at'] = datetime.datetime.now()
            import importlib
            mod = importlib.import_module(module_name, '.')
            try:
                result = mod.execute_controller(command_queues[:], result_queues[:], parameters)
                controller_status['result'] = result
                controller_status['status'] = 'finished'
                log('controller thread finished')
            except:
                left_in_queues = []
                for q in command_queues + result_queues:
                    try:
                        while not q.empty():
                            left_in_queues.append(q.get(block=False))
                    except (queue.Empty, EOFError, BrokenPipeError):
                        continue
                import traceback
                import io
                buf = io.StringIO()
                traceback.print_exc(file=buf)
                controller_status['result'] = {
                    'exception': buf.getvalue(),
                    'left_in_queues': left_in_queues,
                }
                controller_status['status'] = 'error'
                log('controller thread caught exception')

        controller_status['module_name'] = module_name
        controller_status['run_id'] = str(datetime.datetime.now().timestamp())
        controller_status['status'] = 'running'
        Thread(target=run).start()

    def shutdown_httpd():
        Thread(target=lambda: httpd.shutdown()).start()

    import http.server

    parameters = {
        'headless': True,
    }

    class ControllerHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

        def do_POST(self):
            length = self.headers.get('content-length')
            nbytes = int(length)
            command = self.rfile.read(nbytes).decode('utf8')
            log(f'received cmd "{command}"')

            if command.startswith('run '):
                args = command.split(' ')
                module_name = args[1]
                log(f'starting testcase {module_name} ...')
                for que in command_queues:
                    que.put(['run', module_name, parameters])

                start_controller(module_name)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(controller_status['run_id'].encode('utf8'))
                return
            elif command.startswith('query '):
                run_id = command.split(' ')[1]
                if controller_status['run_id'] != run_id:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write('wrong run_id'.encode('utf8'))
                    return

                if controller_status['status'] == 'error':
                    log(controller_status['result'])
                    self.send_response(500)
                    self.end_headers()
                    result = {
                        'status': 'error',
                        'controller': controller_status['result'],
                    }
                    self.wfile.write(json.dumps(result).encode('utf8'))
                    return

                if controller_status['status'] != 'finished':
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write('still running'.encode('utf8'))
                    return

                left_in_queues = []
                for q in command_queues + result_queues:
                    try:
                        while not q.empty():
                            left_in_queues.append(q.get(block=False))
                    except (queue.Empty, EOFError, BrokenPipeError):
                        continue

                finished_at = datetime.datetime.now()
                self.send_response(200)
                self.end_headers()
                resp = {
                    'name': controller_status['module_name'],
                    'result': controller_status['result'],
                    'left_in_queues': left_in_queues,
                    'time': {
                        'started_at': controller_status['started_at'].ctime(),
                        'finished_at': finished_at.ctime(),
                        'elapsed': (finished_at - controller_status['started_at']).total_seconds(),
                    }
                }
                log(f'response: {resp}')
                self.wfile.write(json.dumps(resp).encode('utf8'))
                log('response sent')
                return

            elif command.startswith('set '):
                _, key, value = command.split(' ')
                key = key.strip()
                value = value.strip()

                if value == 'true':
                    parsed_value = True
                elif value == 'false':
                    parsed_value = False
                else:
                    try:
                        parsed_value = int(value)
                    except ValueError:
                        parsed_value = value

                parameters[key] = parsed_value
                self.send_response(200)
                self.end_headers()
                self.wfile.write(f'headless is set to {parameters["headless"]}'.encode('utf8'))
                return

            elif command == 'shutdown':
                log('shutdown controller and workers')
                try:
                    for que in command_queues:
                        que.put(['shutdown'])
                    log('shutdown sent to the workers')
                    self.send_response(200)
                    self.end_headers()
                    self.flush_headers()
                    return
                finally:
                    shutdown_httpd()
                    log('shutdown httpd')
                    log('exiting ...')
                    exit()

    log('starting http server')
    addr = ('', 8888)
    httpd = http.server.HTTPServer(addr, ControllerHTTPRequestHandler)
    httpd.serve_forever()


if __name__ == '__main__':
    if sys.argv[1] == 'worker':
        port = int(sys.argv[2])
        log(f'start worker port {port}')
        worker_server(port)
    if sys.argv[1] == 'controller':
        workers = [p.split(':') for p in sys.argv[2].split(',')]
        log(f'start controller workers {workers}')
        controller_client(workers)

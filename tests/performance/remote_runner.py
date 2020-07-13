import json
import sys
import datetime

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
    headless = True
    while True:
        log('receiving cmd...')
        cmd = command_queue.get()
        log(f'received {cmd}')
        if cmd[0] == 'name':
            name = cmd[1]
        elif cmd[0] == 'run':
            module_name = cmd[1]
            import importlib
            mod = importlib.import_module(module_name, '.')
            mod.execute_worker(name, command_queue, result_queue, headless)
            log('worker is finished')
        elif cmd[0] == 'shutdown':
            log('shutting down ...')
            mgr.shutdown()
            break
        elif cmd[0] == 'headless':
            headless = cmd[1]


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

    def shutdown_httpd():
        from threading import Thread
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
                for queue in command_queues:
                    queue.put(['run', module_name])

                try:
                    started_at = datetime.datetime.now()
                    import importlib
                    mod = importlib.import_module(module_name, '.')
                    result = mod.execute_controller(command_queues[:], result_queues[:], parameters['headless'])
                    finished_at = datetime.datetime.now()
                    self.send_response(200)
                    self.end_headers()
                    resp = {
                        'name': module_name,
                        'result': result,
                        'time': {
                            'started_at': started_at.ctime(),
                            'finished_at': finished_at.ctime(),
                            'elapsed': (finished_at - started_at).total_seconds(),
                        }
                    }
                    log(f'response: {resp}')
                    self.wfile.write(json.dumps(resp).encode('utf8'))
                    log('response sent')
                except:
                    import traceback
                    import io
                    buf = io.StringIO()
                    traceback.print_exc(file=buf)
                    self.send_response(500)
                    self.end_headers()
                    print(buf.getvalue())
                    self.wfile.write(buf.getvalue().encode('utf8'))
                    return

            elif command.startswith('headless '):
                args = command.split(' ')
                parameters['headless'] = True if args[1] == 'true' else False
                for queue in command_queues:
                    queue.put(['headless', parameters['headless']])
                self.send_response(200)
                self.end_headers()
                self.wfile.write(f'headless is set to {parameters["headless"]}'.encode('utf8'))
            elif command == 'shutdown':
                log('shutdown controller and workers')
                for queue in command_queues:
                    queue.put(['shutdown'])
                log('shutdown sent to the workers')
                self.send_response(200)
                self.end_headers()
                self.flush_headers()
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

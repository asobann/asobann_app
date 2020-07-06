import re
import json

import random
random.seed()
AUTHKEY = b'noscret'


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

    print('running worker_server')
    MyManager.register('command_que', callable=lambda: command_queue)
    MyManager.register('result_que', callable=lambda: result_queue)
    mgr = MyManager(address=('', port), authkey=AUTHKEY)
    mgr.start()

    name = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(10)])
    while True:
        print('receiving cmd...')
        cmd = command_queue.get()
        print(f'received {cmd}')
        if cmd[0] == 'name':
            name = cmd[1]
        elif cmd[0] == 'run':
            module_name = cmd[1]
            import importlib
            mod = importlib.import_module(module_name, '.')
            mod.execute_worker(name, command_queue, result_queue)
        elif cmd[0] == 'shutdown':
            mgr.shutdown()
            break


def controller_client(workers):
    from multiprocessing.managers import BaseManager

    class MyManager(BaseManager):
        pass

    print('running controller_client')
    import sys
    sys.stdout.flush()
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
    print('connected to workers')

    import http.server
    class ControllerHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

        def do_POST(self):
            try:
                length = self.headers.get('content-length')
                nbytes = int(length)
                command = self.rfile.read(nbytes).decode('utf8')
                print(f'received cmd "{command}"')
                sys.stdout.flush()

                if command.startswith('run '):
                    module_name = command.split(' ')[1]
                    print(f'starting testcase {module_name}...')
                    sys.stdout.flush()

                    for queue in command_queues:
                        queue.put(['run', module_name])

                    import importlib
                    mod = importlib.import_module(module_name, '.')
                    mod.execute_controller(command_queues, result_queues)

                    print('receiving result...')
                    sys.stdout.flush()
                    result = []
                    for queue in result_queues:
                        result.append(queue.get())

                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode('utf8'))
                    print('response sent')
                    sys.stdout.flush()
                elif command == 'shutdown':
                    print('shutdown controller and workers')
                    sys.stdout.flush()
                    for queue in command_queues:
                        queue.put(['shutdown'])

                    self.send_response(200)
                    self.end_headers()
                    self.flush_headers()
                    exit()
            except:
                import traceback
                traceback.print_exc()
                sys.stdout.flush()
                sys.stderr.flush()
                raise

    print('starting http server')
    sys.stdout.flush()
    addr = ('', 8888)
    httpd = http.server.HTTPServer(addr, ControllerHTTPRequestHandler)
    httpd.serve_forever()


if __name__ == '__main__':
    import sys

    if sys.argv[1] == 'worker':
        port = int(sys.argv[2])
        print(f'start worker port {port}')
        worker_server(port)
    if sys.argv[1] == 'controller':
        workers = [p.split(':') for p in sys.argv[2].split(',')]
        print(f'start controller workers {workers}')
        controller_client(workers)

AUTHKEY = b'noscret'


def worker_server(port):
    '''
    This will run on remote host or container.
    '''
    from multiprocessing.managers import BaseManager
    from multiprocessing import Queue
    command_queue = Queue()
    result_queue = Queue()

    class MyManager(BaseManager):
        pass

    MyManager.register('command_que', callable=lambda: command_queue)
    MyManager.register('result_que', callable=lambda: result_queue)
    mgr = MyManager(address=('', port), authkey=AUTHKEY)
    mgr.start()

    while True:
        cmd = command_queue.get()
        if cmd == 'run':
            result_queue.put('Hello, container!')
        if cmd == 'shutdown':
            mgr.shutdown()
            break


def controller_client(workers):
    from multiprocessing.managers import BaseManager

    class MyManager(BaseManager):
        pass

    MyManager.register('command_que')
    MyManager.register('result_que')
    command_queues = []
    result_queues = []
    for host, port in workers:
        mgr = MyManager(address=(host, int(port)), authkey=AUTHKEY)
        mgr.connect()
        command_queues.append(mgr.command_que())
        result_queues.append(mgr.result_que())

    for queue in command_queues:
        queue.put('run')

    for queue in result_queues:
        print(queue.get())

    for queue in command_queues:
        queue.put('shutdown')


if __name__ == '__main__':
    import sys

    if sys.argv[1] == 'worker':
        port = int(sys.argv[2])
        worker_server(port)
    if sys.argv[1] == 'controller':
        workers = [p.split(':') for p in sys.argv[2].split(',')]
        controller_client(workers)

def execute_controller(command_queues, result_queues):
    for queue in command_queues:
        queue.put('run')

    result = []
    for queue in result_queues:
        result.append(queue.get())
    return result


def execute_worker(name, command_queue, result_queue):
    command_queue.get()
    result_queue.put(f'Hello, container! from {name}')


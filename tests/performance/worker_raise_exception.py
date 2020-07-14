def execute_controller(command_queues, result_queues, headless):
    for queue in command_queues:
        queue.put('run')

    result = []
    for queue in result_queues:
        result.append(queue.get())
    return result


def execute_worker(name, command_queue, result_queue, headless):
    command_queue.get()
    raise RuntimeError('Some Error In Worker')


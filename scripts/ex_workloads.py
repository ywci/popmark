WORKLOADS = {
    'client': {
        'workloads': [
            {'workload0': {'cmd': 'ex_client --client_result1 21 --client_result2 22 --output /tmp/client_results'}},
            {'workload1': {'cmd': 'ex_client --client_result1 23 --client_result2 24 --output /tmp/client_results'}},
        ],
        'start': 'ex_client_start.sh',
        'stop': 'ex_client_stop.sh'
    },
    'server': {
        'workloads': [
            {'workload0': {'cmd': 'ex_server --server_result1 11 --server_result2 12 --output /tmp/server_results'}},
            {'workload1': {'cmd': 'ex_server --server_result1 13 --server_result2 14 --output /tmp/server_results'}},
        ],
        'start': 'ex_server_start.sh',
        'stop': 'ex_server_stop.sh'
    },
    'runner': {
        'workloads': [
            {'workload0': {'cmd': 'ex_runner --runner_result1 31 --runner_result2 32 --output /tmp/runner_results'}},
            {'workload1': {'cmd': 'ex_runner --runner_result1 33 --runner_result2 34 --output /tmp/runner_results'}},
        ],
        'start': 'ex_runner_start.sh',
        'stop': 'ex_runner_stop.sh'
    },
    'collector': {
        'outputs': {
            '/tmp/client_results': ['client_result1', 'client_result2'],
            '/tmp/server_results': ['server_result1', 'server_result2'],
            '/tmp/runner_results': ['runner_result1', 'runner_result2']
        }
    },
    'roles': {
        'client': ['127.0.0.1'],
        'server': ['127.0.0.1'],
        'runner': ['127.0.0.1'],
        'collector': ['127.0.0.1']
    },
    'repeats': 3,
    'reboot': False
}

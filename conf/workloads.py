WORKLOADS = {
    'client': {
        # List of dictionaries containing workload names and their corresponding command paths
        'workloads': [],
        
        # Script used before testing (put it into the 'scripts' directory or provide an absolute path)
        'start': '',
        
        # Script used after testing (put it into the 'scripts' directory or provide an absolute path)
        'stop': ''
    },
    
    'server': {
        # List of dictionaries containing workload names and their corresponding command paths
        'workloads': [],
        
        # Script used before testing (put it into the 'scripts' directory or provide an absolute path)
        'start': '',
        
        # Script used after testing (put it into the 'scripts' directory or provide an absolute path)
        'stop': ''
    },
    
    'runner': {
        # List of dictionaries containing workload names and their corresponding command paths
        'workloads': [],
        
        # Script used before testing (put it into the 'scripts' directory or provide an absolute path)
        'start': '',
        
        # Script used after testing (put it into the 'scripts' directory or provide an absolute path)
        'stop': ''
    },
    
    'collector': {
        # Dictionary mapping output paths to parameter lists
        'outputs': {}
    },
    
    'roles': {
        # Address list of clients
        'client': [],
        
        # Address list of servers
        'server': [],
        
        # Address list of runners
        'runner': [],
        
        # Address list of collectors
        'collector': []
    },
    
    # Number of times to repeat each workload
    'repeats': 1,
    
    # Reboot members after each test
    'reboot': False
}

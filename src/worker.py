import time
from util import *
from copy import copy
from popmark import *
from workloads import WORKLOADS

class Worker(object):
    def __init__(self, role, start=0, repeats=0):
        if os.path.exists(FILE_LOG):
            os.remove(FILE_LOG)
        
        nr_repeats = WORKLOADS['repeats']
        if nr_repeats == None:
            log_file_err('the repeat times must be set')
        
        if role not in [SERVER, CLIENT, RUNNER]:
            log_file_err('this is an invalid role %s' % str(role))
        
        addr = get_addr()
        if not addr:
            log_file_err('only members can be set as workers')
        
        if start < 0 or start > len(WORKLOADS[role]['workloads']):
            log_file_err('cannot start %s from number %s workload' % (role, start))

        nr_client_workloads = len(WORKLOADS['client']['workloads'])
        nr_server_workloads = len(WORKLOADS['server']['workloads'])
        nr_runner_workloads = len(WORKLOADS['runner']['workloads'])
        self._workload_max = max(nr_client_workloads, nr_server_workloads, nr_runner_workloads)
        self._has_client = nr_client_workloads > 0
        self._has_server = nr_server_workloads > 0
        self._has_runner = nr_runner_workloads > 0
        
        if self._has_client and self._workload_max != nr_client_workloads:
            log_file_err('invalid client workloads')
        
        if self._has_server and self._workload_max != nr_server_workloads:
            log_file_err('invalid server workloads')
        
        if self._has_runner and self._workload_max != nr_runner_workloads:
            log_file_err('invalid runner workloads')
        
        if role not in WORKLOADS['roles'] or addr not in WORKLOADS['roles'][role]:
            log_file_err('invalid addr %s for %s' % (addr, role))
        
        self._role_id = WORKLOADS['roles'][role].index(addr)
        self._role = role
        self._addr = addr
        self._start = start
        self._progress = {}
        self._process = None
        self._repeats = repeats
        self._collect = addr in WORKLOADS['roles']['collector']
        if self._collect:
             for i in [CLIENT, SERVER, RUNNER]:
                 if addr in WORKLOADS['roles'][i]:
                     if i != role:
                         self._collect = False
                     break
     
    def _get_req_addr(self):
        return req_addr(MANAGER_ADDR, MANAGER_PORT)
    
    def _get_name(self):
        workloads = WORKLOADS[self._role]['workloads']
        if workloads and self._start < len(workloads):
            return list(workloads[self._start].keys())[0]
    
    def _get_workload(self):
        prepare = WORKLOADS[self._role].get('start')
        finalize = WORKLOADS[self._role].get('stop')
        workloads = WORKLOADS[self._role]['workloads']
        if workloads and self._start < len(workloads):
            name = self._get_name()
            workload = copy(workloads[self._start][name])
            if not workload.get('cmd'):
                log_file('[%s]: failed to find cmd of workload "%s"' % (self._role, name))
                raise Exception('failed to find cmd of workload "%s"' % name)
            param = workload.get('param')
            if param:
                if len(param) != len(WORKLOADS['roles'][self._role]):
                    log_file('[%s]: failed to individually set parameter for workload "%s"' % (self._role, name))
                    raise Exception('failed to find cmd of workload "%s"' % name)
                workload['cmd'] = "%s %s" % (workload['cmd'], param[self._role_id])
            if prepare:
                workload['cmd'] = "%s;%s" % (prepare, workload['cmd'])
            if finalize:
                workload['cmd'] = "%s;%s" % (workload['cmd'], finalize)
            log_file('[%s] cmd="%s" workload=%s (%s: %s/%s)' % (self._role, workload['cmd'], name, self._start, self._repeats + 1, WORKLOADS['repeats']))
            return (name, workload)
        else:
            return (None, None)
    
    def _get_args(self):
        name = self._get_name()
        return (self._addr, self._role, self._start, self._repeats, name)
    
    def _get_results(self):
        return check_results()
    
    def _request(self, req):
        if self._start not in self._progress:
            self._progress.update({self._start: -1}) 
        if self._repeats != self._progress[self._start]:
            self._progress[self._start] = self._repeats
        addr = self._get_req_addr()
        cli = create_client()
        cli.connect(addr)
        try:
            if req in [BEGIN, ENTER, READY, END]:
                args = self._get_args()
                ret = cli.request(req, *args)
            elif req == EXIT:
                args = self._get_args()
                results = self._get_results() if self._collect else None
                ret = cli.request(req, *args, results)
            else:
                raise Exception('invalid request %s' % str(req))
        finally:
            cli.close()
        return ret
    
    def _launch(self, cmd):
        self._process = launch(self._role, cmd)
    
    def _terminate(self):
        self._process.terminate()
    
    def run(self):        
        while True:
            name, workload = self._get_workload()
            if not name:
                log_file("[%s] finished" % self._role)
                break
            else:
                clear_results()
            
            while not self._request(BEGIN):
                time.sleep(1)
            
            if self._role == SERVER:
                log_file("[%s] %s ==> %s" % (self._role, str(name), str(workload['cmd'])))
                self._launch(workload['cmd'])
            
            while not self._request(ENTER):
                time.sleep(1)
            
            if self._role == CLIENT:
                log_file("[%s] %s ==> %s" % (self._role, str(name), str(workload['cmd'])))
                self._launch(workload['cmd'])
            
            while not self._request(READY):
                pass
            
            if self._role == RUNNER:
                log_file("[%s] %s ==> %s" % (self._role, str(name), str(workload['cmd'])))
                self._launch(workload['cmd'])
            
            self._request(EXIT)
            log_file("[%s] %s ==> start=%d, repeats=%d (%s)" % (self._role, str(name), self._start, self._repeats, EXIT))
            while not self._request(END):
                time.sleep(1)
            
            self._repeats = self._repeats + 1
            if self._repeats == WORKLOADS['repeats']:
                self._start = self._start + 1
                self._repeats = 0
            
            if WORKLOADS['reboot']:
                reboot()
            else:
                self._terminate()

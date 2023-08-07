import os
from util import *
from popmark import *
from defaults import *
from workloads import *
from shutil import rmtree
from threading import Lock, Thread

class Manager(object):
    def __init__(self, start=0):
        kill_defunct_processes()
        nr_client_workloads = len(WORKLOADS['client']['workloads'])
        nr_server_workloads = len(WORKLOADS['server']['workloads'])
        nr_runner_workloads = len(WORKLOADS['runner']['workloads'])
        self._workload_max = max(nr_client_workloads, nr_server_workloads, nr_runner_workloads)
        if self._workload_max == 0:
            raise Exception('no workloads')
        
        self._has_client = nr_client_workloads > 0
        self._has_server = nr_server_workloads > 0
        self._has_runner = nr_runner_workloads > 0
        if self._has_client and self._workload_max != nr_client_workloads:
            raise Exception('invalid client workloads')
        if self._has_server and self._workload_max != nr_server_workloads:
            raise Exception('invalid server workloads')
        if self._has_runner and self._workload_max != nr_runner_workloads:
            raise Exception('invalid runner workloads')
        
        self._stat = {}
        self._uptime = {}
        self._params = []
        self._results = {}
        self._lock = Lock()
        self._start = start
        self._workloads = []
        self._repeat_max = WORKLOADS['repeats']
        
        self._clean_output()
        for i in range(self._workload_max):
            if self._has_server:
                workload = self._get_workload(i, SERVER)
                if self._has_client and workload != self._get_workload(i, CLIENT):
                    raise Exception('the server workloads are not matched with the client workloads')
                if self._has_runner and workload != self._get_workload(i, RUNNER):
                    raise Exception('the server workloads are not matched with the runner workloads')
                self._workloads.append(workload)
            else:
                if self._has_runner:
                    workload = self._get_workload(i, RUNNER)
                elif self._has_client:
                    workload = self._get_workload(i, CLIENT)
                else:
                    raise Exception('no workload specified')
                self._workloads.append(workload)
                
        if not self._repeat_max:
            raise Exception('repeat times must be set')
            
        for i in WORKLOADS['collector']['outputs']:
            for j in WORKLOADS['collector']['outputs'][i]:
                if j not in self._params:
                    self._params.append(j)
                else:
                    raise Exception('%s appears in different outputs' % j)
        
        for i in WORKLOADS['roles']['collector']:
            match = False
            for role in [CLIENT, SERVER, RUNNER]:
                if i in WORKLOADS['roles'][role]:
                    match = True
                    break
            if not match:
                raise Exception('collector %s should be a client/server/runner')
        
        if WORKLOADS['reboot'] and MANAGER_ADDR not in get_members():
            reboot_members()
        check_members()
        self._uptime = get_uptime()
        reset()
        start_members(self._start, 0)
    
    def _clean_output(self, clean=True):
        if clean:
            rmtree(OUTPUTS, ignore_errors=True)
        if not os.path.exists(OUTPUTS):
            os.mkdir(OUTPUTS)
    
    def _log(self, s):
        if LOG:
            log("[popmark] %s" % s)
    
    def _check_results(self, workload, results):
        if workload not in self._results:
            self._results.update({workload: {}})
        for i in results:
            if self._params and i not in self._params:
                raise Exception('invalid result with name %s' % i)
            if i not in self._results[workload]:
                self._results[workload].update({i: []})
            self._results[workload][i].append(results[i])
    
    def _check_state(self, req, addr, role, start, repeats):
        if req not in REQ:
            raise Exception('invalid request %s' % str(req))
        if start > self._start and req != BEGIN:
            raise Exception('invalid state, req=%s, cannot start from %s (current=%s)' % (req, start, self._start))
        if role not in [SERVER, CLIENT, RUNNER]:
            raise Exception('invalid role %s, req=%s' % (str(role), req))
        if role not in self._stat:
            self._stat.update({role: {}})
        if start not in self._stat[role]:
            self._stat[role].update({start: {}})
        if repeats not in self._stat[role][start]:
            self._stat[role][start].update({repeats: {}})
        if req not in self._stat[role][start][repeats]:
            self._stat[role][start][repeats].update({req: []})
        if addr not in self._stat[role][start][repeats][req]:
            self._stat[role][start][repeats][req].append(addr)
            if SHOW_STATE:
                self._log('%s@%s => %s (%s: %s/%s)' % (role, addr, req.lower(), start, repeats + 1, self._repeat_max))
    
    def _can_continue(self, req, start, repeats):
        for i in [CLIENT, SERVER, RUNNER]:
            if not WORKLOADS[i]['workloads']:
                continue
            elif i not in self._stat \
                or start not in self._stat[i] \
                or repeats not in self._stat[i][start] \
                or req not in self._stat[i][start][repeats] \
                or len(self._stat[i][start][repeats][req]) != len(WORKLOADS['roles'][i]):
                return False
        return True
    
    def _can_finish(self, start, repeats):
        for i in [CLIENT, SERVER, RUNNER]:
            if not WORKLOADS[i]['workloads']:
                continue
            elif i not in self._stat \
                or start not in self._stat[i] \
                or repeats not in self._stat[i][start] \
                or EXIT not in self._stat[i][start][repeats] \
                or len(self._stat[i][start][repeats][EXIT]) != len(WORKLOADS['roles'][i]):
                return False
        return True
    
    def _save(self, start):
        workload = self._workloads[start]
        save_results(workload, self._results[workload])
    
    def _get_rsp(self, req, start, repeats):
        if req != END:
            return self._can_continue(req, start, repeats) 
        else:
            return self._can_finish(start, repeats)
    
    def _get_workload(self, start, role=SERVER):
        return list(WORKLOADS[role]['workloads'][start].keys())[0]
    
    def request(self, req, addr, role, start, repeats, workload, results=None):
        if addr not in WORKLOADS['roles'][role]:
            raise Exception('invalid role %s at %s' % (role, addr))
        if workload and workload != self._workloads[start]:
            raise Exception('invalid workload index %s (%s is expected)' % (workload, self._workloads[start]))
        self._lock.acquire()
        try:
            self._check_state(req, addr, role, start, repeats)
            if req == EXIT:
                if results:
                    if SHOW_RESULTS:
                        self._log('%s@%s => %s (%s: %s/%s)' % (role, addr, results, start, repeats + 1, self._repeat_max))
                    self._check_results(workload, results)
            elif req == END:
                if self._can_finish(start, repeats):
                    pos = repeats + 1
                    if pos == self._repeat_max:
                        self._save(start)
                        self._start =  start + 1
                        pos = 0
                    if self._start < self._workload_max:
                        if WORKLOADS['reboot']:
                            t = Thread(target=self._restart, args=(pos))
                            t.start()
        finally:
            self._lock.release()
        return self._get_rsp(req, start, repeats)
    
    def _restart(self, repeats):
        wait = True
        while wait:
            wait = False
            uptime = get_uptime()
            for i in get_members():
                if uptime[i] == self._uptime[i]:
                    wait = True
                    break
        self._uptime = uptime
        reset()
        start_members(self._start, repeats)

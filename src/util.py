import os
import sys
import time
import shlex
import psutil
import zerorpc
import netifaces
import subprocess
from popmark import *
from defaults import *
from time import strptime
from threading import Thread
from datetime import datetime
from workloads import WORKLOADS
from subprocess import getoutput, Popen
from statistics import mean, stdev, median

# Roles ###########
SERVER = 'server'
CLIENT = 'client'
RUNNER = 'runner'
###################

# REQ TYPES #######
BEGIN  = 'begin'
ENTER  = 'enter'
READY  = 'ready'
EXIT   = 'exit'
END    = 'end'
###################

REQ = [BEGIN, ENTER, READY, EXIT, END]
ROLE_ARG = {CLIENT: '-c', SERVER: '-s', RUNNER: '-r'}
HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = HOME if not WORKSPACE else os.path.join(WORKSPACE, os.path.basename(HOME))
SCRIPTS = os.path.join(HOME, 'scripts')
OUTPUTS = os.path.join(HOME, 'outputs')
GETVAL = os.path.join(SCRIPTS, 'getval')
LAUNCHER = os.path.join(os.path.join(TARGET, 'src'), 'run.py')
IF_TYPE = 2

def log(s, time=False, force=False):
    if DEBUG or force:
        if time:
            print(str(s) + '  %s' % str(datetime.utcnow()))
        else:
            print(str(s))

def log_get(obj, s):
    name = obj.__class__.__name__
    return name + ': ' + str(s)

def log_err(obj, s):
    if obj:
        s = log_get(obj, s)
    log(s, time=True, force=True)
    sys.exit(-1)

def log_file(s):
    with open(FILE_LOG, 'a') as f:
        f.write('%s %s\n' % (s, datetime.now()))

def log_file_err(s):
    with open(FILE_LOG, 'a') as f:
        f.write('Error: %s\n' % s)
    sys.exit(-1)

def get_ip_addresses():
    addresses = []
    interfaces = netifaces.interfaces()
    for iface in interfaces:
        res = netifaces.ifaddresses(iface)
        if IF_TYPE in res:
            addresses.append(res[IF_TYPE][0]['addr'])
    return addresses

def get_output(cmd):
    ret = getoutput(cmd)
    if type(ret) != str:
        ret = ret.decode('utf8')
    return ret

def get_members():
    members = []
    for i in [CLIENT, SERVER, RUNNER]:
        if i in WORKLOADS['roles']:
            for j in WORKLOADS['roles'][i]:
                if j not in members:
                    members.append(j)
    return members

def get_addr():
    members = get_members()
    addr_list = get_ip_addresses()
    for i in addr_list:
        if i in members:
            return i

def kill_defunct_processes():
    defunct_processes = []
    for proc in psutil.process_iter():
        try:
            parent = proc.parent()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        if proc.status() == psutil.STATUS_ZOMBIE:
            defunct_processes.append(proc)
            parent.terminate()
    for proc in defunct_processes:
        proc.wait()

def remote_copy(addr, src, dest=None):
    if not dest:
        dest = src
    if dest == '/':
        raise Exception('/ cannot be set as target directory')
    parent = os.path.dirname(dest)
    if not USER or not PASSWORD:
        os.system('ssh -o StrictHostKeyChecking=no %s "rm -rf %s"' % (addr, dest))
        os.system('ssh %s "mkdir -p %s"' % (addr, parent))
        os.system('rsync -r %s %s:%s' % (src, addr, dest))
    else:
        os.system('sshpass -p %s ssh -o StrictHostKeyChecking=no %s@%s "rm -rf %s"' % (PASSWORD, USER, addr, dest))
        os.system('sshpass -p %s ssh %s@%s "mkdir -p %s"' % (PASSWORD, USER, addr, parent))
        os.system('sshpass -p %s rsync -r %s %s@%s:%s' % (PASSWORD, src, USER, addr, parent))

def remote_call(addr, cmd, quiet=True, background=True):
    if quiet:
        if not USER or not PASSWORD:
            cmd_str = 'ssh -o StrictHostKeyChecking=no %s "%s"' % (addr, cmd)
        else:
            cmd_str = 'sshpass -p %s ssh -o StrictHostKeyChecking=no %s@%s "%s"' % (PASSWORD, USER, addr, cmd)
        if SHOW_CMD:
            print(cmd_str)
        return get_output(cmd_str)
    else:
        if not USER or not PASSWORD:
            cmd_str = 'ssh%s -o StrictHostKeyChecking=no %s "%s"' % (' -f' if background else '', addr, cmd)
        else:
            cmd_str = 'sshpass -p %s ssh%s -o StrictHostKeyChecking=no %s@%s "%s"' % (PASSWORD, ' -f' if background else '', USER, addr, cmd)
        if SHOW_CMD:
            print(cmd_str)
        os.system(cmd_str)

def req_addr(ip_addr, port):
    return 'tcp://%s:%d' % (str(ip_addr), int(port))

def check_members():
    for i in get_members():
        ret = remote_call(i, "%s -c 'import os; print(os.path.exists(\"%s\"))'" % (PYTHON, TARGET))
        if not bool(ret):
            raise Exception('failed to find %s at %s' % (TARGET, i))

def get_uptime():
    res = {}
    for i in get_members():
        uptime = None
        while not uptime:
            try:
                uptime = remote_call(i, 'uptime -s')
                if uptime:
                    strptime(uptime, "%Y-%m-%d %H:%M:%S")
            except:
                uptime = None
        res.update({i: uptime})
    return res

def reboot():
    os.system('reboot')

def remote_reboot(addr):
    if not USER or not PASSWORD:
        subprocess.run(['ssh', '-o', 'StrictHostKeyChecking=no', addr, 'reboot'], 
                        shell=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False)
    else:
        subprocess.run(['sshpass', '-p', PASSWORD, 'ssh', '-o', 'StrictHostKeyChecking=no', '%s@%s' % (USER, addr), 'reboot'],
                        shell=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False)

def reboot_members():
    for i in get_members():
        remote_reboot(i)

def start_member(addr, role, start, repeats):
    remote_call(addr, '%s %s %s --start %s --repeats %s' % (PYTHON, LAUNCHER, ROLE_ARG[role], start, repeats))

def start_members(start, repeats):
    for role in [SERVER, CLIENT, RUNNER]:
        if role in WORKLOADS['roles']:
            for addr in WORKLOADS['roles'][role]:
                log_file("start %s (role=%s)" % (addr, role))
                th = Thread(target=start_member, args=(addr, role, start, repeats))
                th.start()

def reset():
    addr_list = []
    for role in [SERVER, CLIENT, RUNNER]:
        if role in WORKLOADS['roles']:
            for addr in WORKLOADS['roles'][role]:
                if addr not in addr_list:
                    addr_list.append(addr)
                    for i in WORKLOADS['collector']:
                        remote_call(addr, 'rm -f %s' % i)

def launch(role, cmd):
    tmp = os.path.join(TMP, ".popmark.%s" % role)
    with open(tmp, 'w') as f:
        f.write('#!/bin/sh\n')
        items = cmd.split(';')
        fst = items[0]
        if fst.startswith('/'):
            dirname = os.path.dirname(fst.split(' ')[0])
            f.write('cd %s\n' % dirname)
            c = fst[len(dirname):]
            if c.startswith('/'):
                c = '.' + c
            else:
                c = './' + c
            items[0] = c
        f.write('%s\n' % ';'.join(items))
    os.system('chmod +x %s' % tmp)
    args = shlex.split(tmp)
    return Popen(args)

def create_client():
    return zerorpc.Client(heartbeat=None)

def parse_results(filename):
    result = {}
    with open(filename, 'r') as file:
        for line in file:
            assignment = line.strip()
            try:
                parsed_dict = eval(assignment)
                if isinstance(parsed_dict, dict):
                    result.update(parsed_dict)
            except (SyntaxError, NameError, TypeError):
                log_file_err("failed to parse %s (the result must be of type dict)" % filename)
    return result

def clear_results():
    for i in WORKLOADS['collector']['outputs']:
        if os.path.exists(i):
            os.remove(i)

def check_results():
    results = {}
    for i in WORKLOADS['collector']['outputs']:
        while True:
            if os.path.exists(i):
                cnt = 0
                for param in WORKLOADS['collector']['outputs'][i]:
                    val = get_output('%s %s %s' % (GETVAL, i, param)).strip()
                    if val != '':
                        results.update({param: val})
                        cnt = cnt + 1
                    else:
                        break
                if cnt == len(WORKLOADS['collector']['outputs'][i]):
                    if 0 == cnt:
                        results.update(parse_results(i))
                    break
            time.sleep(1)
    return results

def gen_statistical_results(results):
    values = list(map(lambda v: float(v), results))
    avg = mean(values)
    dev = stdev(values)
    med = median(values)
    total = sum(values)
    return (avg, dev, med, total)

def gen_output(path, name, results):
    if len(results) > 1:
        avg, dev, med, total = gen_statistical_results(results)
        with open(os.path.join(path, '%s.avg' % name), 'w') as f:
            f.write(str(avg))
        with open(os.path.join(path, '%s.dev' % name), 'w') as f:
            f.write(str(dev))
        with open(os.path.join(path, '%s.med' % name), 'w') as f:
            f.write(str(med))
        with open(os.path.join(path, '%s.sum' % name), 'w') as f:
            f.write(str(total))
    else:
        with open(os.path.join(path, '%s' % name), 'w') as f:
            f.write(str(results[0]))

def gen_outputs(path, results, surfix=''):
    for i in results:
        name = os.path.join(path, i)
        if surfix:
            name = "%s.%s" % (name, surfix)
        with open(name, 'w') as f:
            f.write(str(results[i]))

def save_results(workload, results):
    fields = {}
    fields_avg = {}
    fields_dev = {}
    fields_med = {}
    fields_total = {}
    path = os.path.join(OUTPUTS, workload)
    os.makedirs(path, exist_ok=True)
    for param in results:
        if len(results[param]) == 0:
            raise Exception('no result of %s' % param)
        if type(results[param][0]) == dict:
            res = {}
            for item in results[param]:
                for j in item:
                    if j not in res:
                        res.update({j: []})
                    res[j].append(item[j])
            for i in res:
                if len(res[i]) == 1:
                    if i not in fields:
                        fields.update({i: {}})
                    fields[i].update({param: res[i][0]})
                else:
                    avg, dev, med, total = gen_statistical_results(res[i])
                    if i not in fields_avg:
                        fields_avg.update({i: {}})
                    fields_avg[i].update({param: avg})
                    if i not in fields_dev:
                        fields_dev.update({i: {}})
                    fields_dev[i].update({param: dev})
                    if i not in fields_med:
                        fields_med.update({i: {}})
                    fields_med[i].update({param: med})
                    if i not in fields_total:
                        fields_total.update({i: {}})
                    fields_total[i].update({param: total})
        else:
            gen_output(path, param, results[param])
    if fields:
        gen_outputs(path, fields)
    if fields_avg:
        gen_outputs(path, fields_avg, 'avg')
    if fields_dev:
        gen_outputs(path, fields_dev, 'dev')
    if fields_med:
        gen_outputs(path, fields_med, 'med')
    if fields_total:
        gen_outputs(path, fields_total, 'sum')

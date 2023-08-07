import os
import sys
import zerorpc
import argparse
from subprocess import getoutput
from threading import Thread

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(HOME)
sys.path.append(os.path.join(HOME, 'src'))
sys.path.append(os.path.join(HOME, '.env'))
os.environ["PATH"] += ':' + os.path.join(HOME, 'scripts')
    
try:
    from popmark import *
except:
    sys.path.append(os.path.join(HOME, 'conf'))
    from popmark import *

from workloads import WORKLOADS
from manager import Manager
from worker import Worker
from util import *

def reset_manager():
    pid = getoutput("lsof -i:%s | tail -n 1 | awk -F ' ' '{print $2}'" % MANAGER_PORT)
    if pid:
        os.system('kill -9 %s' % pid)

if __name__ == '__main__':
    if WORKLOADS['reboot'] and MANAGER_ADDR in get_members():
        raise Exception('cannot reboot manager')
    if len(sys.argv) == 1:
        if MANAGER_ADDR not in get_ip_addresses():
            raise Exception('This program must be launched at %s' % MANAGER_ADDR)
        reset_manager()
        mgr = zerorpc.Server(Manager(), heartbeat=None)
        mgr.bind(req_addr(MANAGER_ADDR, MANAGER_PORT))
        mgr.run()
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--client', action='store_true')
        parser.add_argument('-s', '--server', action='store_true')
        parser.add_argument('-r', '--runner', action='store_true')
        parser.add_argument('-m', '--manager', action='store_true')
        parser.add_argument('--start', type=int, default=0)
        parser.add_argument('--repeats', type=int, default=0)
        args = parser.parse_args(sys.argv[1:])
        if args.manager:
            reset_manager()
            mgr = zerorpc.Server(Manager(start=args.start), heartbeat=None)
            mgr.bind(req_addr(MANAGER_ADDR, MANAGER_PORT))
            mgr.run()
        else:
            if args.server:
                w = Worker(role=SERVER, start=args.start, repeats=args.repeats)
            elif args.client:
                w = Worker(role=CLIENT, start=args.start, repeats=args.repeats)
            elif args.runner:
                w = Worker(role=RUNNER, start=args.start, repeats=args.repeats)
            else:
                raise Exception('none of server/client/runner is specified')
            th = Thread(target=w.run)
            th.start()
            th.join()

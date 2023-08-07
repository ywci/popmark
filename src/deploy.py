import os
import sys

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(HOME)
sys.path.append(os.path.join(HOME, 'src'))
sys.path.append(os.path.join(HOME, '.env'))

from util import *
from popmark import *

TARGET = os.path.join(WORKSPACE, os.path.basename(HOME)) if WORKSPACE else HOME

def deploy(addr):
    print('Install to %s' % addr)
    remote_call(addr, "apt-get update")
    remote_call(addr, "apt install -y rsync")
    remote_copy(addr, HOME, TARGET)
    remote_call(addr, os.path.join(TARGET, 'install.sh --no-deploy'))

def install():
    members = get_members()
    for i in members:
        if i != MANAGER_ADDR or TARGET != HOME:
            deploy(i) 

if __name__ == '__main__':
    install()

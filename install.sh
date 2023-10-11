#!/bin/bash

PACKAGES=("zerorpc" "netifaces" "psutil")

PYTHON=python3
INSTALLER=pip3

ENV=.env
CONF=conf/popmark.py
DEPLOY=src/deploy.py
WORKLOADS=conf/workloads.py
DIR=`readlink -f $0 | xargs dirname`

SSHPASS=`which sshpass`
if [ "$SSHPASS" = "" ]; then
    apt-get install -y -qq sshpass
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-deploy)
        DEPLOY=""
        shift 1
        ;;
        *)
        echo "Usage: $0 [OPTION]..."
        echo "Options:"
        echo "  --no-deploy: no deployment"
        exit
        ;;
    esac
done

apt-get install -y -qq python3-pip rsync
rm -rf $DIR/$ENV
mkdir -p $DIR/$ENV
for i in ${PACKAGES[@]}; do
    # $INSTALLER install --break-system-packages --quiet $i
    $INSTALLER install --quiet $i
done
cp $DIR/$CONF $DIR/$ENV
cp $DIR/$WORKLOADS $DIR/$ENV
if [ "$DEPLOY" != "" ]; then 
  $PYTHON $DIR/$DEPLOY
fi
rm -rf $DIR/$ENV

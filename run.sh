#!/bin/bash

PYTHON=python3
SYSTEM=`$PYTHON -c 'import platform; print(platform.system())'`
if [ "$SYSTEM" != "Linux" ]; then
    echo "$SYSTEM does not support"
    exit
fi

DIR=`readlink -f $0 | xargs dirname`
CONF=$DIR/conf/popmark.py
WORKLOADS=$DIR/conf/workloads.py
ENV=$DIR/.env

TEST_CONF=$DIR/scripts/ex_conf.py
TEST_WORKLOADS=$DIR/scripts/ex_workloads.py

TEST=0
START=0
SERVER=0
CLIENT=0
RUNNER=0
MANAGER=1
REPEATS=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --conf)
        CONF=$2
        shift 2
        ;;
        --start)
        START=$2
        shift 2
        ;;
        --repeats)
        REPEATS=$2
        shift 2
        ;;
        --test)
        TEST=1
        shift 1
        ;;
        -s)
        SERVER=1
        MANAGER=0
        shift 1
        ;;
        -c)
        CLIENT=1
        MANAGER=0
        shift 1
        ;;
        -m)
        shift 1
        ;;
        -r)
        RUNNER=1
        MANAGER=0
        shift 1
        ;;
        -h|--help)
        $PYTHON $DIR/src/run.py --help 
        exit
        ;;
        *)
        echo "Error: invalid option $1"
        exit
        ;;
    esac
done

if [ ! -e $CONF ]; then
    echo "Error: $CONF does not exist"
    exit
fi

if [ ! -e $WORKLOADS ]; then
    echo "Error: $WORKLOADS does not exist"
    exit
fi

rm -rf $ENV
mkdir -p $ENV

if [ "$TEST" = "1" ]; then
    NAME_CONF=`basename $CONF`
    NAME_WORKLOADS=`basename $WORKLOADS`
    cp $TEST_CONF $ENV/$NAME_CONF
    cp $TEST_WORKLOADS $ENV/$NAME_WORKLOADS
else
    cp $CONF $ENV/
    cp $WORKLOADS $ENV/
fi

if [ "$MANAGER" = "1" ]; then
    $PYTHON $DIR/src/run.py -m --start $START
elif [ "$SERVER" = "1" ]; then
    $PYTHON $DIR/src/run.py -s --start $START --repeats $REPEATS
elif [ "$CLIENT" = "1" ]; then
    $PYTHON $DIR/src/run.py -c --start $START --repeats $REPEATS 
elif [ "$RUNNER" = "1" ]; then
    $PYTHON $DIR/src/run.py -r --start $START --repeats $REPEATS
else
    $PYTHON $DIR/src/run.py
fi
rm -rf $ENV

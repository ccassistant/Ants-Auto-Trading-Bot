#!/bin/bash

source `pwd`/venv_ants/bin/activate
pip3 install -U -r requirements.txt
nohup python `pwd`/process_monitor.py > ./logs/console.out 2>&1 & echo $! >ant.pid

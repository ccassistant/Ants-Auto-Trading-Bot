#!/bin/bash

#for container
#ssh key generation if not exist
ssh-keygen -q -t rsa -m pem -N '' -f $SSH_DIR/id_rsa 2>/dev/null <<< n >/dev/null

service rabbitmq-server start


source ${ANT_BOT_PATH}/venv_ants/bin/activate
# python ${ANT_BOT_PATH}/process_monitor.py > ./logs/console.out 2>&1 & echo $! >ant.pid
python ${ANT_BOT_PATH}/process_monitor.py

#!/bin/bash

#for container
#ssh key generation if not exist
ssh-keygen -q -t rsa -m pem -N '' -f $SSH_DIR/id_rsa 2>/dev/null <<< n >/dev/null

service rabbitmq-server start


$ANT_BOT_PATH/run.sh

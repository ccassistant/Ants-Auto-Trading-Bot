#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging

from ants.provider.provider import Provider
from messenger.q_receiver import MQReceiver

from env_server import Enviroments


class MQProvider(Provider):
    """
    Q로 전달된 메시지를 받아서 노티해준다
    """

    def __init__(self, q_name=None):
        Provider.__init__(self)
        self.logger = logging.getLogger(__name__)

        if q_name is None:
            self.exchange_name = Enviroments().qsystem.get_quicktrading_q()
        else:
            self.exchange_name = q_name
        self.mq_receiver = MQReceiver(self.exchange_name, self.callback)

        self.is_run = False

    def callback(self, ch, method, properties, body):
        body = json.loads(body.decode("utf-8"))
        try:
            ret = eval(body)
        except Exception as exp:
            self.logger.warning("Can" "t converte {}".format(body))
            ret = {}

        self.logger.debug("Received {}".format(body))
        self.notify(ret)

    def register(self, update, coins):
        self.logger.info("register update")
        self.attach(update)

    def run(self):
        self.logger.info("Try MQ subscribe start")
        self.mq_receiver.start()

    def stop(self):
        self.logger.info("MQ provider will stop...")
        self.is_run = False
        self.mq_receiver.close()
        self.logger.info("MQ provider will stop.")


if __name__ == "__main__":
    print("MQ RCV test")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    stream_hander = logging.StreamHandler()
    stream_hander.setFormatter(formatter)
    logger.addHandler(stream_hander)

    import signal

    def signal_handler(sig, frame):
        print("\nExit Program by user Ctrl + C")
        mq.stop()

    signal.signal(signal.SIGINT, signal_handler)

    mq = MQProvider()
    # mq.load_setting('configs/mail.key')
    mq.run()

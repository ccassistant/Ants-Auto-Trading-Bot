# -*- coding: utf-8 -*-
import logging


CURRENT_MESSAGE_VERSION = "1"
SUPPORT_VERSION = ["1"]


class MessageDict(dict):
    """
    message 포멧에서 필요한 데이터를 뽑아쓸 수 있도록 해줌
    이 클래스 자체가 데이터 클래스 겸 헬프 메소드를 포함하도록 구성함
    input으로 입력되는 모든 메시지는 이 클래스를 통하도록 한다
    ex) 
    new_order = MessageDict('btc', 'krw', 'buy', 'limit', '100%', '100%')
    new_order = MessageDict('btc', 'krw', 'buy', 'limit', 100%', '100%', rule='tsb', tsb1='track')
    
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parser_list = {"1": self.__parser_v1__}

    def build_from_dict(self, msg_dict):
        # msg_dict = {'auto': '0', 'ver': '1', 'exchange': 'UPBIT', 'side': 'BUY', 'type': 'LIMIT', 'coin': 'ETH', 'market': 'KRW', 'price': '210100.0', 'amount': '100%', 'rule': 'TSB', 'tsb-minute': '15', 'tsb-ver': '3.3'}
        self.update(msg_dict)
        return dict(self)

    def build(self, exchange, coin, market, side, _type, amount, price, **args):
        self["VER"] = CURRENT_MESSAGE_VERSION
        self["AUTO"] = 0
        self["EXCHANGE"] = exchange
        self["COIN"] = coin
        self["MARKET"] = market
        self["SIDE"] = side
        self["TYPE"] = _type
        self["AMOUNT"] = amount
        self["PRICE"] = price
        for key, value in args.items():
            self[key.upper()] = value

        return dict(self)

    def parsing(self, rcv_msg):
        rcv_msg = rcv_msg.upper().split("#")
        msg = rcv_msg[1:]
        self.logger.debug(msg)

        ver = None
        for item in msg:
            ver = item.split(":")[0].upper().strip()
            if ver == "VER":
                ver = item.split(":")[1].strip()
                break

        if ver is None:
            msg = "can" "t find message version information"
            self.logger.warning(msg)
            raise Exception(msg)

        if ver not in SUPPORT_VERSION:
            msg = "this message ver is not support:{}".format(ver)
            self.logger.warning(msg)
            raise Exception(msg)

        return self.parser_list[ver](msg)

        msg = f"This version:({ver}) is not support"
        self.logger.debug(msg)
        raise Exception(msg)

    def __parser_v1__(self, rcv_msg):
        """
        {
            'AUTO':True,
            'EXCHANGE':'upbit',
            'COIN':'BTC',
            'MARKET':'KRW',
            'TYPE':'LIMIT',
            'SIDE':'BUY',
            'RULE':'TSB',
            'TSB-MINUTE':'15m'
            'TSB-VER':'3.3'
        }
        """
        result = {}
        for item in rcv_msg:
            try:
                item = item.strip()  # 공백 제거
                item = item.split(":")
                result[item[0].lower()] = item[1].upper()
            except Exception as exp:
                self.logger.warning("message parsing error : {}".format(exp))
                raise exp

        if result.get("type") is None:
            result["type"] = "limit"

        for key in result.keys():
            self[key] = result[key]

        return result


if __name__ == "__main__":
    print("message parser test")

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    stream_hander = logging.StreamHandler()
    stream_hander.setFormatter(formatter)
    logger.addHandler(stream_hander)

    # 메시지 입력 테스트
    msg = MessageDict()
    test_msg = "#AUTO:0 #VER:1 #EXCHANGE:UPBIT #SIDE:BUY #TYPE:LIMIT #COIN:ETH #MARKET:KRW #PRICE:210100.0 #AMOUNT:100% #RULE:TSB #TSB-MINUTE:15 #TSB-VER:3.3"
    ret = msg.parsing(test_msg)
    print("-" * 80)
    print(ret)
    print(msg)

    # 최소한 메시지를 넣고 테스트
    msg = MessageDict()
    test_msg = "#VER:1 #EXCHANGE:UPBIT #SIDE:BUY #TYPE:LIMIT #COIN:ETH #MARKET:KRW #PRICE:210100.0 #AMOUNT:100%"
    ret = msg.parsing(test_msg)

    # dict to message 테스트
    test_dict = {
        "auto": "0",
        "ver": "1",
        "exchange": "UPBIT",
        "side": "BUY",
        "type": "LIMIT",
        "coin": "ETH",
        "market": "KRW",
        "price": 210100.0,
        "amount": "100%",
        "rule": "TSB",
        "tsb-minute": "15",
        "tsb-ver": "3.3",
    }
    ret = msg.build_from_dict(test_dict)
    print("-" * 80)
    print(ret)
    print(msg)

    # 메시지 생성 테스트
    msg = MessageDict()
    # def build(self, exchange, coin, market, side, _type, amount, price, **args):
    ret = msg.build(
        "upbit",
        "btc",
        "krw",
        "buy",
        "limit",
        0.001,
        1000000,
        rule="TSB",
        tsb_minute="15",
        tsb_ver="3.3",
    )
    print("-" * 80)
    print(ret)
    print(msg)

    msg = MessageDict()
    test_msg = "#VER:1 afdsfd"
    ret = msg.parsing(test_msg)

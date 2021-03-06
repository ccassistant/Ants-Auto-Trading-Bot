# -*- coding: utf-8 -*-

"""
거래소
- 공통 기능
- 필수 기능 목록을 넣어둔다.
"""

import abc
import decimal
import binascii
import logging
import ccxt
import base64
import requests
import time
import json
import traceback
from datetime import datetime, timezone

from ccxt.base.decimal_to_precision import decimal_to_precision  # noqa F401
from ccxt.base.decimal_to_precision import TRUNCATE  # noqa F401
from ccxt.base.decimal_to_precision import ROUND  # noqa F401
from ccxt.base.decimal_to_precision import DECIMAL_PLACES  # noqa F401
from ccxt.base.decimal_to_precision import SIGNIFICANT_DIGITS  # noqa F401
from ccxt.base.decimal_to_precision import PAD_WITH_ZERO  # noqa F401
from ccxt.base.decimal_to_precision import NO_PADDING  # noqa F401

from exchangem.model.observers import ObserverNotifier
from exchangem.crypto import Crypto
from exchangem.cache import Cache
from exchangem.utils import Util as util
from exchangem.model.order_record import OrderRecord
from exchangem.model.order_info import OrderInfo
from exchangem.model.coin_model import CoinModel
from exchangem.model.price_storage import PriceStorage

from env_server import Enviroments, ExchangesEnv
from q_publisher import MQPublisher
from q_receiver import MQReceiver


class Base(ObserverNotifier, metaclass=abc.ABCMeta):
    def __init__(self, args={}):
        ObserverNotifier.__init__(self)
        orderes = []
        env = Enviroments()
        self.env = env
        self.cache = Cache()
        self.exchange_name = self.__class__.__name__.lower()
        self.logger.debug("{} exchange init with args : {}".format(self.exchange_name, args))
        self.exchange = None

        self.config = env.exchanges.get(self.exchange_name)
        if self.config == {}:
            self.config = env.exchanges.get("default")

        self.telegram = args.get("telegram")

        self.logger = logging.getLogger("exchange." + self.__class__.__name__.lower())

        exchange_obj = None
        for id in ccxt.exchanges:
            if id == self.exchange_name:
                exchange_obj = getattr(ccxt, id)
                break

        try:
            self.key_set = self.load_key(self.exchange_name)
            self.exchange = exchange_obj(self.key_set)
        except Exception as exp:
            self.exchange = exchange_obj()
            self.logger.warning("Key file loading failed. : {}".format(exp))

        self.markets = self.exchange.loadMarkets()

        # 설정파일에 있어야하는데 없는 설정들을 초기화 한다
        if (
            env.exchanges.get(self.exchange_name) is None
            or env.exchanges.get(self.exchange_name).get("coin") is None
        ):
            env.exchanges[self.exchange_name] = {}
            env.exchanges[self.exchange_name]["coin"] = env.exchanges["default"]["coin"]
            env.save_config()

        self.database = MQPublisher(self.env.qsystem.get_database_q())

    def load_key(self, exchange_name):
        private_key_file = Enviroments().common["key_file"]

        crypto = Crypto()
        crypto.readKey(private_key_file)

        en_key_set = Enviroments().exchanges[exchange_name]["keys"]

        data = en_key_set["apiKey"]
        borg = binascii.a2b_base64(data)
        apiKey = crypto.decrypt(borg)

        data = en_key_set["secret"]
        borg = binascii.a2b_base64(data)
        secret = crypto.decrypt(borg)

        key_set = {"apiKey": apiKey, "secret": secret}
        return key_set

    def load_config(self, file_name):
        return util.readConfig(file_name)

    @abc.abstractmethod
    def get_balance(self, target):
        pass

    @abc.abstractmethod
    def fetch_orders_by_uuids(self, uuids):
        pass

    def create_order(self, symbol, type, side, amount, price, params, etc):
        amount = (float)(amount)
        price = (float)(price)
        prefix_str = ""
        d_amount = self.decimal_to_precision(amount)
        d_price = self.decimal_to_precision(price)
        order_info = None
        desc = None
        coin_name = symbol.split("/")[0].lower()

        if ExchangesEnv().get_trading_list("default").get("all") != True:
            if coin_name not in ExchangesEnv().get_trading_list("default").get("list"):
                self.logger.debug("{} is not in trading list".format(coin_name))
                raise Exception("완료 : {} is not in trading list".format(coin_name))

        if Enviroments().etc["test_mode"] == True:
            self.logger.info(
                "EXCHANGE IN TEST MODE : {} {} {} {} {}".format(
                    symbol, type, side, d_amount, d_price
                )
            )
            desc = {"TEST_MODE": "True"}
            prefix_str = "가상"
            order_info = OrderInfo()
            order_info.set(
                symbol,
                "id",
                side,
                d_price,
                d_amount,
                "",
                "",
                datetime.now(),
                "",
                self.exchange_name,
                etc["from"],
                etc={},
            )
        else:
            try:
                desc = self.exchange.create_order(symbol, type, side, amount, price, params)
                order_info = self.parsing_order_info(desc, etc)
                # 오더 id를 디비큐로 날려준다
                self.database.send(str(order_info))
            except Exception as exp:
                err_str = traceback.format_exc()
                self.logger.debug(f"{err_str}")
                # 주문 오류도 exception으로 처리 된다.
                self.logger.warning("create_oder exception :\n{}".format(exp))
                _str = str(exp)
                _str = _str[_str.index(" ") :]
                try:
                    _dict = json.loads(_str)
                except:
                    _dict = {"exp": _str}
                order = {}
                order["symbol"] = symbol
                order["type"] = type
                order["side"] = side
                order["amount"] = d_amount
                order["price"] = d_price
                order["etc"] = etc

                _dict["request_order"] = order
                raise Exception(_dict)

        try:
            # DB에 기록
            coin_name = symbol.split("/")[0]
            market = symbol.split("/")[1]
            # type = type
            # side = 'buy'
            # amount = 1.1
            # price = 0.45
            params = str(params)
            time = datetime.now()
            request_id = str(desc)
            exchange_name = self.__class__.__name__.lower()

            record = OrderRecord(
                coin_name,
                market,
                type,
                side,
                amount,
                price,
                params,
                time,
                request_id,
                exchange_name,
            )

            total = self.decimal_to_precision(float(amount) * float(price))

            # {'symbol': 'MCO/KRW', 'id': 'd4910a41-385d-4ba9-8317-a8e9ffbc544f', 'side': 'sell', 'price': 8215.0, 'amount': 3.84565168, 'status': 'open', 'remaining': 3.84565168, 'ts_create': 1559005222000, 'ts_updated': None}
            """
            요청하신 내용을 완료하였습니다.
            오더 : UPBIT, BUY, BTC/KRW
            주문수량 : 0.00966634
            주문단가 : 1034000.0
            주문총액 : 9994.99556
            """

            # msg = F'{num1:.2f} is not {n2:,}'
            msg = (
                f"{prefix_str}오더 : {exchange_name.upper()}, {side.upper()}, {coin_name.upper()}/{market.upper()}\n"
                f"주문수량 : {d_amount:,.8f}\n"
                f"주문단가 : {d_price:,.8f}\n"
                f"주문총액 : {total:,.8f}"
            )

            # msg = '{}오더 : {}, {}, {}/{}, 주문 개수:{}, 주문단가:{}, 총 주문금액:{}'.format(
            #                             prefix_str,
            #                             exchange_name.upper(),
            #                             side.upper(),
            #                             coin_name.upper(),
            #                             market.upper(),
            #                             d_amount,
            #                             d_price,
            #                             total)

        except Exception as exp:
            raise exp

        return msg, order_info

    def parsing_order_info(self, msg, etc=None):
        """
        binance 값 예제
        {'info': {'symbol': 'BTTBTC', 'orderId': 1588726, 'clientOrderId': 'and_3f55e388f97e463fa3776d02e726ec12', 'price': '0.00000034', 'origQty': '18633.00000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'NEW', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'SELL', 'stopPrice': '0.00000000', 'icebergQty': '0.00000000', 'time': 1549975901810, 'updateTime': 1549975901810, 'isWorking': True}, 'id': '1588726', 'timestamp': 1549975901810, 'datetime': '2019-02-12T12:51:41.810Z', 'lastTradeTimestamp': None, 'symbol': 'BTT/BTC', 'type': 'limit', 'side': 'sell', 'price': 3.4e-07, 'amount': 18633.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 18633.0, 'status': 'open', 'fee': None, 'trades': None}, 
        
        {
        'info': {'symbol': 'NPXSBTC', 'orderId': 8887249, 'clientOrderId': 'and_a4eceda1a93242f69892ff2668e5bfd1', 'price': '0.00000021', 'origQty': '3567423.00000000', 'executedQty': '0.00000000', 'cummulativeQuoteQty': '0.00000000', 'status': 'NEW', 'timeInForce': 'GTC', 'type': 'LIMIT', 'side': 'SELL', 'stopPrice': '0.00000000', 'icebergQty': '0.00000000', 'time': 1552729837991, 'updateTime': 1552729837991, 'isWorking': True}, 
        'id': '8887249', 'timestamp': 1552729837991, 'datetime': '2019-03-16T09:50:37.991Z', 'lastTradeTimestamp': None, 'symbol': 'NPXS/BTC', 'type': 'limit', 'side': 'sell', 'price': 2.1e-07, 'amount': 3567423.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 3567423.0, 'status': 'open', 'fee': None, 'trades': None    
        }
    
        위의 구조에서 'info'를 키로 사용하는 것은 거래소에서 raw로 응답온 값들이다
        info를 제외한 다른 key들은 모든 거래소 공통 값이다
        """
        self.logger.debug("parsing msg to orderInfo : {}".format(msg))

        try:
            __from__ = etc["from"]
        except:
            self.logger.warning("from info is not exist")
            __from__ = "unknow"

        r = OrderInfo()
        r.set(
            msg.get("symbol"),
            msg.get("id"),
            msg.get("side"),
            msg.get("price"),
            msg.get("amount"),
            msg.get("status"),
            msg.get("remaining"),
            msg.get("timestamp"),
            msg.get("lastTradeTimestamp"),
            self.exchange_name,
            __from__,
        )
        return r

    @abc.abstractmethod
    def check_amount(self, coin_name, seed_size, price):
        """
        코인 이름과 시드 크기를 입력받아서 매매 가능한 값을 돌려준다
        이때 수수료 계산도 함께 해준다
        매매가능한 크기가 거래소에서 지정한 조건에 부합하는지도 함께 계산해서
        돌려준다
        
        가령 주문 단위가 10으로 나눠서 떨어져야 한다면 계산값이 11이 나올경우
        10으로 돌려준다
        주문 가격이 오류인 경우 price오류와 함께 예외를 발생시킨다
        
        return 매매가능한 양, 가격, 수수료
        """
        pass

    @abc.abstractmethod
    def get_last_price(self, symbol):
        pass

    @abc.abstractmethod
    def get_fee(self, market):
        pass

    # def __coin_availabel_size(self, coin_name):
    #     ddddd

    def get_availabel_size(self, coin_name, is_buy=True, want_cached=True):
        cached, data = self.cache.get_cache(coin_name)
        if cached and not want_cached:
            return data

        """
        coin_name의 사용 제한 값을 돌려준다
        법정화폐 및 통화도 코인으로 간주하여 처리한다
        freeze_size : 사용하지 않고 남겨둘 자산의 크기
        availabel_size : 사용할 자산의 크기
        """
        coin_name = coin_name.upper()
        try:
            coin_info = self.env.exchanges["default"]["coin"][coin_name.lower()]
            # coin_info = self.config.get('coin').get(coin_name.lower())
            if coin_info.get("amount") is None:
                raise Exception()
        except Exception as exp:
            coin_info = self.env.exchanges["default"]["coin"]["krw"]

        # if(coin_info == None):
        #     coin_info = self.config.get('coin').get('default')
        #     if(coin_info == None):
        #         Enviroments().exchanges[self.exchange_name]['coin'] = Enviroments().exchanges['default']['coin']
        #         Enviroments().save_config()
        #         coin_info = self.config.get('coin').get('default')

        coin_info = coin_info.get("amount")

        freeze_size = coin_info.get("keep")
        if freeze_size == None:
            freeze_size = 0

        availabel_size = coin_info.get("available")
        if availabel_size == None:
            availabel_size = 0

        self.logger.debug(
            "get_availabel_size name : {}, freeze_size: {}, availabel_size: {}".format(
                coin_name, freeze_size, availabel_size
            )
        )

        balance = self.get_balance(coin_name)
        if balance == None or balance.get(coin_name) == None:
            # 해당 코인의 잔고가 0일 경우
            self.logger.debug("get_availabel_size balance : {}".format(balance))
            self.cache.set_cache(coin_name, 0)
            return 0

        bal_left = balance.get(coin_name)["free"] - freeze_size
        if bal_left < 0:
            self.logger.debug(
                "get_availabel_size 0 caseu balance, freeze_size : {}/{}".format(
                    balance.get(coin_name)["free"], freeze_size
                )
            )
            self.cache.set_cache(coin_name, 0)
            return 0

        if is_buy:
            if availabel_size == None:
                # None이란 의미는 설정값이 없다는 의미
                # 설정값이 없으면 잔고에 남아있는 모든 금액을 사용할 수 있으므로
                # 0으로 설정해 거래를 막아버린다
                # 코인 종류를 다이나믹하게 바꾸는 상황에서 설정값이 없다고 막아버리면...
                # 추후 핫컨피그로 가서 동적으로 바꾸는 기능을 지원할 때 설정값이 없으면 막아버리는 루틴으로 가야할듯..
                # 지금은 설정값이 없으면 전부를 매매 대상으로 봄
                # ret = balance.get(coin_name)['free']
                availabel_size = 0
                self.logger.debug(
                    "get_availabel_size(BUY) availabel_size is not setting : {}".format(
                        availabel_size
                    )
                )
                self.cache.set_cache(coin_name, availabel_size)
                return availabel_size

            if availabel_size < bal_left:
                ret = self.decimal_to_precision(availabel_size)
                self.cache.set_cache(coin_name, ret)
                return ret
            else:
                self.cache.set_cache(coin_name, bal_left)
                return self.decimal_to_precision(bal_left)
        else:  # sell mode일 떄
            if availabel_size == None:
                self.cache.set_cache(coin_name, bal_left)
                return bal_left

            if availabel_size < bal_left:
                self.cache.set_cache(coin_name, availabel_size)
                return availabel_size
            else:
                self.cache.set_cache(coin_name, bal_left)
                return bal_left

    def has_market(self, market):
        try:
            r = self.exchange.markets[market]
        except Exception as exp:
            self.logger.warning(exp)
            r = None

        if r != None:
            return True
        else:
            return False

    def decimal_to_precision(self, value):
        return float(decimal_to_precision(value, TRUNCATE, 8, DECIMAL_PLACES))

    def except_parsing(self, exp):
        # ccxt에서 예외 args를 공��(' ')으로 구분해서 넣어줌.
        exp_str = exp.args[0]
        error = exp.args[0][exp_str.index(" ") :]
        dd = eval(error)
        return dd.get("error").get("message")

    def get_BTC_price(self):
        # BTC / USDT의가격을 돌려준다.
        pass

    def get_key_market_price(self, key_coin):
        """
        기축 통화 가격을 USDT 기준으로 돌려준다.
        """
        symbol = key_coin + "/USDT"
        r = self.key_market_price.get(symbol)
        if r == None:
            symbol = key_coin + "/KRW"
            r = self.key_market_price.get(symbol)
            if r == None:
                raise Exception("{} is not key coin".format(symbol))

            krw_rate = self.get_usd_krw()
            r = r / krw_rate

        return r

    def is_small_balance(self, count, market):
        BASE_PRICE_USDT = 0.5

        if market == "KRW":
            if count < BASE_PRICE_USDT * 1300:
                return True
            else:
                return False

        if market == "USDT":
            if count < BASE_PRICE_USDT:
                return True
            else:
                return False

        # KRW을 제외한 ETH, BTC일 경우
        ps = PriceStorage()
        pre_price = ps.get_price(self.exchange_name.upper(), "USDT", market)["price"]

        price = count * pre_price
        if price < BASE_PRICE_USDT:
            return True
        else:
            return False

    def get_usd_krw(self):
        # 업비트 환율 정보를 얻어온다
        url = "https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWUSD"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        }

        info = requests.get(url, headers=headers).json()
        return info[0]["basePrice"]

    def get_order_book(self, symbol):
        st = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        result = self.exchange.fetch_order_book(symbol)
        tgap = st - result.get("timestamp")  # milliseconds
        self.logger.debug("st:{}, rl:{}, tgap : {}".format(st, result.get("timestamp"), tgap))
        return result

    def get_order_books(self, symbols, params={}):
        try:
            st = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
            result = self.exchange.fetch_order_books(symbols, params)
            # result[symbol]['timestamp'] 형식으로 돌아온다. 코인마다 각각 시간이 다르다
            return result
        except Exception as e:
            self.logger.warning("exchange is not support getOrderBooks : {}".format(e))
            return None

    def get_private_order(self, symbol=None):
        return self.exchange.fetch_open_orders(symbol)

    @abc.abstractmethod
    def get_private_orders_detail(self, id):
        pass

    def cancel_private_order(self, id, symbol=None, params={}):
        return self.exchange.cancel_order(id, symbol, params)


class SupportWebSocket(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def open(self):
        pass

    @abc.abstractmethod
    def close(self):
        pass

    @abc.abstractmethod
    def connect(self):
        pass

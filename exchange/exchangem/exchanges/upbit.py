# -*- coding: utf-8 -*-
import logging
import time
import json
from datetime import datetime
import websocket
import threading
import ccxt

from exchangem.model.exchange import Base
from exchangem.model.balance import Balance
from exchangem.model.order_info import OrderInfo

class Upbit(Base):
    def __init__(self, args={}):
        Base.__init__(self, args)
   
    def connect(self):
        self.noti_msg( '### 연결 중..')
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp("wss://api.upbit.com/websocket/v1",
                                  on_message = lambda ws, msg: self.on_message(ws, msg),
                                  on_error = lambda ws, msg: self.on_error(ws, msg),
                                  on_close = lambda ws: self.on_close(ws),
                                  on_open = lambda ws: self.on_open(ws))
        self.thread_hnd = threading.Thread(target=self.ws.run_forever)
        self.thread_hnd.start()
        
        
    def on_message(self, ws, message):
        # self.logger.debug( 'got message in upbit : {}'.format(message) )
        self.notify(message)
        pass

    def on_error(self, ws, error):
        self.logger.error( error )

    def on_close(self, ws):
        self.logger.info( "### closed ###" )

    def on_open(self, ws):
        data=[{"ticket":"upbit_arbit_bot"}, #고유한 키값을 넣어서 응답이 왔을 때 구분자로 사용한다.
            {"type":"orderbook","codes":self.coins},
            {"format":"SIMPLE"}]
        ws.send(json.dumps(data))
        
    def close(self):
        self.ws.close()
        # self.thread_hnd.exit()
    
    def noti_msg(self, msg):
        self.logger.info(msg)
        # aTeleBot.sendMessageToAll(msg)
    
    def target_coins(self, coins):
        self.coins = coins
    
    def async_get_order_book(self):
        self.connect()
    
    def register_callback(self, cb):
        pass
    
    def get_balance(self, target):
        #업비트는 전체 계좌 조회만 제공한다
        balance = Balance()
        ret = self.exchange.fetch_balance()
        if(not ret.get(target)):
            #보유한 것이 없어서 None일 수도 있고 미지원 코인일 때도 None가 뜬다
            return None
            
        #업빗에서는 total = used + free
        #free는 매도 오더를 냈을 때 '-100' 마이너스 값으로 나온다
        # free = -194
        # total = 0
        # used = 194
        # 위의 경우 버그로 예상된다.
        # free = 24954
        # total = 39882
        # used = 14928
        # 이 경우는 올바르게 나온다.
        # 즉 전량매도 했을 때 free가 마이너스로 나오고 이 때문에 total이 잘못된 값을 가진다
        # 이 버그는 ccxt에서 발생하는 것으로 보인다. 빗썸 REST API를 호출하면 올바른 값을 돌려준다. 2019-03-14
        

        #그러므로 여기서 해당 버그를 감안해 보정해준다. 2019-03-14        
        free = ret[target]['free']
        used = ret[target]['used']
        if(free < 0):
            free = 0
        total = free + used
        
        balance.add(target, total, used, free)

        return balance
    
    def get_all_balance(self):
        #업비트는 전체 계좌 조회만 제공한다
        balance = Balance()
        ret = self.exchange.fetch_balance()
        info = ret['info']
        for item in info:
            name = item['currency']
            balance.add(name, 
                        ret[name]['total'],
                        ret[name]['used'],
                        ret[name]['free'])

        return balance
    
    def check_amount(self, symbol, seed, price):
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
        #TODO KRW일 때는 확인했는데.. USDT, BTC, ETH일 때 확인을 안했음..
        
        market = symbol.split('/')[1]
        if(market == 'KRW'):
            #가격에 따라 주문할 수 있는 범위가 달라진다
            #이에 맞춰 주문할 수 있는 범위를 조정해준다
            # https://docs.upbit.com/docs/market-info-trade-price-detail
            if(price > 2000000):
                div = 1000
            elif(price > 1000000):
                div = 500
            elif(price > 500000):
                div = 100
            elif(price > 100000):
                div = 50
            elif(price > 10000):
                div = 10
            elif(price > 1000):
                div = 5
            elif(price > 100):
                div = 1
            elif(price > 10):
                div = 0.1
            elif(price > 0):
                div = 0.01
            
            price -= price % div
        
        
        if(seed > 0):
            fee = self.get_fee(symbol.split('/')[1])
            fee_p = (seed / price) * fee
            amount = (seed / price) - fee_p
        else:
            fee_p = 0
            amount = 0
    
            
            

        amount = float("{:.8f}".format(amount))
        seed = float("{:.8f}".format(seed))
        fee_p = float("{:.8f}".format(fee_p))
            
        return amount, price, fee_p
        pass

    def get_last_price(self, symbol):
        ticker = self.exchange.fetch_ticker(symbol)
        self.logger.debug(ticker)
        """
        {'symbol': 'BTC/KRW', 'timestamp': 1549698009141, 'datetime': '2019-02-09T07:40:09.141Z', 'high': 4100000.0, 'low': 3776000.0, 'bid': 4002000.0, 'bidVolume': None, 'ask': 4004000.0, 'askVolume': None, 'vwap': 3927711.3257, 'open': 3778000.0, 'close': 4004000.0, 'last': 4004000.0, 'previousClose': None, 'change': 226000.0, 'percentage': 5.9820010587612495, 'average': 3891000.0, 'baseVolume': 5113.40675249, 'quoteVolume': 20083985614.66583, 'info': {'opening_price': '3778000', 'closing_price': '4004000', 'min_price': '3776000', 'max_price': '4100000', 'average_price': '3927711.3257', 'units_traded': '5113.40675249', 'volume_1day': '5113.40675249', 'volume_7day': '17281.38692642', 'buy_price': '4002000', 'sell_price': '4004000', '24H_fluctate': '226000', '24H_fluctate_rate': '5.98', 'date': '1549698009141'}}
        """
        return ticker['last']
        pass
    
    def get_fee(self, market):
        fee = 0.0015
        #업비트의 원화 수수료는 0.05% 이다
        if(market.upper() == 'KRW'):
            fee = 0.0005
            
        return fee

    def get_private_orders(self, symbol=None):
        list = []
        ret = self.exchange.fetch_open_orders(symbol)
        if(ret == None):
            return list
        
        for i in ret:
            r = self.parsing_order_info(i)
            list.append(r)
            
        return list
        
    def get_private_orders_detail(self, id):
        msg = self.exchange.fetch_order(id)
        return self.parsing_order_info(msg)
    
    
if __name__ == '__main__':
    print('test')
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_hander = logging.StreamHandler()
    stream_hander.setFormatter(formatter)
    logger.addHandler(stream_hander)
    
    logging.getLogger("__main__").setLevel(logging.DEBUG)
    logging.getLogger("ccxt").setLevel(logging.DEBUG)
    logging.getLogger("exchangem.model.exchange").setLevel(logging.DEBUG)
    # logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    
    
    up = Upbit({'root_config_file':'configs/ants.conf', 'key_file':'configs/exchanges.key', 'config_file':'configs/upbit.conf'})
    
    coins = ['KRW-ETH', 'KRW-DASH', 'ETH-DASH', 'KRW-LTC', 'ETH-LTC', 'KRW-STRAT', 'ETH-STRAT', 'KRW-XRP', 'ETH-XRP', 'KRW-ETC', 'ETH-ETC', 'KRW-OMG', 'ETH-OMG', 'KRW-SNT', 'ETH-SNT', 'KRW-WAVES', 'ETH-WAVES', 'KRW-XEM', 'ETH-XEM', 'KRW-ZEC', 'ETH-ZEC', 'KRW-XMR', 'ETH-XMR', 'KRW-QTUM', 'ETH-QTUM', 'KRW-GNT', 'ETH-GNT', 'KRW-XLM', 'ETH-XLM', 'KRW-REP', 'ETH-REP', 'KRW-ADA', 'ETH-ADA', 'KRW-POWR', 'ETH-POWR', 'KRW-STORM', 'ETH-STORM', 'KRW-TRX', 'ETH-TRX', 'KRW-MCO', 'ETH-MCO', 'KRW-SC', 'ETH-SC', 'KRW-POLY', 'ETH-POLY', 'KRW-ZRX', 'ETH-ZRX', 'KRW-SRN', 'ETH-SRN', 'KRW-BCH', 'ETH-BCH', 'KRW-ADX', 'ETH-ADX', 'KRW-BAT', 'ETH-BAT', 'KRW-DMT', 'ETH-DMT', 'KRW-CVC', 'ETH-CVC', 'KRW-WAX', 'ETH-WAX']

    from exchangem.model.observers import Observer
    class Update(Observer):
        def update(self, args):
            print('got msg in udt')
            up.close()
            pass
    
    udt = Update()
    
    print(Update.mro())
    up.target_coins(coins)
    up.attach(udt)
    up.async_get_order_book()
    
    bal = up.get_balance('없는코인')
    if(bal is not None):
        print(bal.get_all())
    
    bal = up.get_balance('KRW')
    if(bal is not None):
        print(bal.get_all())
        print(bal.get('KRW'))
        
    print('balance---------------------------------------------------------------')
    print(up.get_all_balance().get('KRW'))
    print(up.get_all_balance().get_all())
    print('balance---------------------------------------------------------------')
    
    print('last price : ', up.get_last_price('BTC/KRW'))
    print('fee : ', up.get_fee('KRW'))
    amount, price, fee = up.check_amount('BTC/KRW', 10000, 3900901)
    print('order : ', amount, price, fee)
    print('order : ', up.check_amount('BTC/KRW', 10000, 0.9157))
    print('order : ', up.check_amount('BTC/KRW', 10000, 12.9157))
    print('order : ', up.check_amount('BTC/KRW', 10000, 163.9157))
    print('order : ', up.check_amount('BTC/KRW', 10000, 8823.9157))
    print('order : ', up.check_amount('BTC/KRW', 0.005, 4000000))
    
    print('KRW seed limit : ', up.get_availabel_size('KRW'))
    print('BTC seed limit : ', up.get_availabel_size('BTC'))
    print('ETH seed limit : ', up.get_availabel_size('ETH'))
    print('EOS seed limit : ', up.get_availabel_size('EOS'))
    print('seed limit : ', up.get_availabel_size('EOS111'))
    
    print('has_market :', up.has_market('BTC/KRW'))
    print('has_market :', up.has_market('BTC/NONE'))
    
    print(up.get_key_market_price('BTC'))
    
    print('1200 won is small balance ? ', up.is_small_balance(1200, 'KRW'))
    print('1310 won is small balance ? ', up.is_small_balance(1310, 'KRW'))
    print('$0.9 is small balance ? ', up.is_small_balance(0.9, 'USDT'))
    print('$1 is small balance ? ', up.is_small_balance(1, 'USDT'))
    print('0.00000001 satosi is small balance ? ', up.is_small_balance(0.00000001, 'BTC'))
    print('0.001 satosi is small balance ? ', up.is_small_balance(0.001, 'BTC'))
    
    # up.connect()
    
    #공개 오더북 읽어오는 테스트
    # print('get order books', up.get_order_books(None))
    # print('get order book', up.get_order_book('GNT/KRW'))
    # print(up.exchange.ids)
    # print('get order books', up.get_order_books(['GNT/KRW', 'BTC/KRW', 'BTC/USDT']))
    
    #개인 오더북 읽어오는 테스트
    print('get private orders', up.get_private_orders())
    # print('get my orders : ', up.get_private_orders('BCH/KRW'))
    # print('get my orders', up.get_private_orders(['BCH/KRW','ZEC/KRW'])) #이렇게 동작하도록 만들어야지..
    
    #거래 취소 테스트, 실제 거래를 넣고 취소하는 테스트이므로 주의를 요구함
    order = up.create_order('BTC/KRW', 'limit', 'buy', '1', '10000', '')
    uuid = order.get()['id']
    print('*' * 160)
    print(order.get())
    print(uuid)
    o_detail = up.get_private_orders_detail(uuid)
    print(o_detail.get())
    up.cancel_private_order(uuid)
    o_detail = up.get_private_orders_detail(uuid)
    print(o_detail.get())
    #거래 취소 테스트 - 끝
    
    # #트레이딩 뷰 와치 목록 뽑는 코드
    # # 'BITTREX:ADABTC,BINANCE:ADAUSDT,'
    # pp = ''
    # markets = up.exchange.loadMarkets()
    # # print(markets)
    # for item in markets:
    #     market = item.split('/')[1]
    #     name = item.split('/')[0]
    #     item = item.replace('/','')
    #     if(market == 'BTC'):
    #         pp = pp + 'BITTREX:' + item + ','
    
    # print(pp)
    
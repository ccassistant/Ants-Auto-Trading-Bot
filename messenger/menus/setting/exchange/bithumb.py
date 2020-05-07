from menus.menu_back import BackMenu
from menus.menu_item import MenuItem
from menus.setting.exchange.apis import ExchangeAPIs


class Bithumb(MenuItem):
    def __init__(self):
        super().__init__()
        # self.__add__(CoinAPIs())
        self.__add__(ExchangeAPIs("bithumb"))
        self.__add__(BackMenu())
        pass

    def __repr__(self):
        return "빗썸 설정"

    def to_dict(self):
        return "빗썸 설정"


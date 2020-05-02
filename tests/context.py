import os
import sys

print("modules")
print(sys.modules)

sys.path.append(os.path.abspath("/workspaces/Ants-Auto-Trading-Bot"))
sys.path.append(os.path.abspath("/workspaces/Ants-Auto-Trading-Bot/antsbot"))
# sys.path.append(os.path.abspath('/workspace/Ants-Auto-Trading-Bot/exchange/exchangem'))
print("-" * 80)
print("sys.path {}".format(sys.path))

from enviroments.sentry_env import SentryEnv

from exchange.exchangem.model.amount_model import AmountModel

from messenger.q_publisher import MQPublisher
from exchange.exchangem.model.coin_model import CoinModel

print("path test")
# sys.path.insert(0, os.path.abspath('../ants'))

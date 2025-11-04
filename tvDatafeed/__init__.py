import requests
import pandas as pd
import json
import time
from datetime import datetime

class Interval:
    IN_1_MINUTE = "1"
    IN_3_MINUTE = "3"
    IN_5_MINUTE = "5"
    IN_15_MINUTE = "15"
    IN_30_MINUTE = "30"
    IN_45_MINUTE = "45"
    IN_1_HOUR = "1H"
    IN_2_HOUR = "2H"
    IN_3_HOUR = "3H"
    IN_4_HOUR = "4H"
    IN_DAILY = "1D"
    IN_WEEKLY = "1W"
    IN_MONTHLY = "1M"

class TvDatafeed:
    def __init__(self, username: str = None, password: str = None):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0"
        }

    def get_hist(self, symbol: str, exchange: str, interval: str = Interval.IN_DAILY, n_bars: int = 500):
        """Simüle edilmiş veri getirici (örnek amaçlı)."""
        import yfinance as yf
        data = yf.download(symbol, period="1y", interval="1wk")
        data.reset_index(inplace=True)
        data.rename(columns={
            "Date": "datetime",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        }, inplace=True)
        return data.tail(n_bars)

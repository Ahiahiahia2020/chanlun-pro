from oandapyV20 import API
from oandapyV20.exceptions import V20Error
from oandapyV20.endpoints.instruments import InstrumentsCandles

def get_oanda_xauusd_1m(count=5000):
    client = API(access_token="YOUR_API_KEY", environment="practice")
    params = {
        "granularity": "M1",
        "count": count,
        "price": "BA"  # Bid/Ask
    }
    
    try:
        r = InstrumentsCandles(instrument="XAU_USD", params=params).request(client)
        candles = []
        for c in r['candles']:
            candles.append({
                'time': c['time'],
                'open': float(c['bid']['o']),
                'high': float(c['bid']['h']),
                'low': float(c['bid']['l']),
                'close': float(c['bid']['c']),
                'volume': c['volume']
            })
        return pd.DataFrame(candles).set_index('time')
    except V20Error as e:
        print("API Error:", e)
        return None

# 获取最近5000根1分钟K线
df = get_oanda_xauusd_1m()
print(df.head())

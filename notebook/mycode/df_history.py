
import pandas as pd
from chanlun.cl_utils import query_cl_chart_config
from chanlun.exchange.exchange_db import ExchangeDB
from chanlun.cl_utils import *
def get_history(
    market: str = 'a',
    code: str = 'SHSE.000300',
    frequency: str = '1m',
    count: int = 0,
    ealry: bool = False, 
    start_date: str = "2025-05-16 09:30:00",
    end_date: str = "2025-05-16 15:01:00"
) -> pd.DataFrame:
    """
    获取历史K线数据并进行预处理
    
    参数:
        market (str): 市场标识符，默认为 'a' 表示沪深A股。
        code (str): 标的资产代码，默认为 'SHSE.000300'。
        frequency (str): 周期列表，默认为 '1m'。
        start_date (str): 开始日期和时间，默认为 "2025-05-16 09:30:00"。
        end_date (str): 结束日期和时间，默认为 "2025-05-16 15:01:00"。
        
    返回:
        pd.DataFrame: 包含 'open', 'high', 'low', 'close', 'volume' 的 DataFrame，索引为 datetime。
    """
    
    # 查询缠论配置
    cl_config = query_cl_chart_config(market, code)
    # print(cl_config)

    # 使用 ExchangeDB 读取数据库中的 K 线数据
    ex = ExchangeDB(market)
    # print("end_date",end_date)
    # 获取 K 线数据
    klines = ex.klines(code, frequency=frequency, start_date=start_date, end_date=end_date)
    # print(klines.iloc[-1])
    # 提取所需列并确保 'date' 列是 datetime 类型
    if count and not ealry:
        df = klines[['date', 'open', 'high', 'low', 'close', 'volume']][-count:]
    elif count and ealry:
        df = klines[['date', 'open', 'high', 'low', 'close', 'volume']][:count]
    else:
        df = klines[['date', 'open', 'high', 'low', 'close', 'volume']]
    df['date'] = pd.to_datetime(df['date'])

    # 设置 'date' 列为索引
    df.set_index('date', inplace=True)

    # 添加 timestamp 列（可选）
    df['timestamp'] = df.index

    return df

if __name__ == '__main__':
    df = get_history(market='a', code='SHSE.000300',count=300, frequency='1m', start_date="2025-05-16 09:30:00", end_date="2025-09-05 10:01:00")
    print(df.tail(100))
    date1 = df['date']
    print(date1)
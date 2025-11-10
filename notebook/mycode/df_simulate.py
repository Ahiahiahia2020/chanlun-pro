import numpy as np
import pandas as pd

def generate_simulated_data(
    n=1440,
    start='2023-01-01',  # 新增的起始时间参数（默认为 '2023-01-01'）
    start_price=100.0,
    price_mean=0.0,
    price_std=0.5,
    high_low_range=0.5,
    volume_min=100,
    volume_max=500,
    seed=42
):
    """
    生成模拟的金融时间序列数据
    
    参数:
    - n (int): 数据点数量（默认 1440，即1天的分钟数据）
    - start (str or datetime-like): 时间序列的起始时间（默认 '2023-01-01'）
    - start_price (float): 初始价格（默认 100.0）
    - price_mean (float): 价格变化的均值（默认 0.0）
    - price_std (float): 价格变化的标准差（默认 0.5）
    - high_low_range (float): 高低价波动范围（默认 0.5）
    - volume_min (int): 成交量最小值（默认 100）
    - volume_max (int): 成交量最大值（默认 500）
    - seed (int): 随机种子（默认 42）
    
    返回:
    - df (DataFrame): 包含 open, high, low, close, volume 的 DataFrame，索引为时间戳
    """
    # 设置随机种子
    np.random.seed(seed)
    
    # 生成时间索引
    times = pd.date_range(start=start, periods=n, freq='min')
    
    # 生成收盘价
    close_prices = np.cumsum(np.random.normal(price_mean, price_std, n)) + start_price
    
    # 生成开盘价
    open_prices = np.empty(n)
    open_prices[0] = start_price
    open_prices[1:] = close_prices[:-1]
    
    # 生成高低价
    high_prices = np.zeros(n)
    low_prices = np.zeros(n)
    for i in range(n):
        body_max = max(open_prices[i], close_prices[i])
        body_min = min(open_prices[i], close_prices[i])
        high_prices[i] = body_max + np.random.uniform(0, high_low_range)
        low_prices[i] = body_min - np.random.uniform(0, high_low_range)
    
    # 生成成交量
    volumes = np.random.randint(volume_min, volume_max + 1, n)
    
    # 构建 DataFrame
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }, index=times)
    
    return df
if __name__ == '__main__':
    df = generate_simulated_data()
    print(df)
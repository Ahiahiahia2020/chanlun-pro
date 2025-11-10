from  vp_analyze import *
from df_history import get_history

def check_low_volume_region(new_price, low_volume_regions):
    """
    判断新价格是否落在某个低成交量区域
    
    参数:
    - new_price (float): 新的收盘价格
    - low_volume_regions (list): 低成交量区域列表，每个元素为 (lower, upper, total_ratio)
    
    返回:
    - in_region (bool): 是否落在低成交量区域
    - region_info (tuple): 如果在区域中，返回 (lower, upper, total_ratio)，否则返回 None
    """
    for idx, (lower, upper, total_ratio) in enumerate(low_volume_regions):
        if lower <= new_price <= upper:
            # 发出信号（可自定义）
            print(f"⚠️ 信号触发：新价格 {new_price:.2f} 落在低成交量区域 {idx+1}")
            print(f"区域范围: 下边界 {lower:.2f} ~ 上边界 {upper:.2f}")
            print(f"该区域总成交量占比: {total_ratio * 100:.2f}%\n")
            return True, (lower, upper, total_ratio)
    print(f"✅ 新价格 {new_price:.2f} 未落在任何低成交量区域\n")
    return False, None


if __name__ == '__main__':

    # 调用函数
    high_poc_list, thin_regions_list = analyze_volume(df, bin_size=1, if_plt=True)

    # 打印结果
    print("高成交量区域的POC:")
    for idx, poc_info in enumerate(high_poc_list):
        print(f"区域 {idx+1}: 价格 {poc_info['price']:.2f}, 成交量占比 {poc_info['volume_ratio'] * 100:.2f}%")

    print("\n低成交量区域:")
    for idx, (lower, upper, total_ratio) in enumerate(thin_regions_list):
        print(f"区域 {idx+1}: [{lower:.2f},  {upper:.2f}], 总占比 {total_ratio * 100:.2f}%")


    # 假设已经运行了分析函数，得到了 low_volume_regions
    # 示例：模拟一个新价格
    new_price = 127.5

    # 调用判断函数
    in_region, region_info = check_low_volume_region(new_price, thin_regions_list)

    if in_region:
        lower, upper, total_ratio = region_info
        # 这里可以执行交易策略，如开仓、平仓等
        print(f"执行交易策略...，止损{lower},止损点差{new_price - lower},止盈{upper},止盈点差{upper - new_price},盈亏比{(upper - new_price)/(new_price - lower)}")
import numpy as np
import pandas as pd
from tabulate import tabulate
from collections import defaultdict
from df_history import get_history
from vp_analyze import analyze_volume, display_signals
import matplotlib.pyplot as plt

base_count = 30
freq_map = {
    "1m": base_count,
    "5m": base_count * 4,
    "15m": base_count * 12,
    "30m": base_count * 22,
    "60m": base_count * 35,
    "1d": base_count * 160,
    "1w": base_count * 160 * 5,
    "1M": base_count * 160 * 22
}
def analyze_and_generate_signals(freqs=["60m","30m","15m","5m"], end_date="2025-6-13 15:00:00" ,if_plt = False):
    """
    分析多周期POC和成交量分布边缘共振信号，并生成可视化图表和信号列表。
    
    参数:
        freqs (list): 需要分析的周期列表
        end_date (str): 分析的结束时间
        if_plt (bool): 是否需要画图
        
    返回:
        dict: 包含表格数据和信号信息的字典
            - table (str): 转置后的表格字符串
            - important_signals (list): 重要POC信号 [(start, end, freqs)]
            - general_signals (list): 一般POC信号 [(start, end, freqs)]
            - important_thin_signals (list): 重要成交量边缘信号 [(start, end, freqs)]
            - general_thin_signals (list): 一般成交量边缘信号 [(start, end, freqs)]
    """

    def merge_adjacent_prices(prices, threshold=2.0):
        if not prices:
            return []
        sorted_prices = sorted(set(prices))
        intervals = []
        start = sorted_prices[0]
        for i in range(1, len(sorted_prices)):
            if sorted_prices[i] - sorted_prices[i - 1] > threshold:
                intervals.append((start, sorted_prices[i - 1]))
                start = sorted_prices[i]
        intervals.append((start, sorted_prices[-1]))
        return intervals

    def merge_intervals(intervals):
        if not intervals:
            return []
        sorted_intervals = sorted(intervals)
        merged = [list(sorted_intervals[0])]
        for current in sorted_intervals[1:]:
            last = merged[-1]
            if current[0] <= last[1]:
                last[1] = max(last[1], current[1])
            else:
                merged.append(list(current))
        return [tuple(interval) for interval in merged]
    poc_list_freq ={}
    thin_list_freq = {}
    real_poc_freq = {}
    for freq in freqs:
        count = freq_map[freq]
        df = get_history(count=count, start_date="2024-2-3 09:30:00",end_date=end_date)
        # print(freq,len(df))
        # print(df.head(1))
        # print(df.tail(1))
        # last_price = df['close'].iloc[-1]
        # print(last_price)
        high_poc_list, thin_regions_list, real_poc = analyze_volume(df, freq=freq, bin_size=1, sense=10, if_plt=if_plt)
        poc_list_freq[freq]=high_poc_list
        thin_list_freq[freq] = thin_regions_list
        real_poc_freq[freq] = real_poc
    last_price = df['close'].iloc[-1]
    # 生成表格
    table_data = []
    for freq in freqs:
        real_poc_info = f"Real POC: {real_poc_freq[freq][0]}"
        poc_info = "\n".join([f"{poc_price},ratio:{vol_ratio:.2%}" for poc_price, _, vol_ratio in poc_list_freq[freq]])
        thin_info = "\n".join([f"{low}-{high + 1},{total_ratio:.2%}" for low, high, total_ratio in thin_list_freq[freq]])
        table_data.append([freq, real_poc_info, poc_info, thin_info])

    df = pd.DataFrame(table_data, columns=["周期", "真实POC", "POC分布", "成交量分布边缘"])
    transposed_df = df.transpose()
    table_str = tabulate(transposed_df, headers="keys", tablefmt="grid")

    # POC信号分析
    price_coverage = defaultdict(list)
    for freq in freqs:
        for poc_price, _, _ in poc_list_freq[freq]:
            for p in np.arange(poc_price - 2, poc_price + 2, 1):
                price_coverage[round(float(p), 1)].append(freq)

    overlap_groups = defaultdict(set)
    for price, freqs_covered in price_coverage.items():
        if len(freqs_covered) >= 2:
            freqs_tuple = tuple(sorted(set(freqs_covered)))
            overlap_groups[freqs_tuple].add(round(price, 1))

    all_signals = []
    for key, prices in overlap_groups.items():
        overlapping_pocs = []
        for freq in key:
            for poc_price, _, _ in poc_list_freq[freq]:
                if any(abs(poc_price - p) <= 1 for p in prices):
                    overlapping_pocs.append((freq, poc_price))

        price_to_freqs = defaultdict(set)
        for freq, poc in overlapping_pocs:
            price_to_freqs[poc].add(freq)

        all_poc_prices = list(price_to_freqs.keys())
        merged_intervals = merge_adjacent_prices(all_poc_prices)

        matched_ranges = []
        for start, end in merged_intervals:
            common_freqs = set()
            for p in np.arange(start - 1, end + 2, 1):
                p = round(float(p), 1)
                if p in price_to_freqs:
                    common_freqs.update(price_to_freqs[p])
            common_freqs = tuple(sorted(common_freqs))
            matched_ranges.append((start, end, common_freqs))

        all_signals.extend(matched_ranges)

    covered_signals = []
    all_signals.sort(key=lambda x: (-len(x[2]), x[0]))
    important_signals = []
    general_signals = []

    for current in all_signals:
        c_start, c_end, c_freqs = current
        is_covered = False
        for covered in covered_signals:
            i_start, i_end, i_freqs = covered
            if set(c_freqs).issubset(i_freqs) and i_start <= c_start <= c_end <= i_end:
                is_covered = True
                break
        if not is_covered:
            covered_signals.append(current)
            if len(c_freqs) >= 3:
                important_signals.append(current)
            else:
                general_signals.append(current)

    # 成交量边缘信号分析
    thin_price_coverage = defaultdict(list)
    for freq in freqs:
        for low, high, _ in thin_list_freq[freq]:
            if high == 999999:
                high = low + 1
            elif low == 0:
                low = high - 1
            for p in np.arange(low, high + 2, 1):
                thin_price_coverage[round(float(p), 1)].append(freq)

    thin_overlap_groups = defaultdict(set)
    for price, freqs_covered in thin_price_coverage.items():
        if len(freqs_covered) >= 2:
            key = tuple(sorted(set(freqs_covered)))
            thin_overlap_groups[key].add(round(price, 1))

    all_thin_signals = []
    for key, prices in thin_overlap_groups.items():
        overlapping_intervals = set()
        for freq in key:
            for low, high, _ in thin_list_freq[freq]:
                if high == 999999:
                    high = low + 1
                elif low == 0:
                    low = high - 1
                if any(low <= p <= high for p in prices):
                    overlapping_intervals.add((low, high))
        merged = merge_intervals(overlapping_intervals)
        for interval in merged:
            all_thin_signals.append((interval[0], interval[1], key))

    covered_thin_signals = []
    important_thin_signals = []
    general_thin_signals = []

    all_thin_signals.sort(key=lambda x: (-len(x[2]), x[0]))
    for current in all_thin_signals:
        c_start, c_end, c_freqs = current
        is_covered = False
        for covered in covered_thin_signals:
            i_start, i_end, i_freqs = covered
            if set(c_freqs).issubset(i_freqs) and i_start <= c_start <= c_end <= i_end:
                is_covered = True
                break
        if not is_covered:
            covered_thin_signals.append(current)
            if len(c_freqs) >= 3:
                important_thin_signals.append(current)
            else:
                general_thin_signals.append(current)


    def plot_poc_and_volume_regions(poc_list_freq, real_poc_freq, thin_list_freq, last_price):
        # 创建图表
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # 获取所有价格数据用于确定坐标范围
        all_prices = []
        
        # 设置Y轴标签和位置
        periods = list(poc_list_freq.keys())
        y_labels = periods
        y_positions = range(len(periods))
        
        # 定义颜色映射
        colors = plt.cm.tab10(np.linspace(0, 1, len(periods)))
        
        # 绘制POC区域和真实POC
        for y_pos, (period, color) in enumerate(zip(periods, colors)):
            # 绘制POC区域
            poc_list = poc_list_freq[period]
            for poc_price, _, _ in poc_list:
                # 将单点POC扩展为小区域显示
                start = poc_price - 0
                end = poc_price + 1
                ax.add_patch(plt.Rectangle((start, y_pos - 0.3), end - start, 0.6, 
                                        facecolor=color, edgecolor='black', alpha=0.7))
                all_prices.extend([start, end])
            
            # 绘制真实POC
            real_poc = real_poc_freq[period][0]
            ax.plot(real_poc + 0.5 , y_pos, 'D', markersize=10, color=color, label=f'{period} POC')
            all_prices.append(real_poc)
        
        # 绘制成交量分布边缘区域
        for y_pos, (period, color) in enumerate(zip(periods, colors)):
            thin_list = thin_list_freq[period]
            for low, high, _ in thin_list:
                # 处理极值
                if high == 999999:
                    max_price = max(all_prices) + 1
                    high = max_price
                if low == 0:
                    low = min(all_prices) - 1
                
                # 绘制区域
                ax.add_patch(plt.Rectangle((low, y_pos - 0.4), high - low, 0.8, 
                                        facecolor='gray', edgecolor='black', alpha=0.3))
                all_prices.extend([low, high])
        
        
        # 添加最新价格线
        ax.axvline(x=last_price, color='red', linestyle='--', linewidth=2, label='lastprice')

        # 高亮显示重要信号区域（≥3个周期共振的POC区域）
        if 'important_signals' in locals() or 'important_signals' in globals():
            for signal in important_signals:
                start, end, freqs = signal
                ax.axvspan(start, end+1, alpha=0.3, color='green')
                # mid_price = (start + end) / 2
                # ax.text(mid_price, len(periods) - 0.5, f'POCarea: {start:.1f}-{end+1:.1f}', 
                #         ha='center', va='center', fontsize=9, color='darkgreen')
        
        # 高亮显示重要信号区域（≥3个周期共振的成交量分布边缘区域）
        if 'important_thin_signals' in locals() or 'important_thin_signals' in globals():
            for signal in important_thin_signals:
                low, high, freqs = signal
                ax.axvspan(low, high+1, alpha=0.3, color='gray')
                # mid_price = (low + high) / 2
                # ax.text(mid_price, len(periods) - 1.5, f'thinvolarea: {low:.1f}-{high:.1f}', 
                #         ha='center', va='center', fontsize=9, color='indigo')
        
        # 设置图表样式
        ax.set_yticks(y_positions)
        ax.set_yticklabels(y_labels)
        ax.set_xlabel('Price')
        ax.set_title('vol-price')
        ax.grid(True, axis='x', linestyle='--', alpha=0.7)
        
        # 自动调整X轴范围
        # min_price = round(last_price) - 50
        # max_price = round(last_price) + 50

        min_price = round(min(all_prices)) - 1
        max_price = round(max(all_prices)) + 1

        ax.xaxis.set_ticks(np.arange(round(min_price), round(max_price), 1), minor=True)
        ax.grid(True, which='minor', axis='x', linestyle=':', linewidth=0.5, alpha=0.8)
        

        ax.set_xlim(min_price, max_price)
        
        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = []
        for period, color in zip(periods, colors):
            legend_elements.append(Patch(facecolor=color, edgecolor='black', 
                                    label=f'{period} POC'))
        
        legend_elements.append(Patch(facecolor='gray', edgecolor='black',
                                label='thin_vol'))
        legend_elements.append(plt.Line2D([0], [0], marker='D', color='w', label='realPOC',
                    markerfacecolor='black', markersize=10))
        legend_elements.append(plt.Line2D([0], [0], color='red', linestyle='--', 
                    label='last_price'))
        
        legend_elements.append(Patch(facecolor='green', edgecolor='green',
                                label='poc_signal', alpha=0.3))
        legend_elements.append(Patch(facecolor='gray', edgecolor='purple',
                                label='thin_signal', alpha=0.3))
        
        ax.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        plt.show()

    if if_plt:
        plot_poc_and_volume_regions(poc_list_freq, real_poc_freq, thin_list_freq, last_price)

    # 返回结果
    return {
        'table': table_str,
        'important_signals': important_signals,
        'general_signals': general_signals,
        'important_thin_signals': important_thin_signals,
        'general_thin_signals': general_thin_signals
    }


def check_last_price_in_important_signals(last_price, important_signals, important_thin_signals):
    """
    判断 last_price 是否在重要信号区间内。

    参数:
        last_price (float): 当前最新价格
        important_signals (list): POC重要信号列表 [(start, end, freqs)]
        important_thin_signals (list): 成交量分布边缘重要信号列表 [(start, end, freqs)]

    返回:
        dict: 包含判断结果的字典
            - in_poc_signal (bool): 是否在POC重要信号区间内
            - in_thin_signal (bool): 是否在成交量分布边缘重要信号区间内
            - matched_poc_ranges (list): 匹配的POC区间 [(start, end)]
            - matched_thin_ranges (list): 匹配的thin区间 [(start, end)]
    """
    in_poc_signal = False
    in_thin_signal = False
    matched_poc_ranges = []
    matched_thin_ranges = []

    # 检查是否在POC重要信号区间内
    for start, end, _ in important_signals:
        if start <= last_price <= end + 1:
            in_poc_signal = True
            matched_poc_ranges.append((start, end + 1))

    # 检查是否在成交量分布边缘重要信号区间内
    for low, high, _ in important_thin_signals:
        if low <= last_price <= high + 1:
            in_thin_signal = True
            matched_thin_ranges.append((low, high + 1))

    return {
        'in_poc_signal': in_poc_signal,
        'in_thin_signal': in_thin_signal,
        'matched_poc_ranges': matched_poc_ranges,
        'matched_thin_ranges': matched_thin_ranges
    }
# 示例调用（假设已加载数据）
if __name__ == "__main__":
    result = analyze_and_generate_signals(end_date="2025-7-18 15:00:00", if_plt=True)
    # print(result['table'])
    display_signals("POC",result['important_signals'], result['general_signals'])
    display_signals("thin",result['important_thin_signals'], result['general_thin_signals'])
    check_res =  check_last_price_in_important_signals(last_price=3921.05, important_signals=result['important_signals'],important_thin_signals=result['important_thin_signals'])
    print(check_res)
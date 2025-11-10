import numpy as np
import pandas as pd
from tabulate import tabulate
from collections import defaultdict
from df_history import get_history
from vp_analyze import analyze_volume
import matplotlib.pyplot as plt

freq_map = {
    "1m": 30,
    "5m": 150,
    "15m": 450,
    "30m": 900,
    "60m": 1800,
    "1d": 7200,
    "1w": 7200 * 5,
    "1M": 7200 * 22
}
# freqs = ["1w","1d","60m","30m","15m","5m"]
# freqs = ["1d","60m","30m","15m","5m"]
freqs = ["60m","30m","15m","5m"]
# freqs = ["30m","15m","5m"]
# freqs = ['5m']
poc_list_freq ={}
thin_list_freq = {}
real_poc_freq = {}
for freq in freqs:
    count = freq_map[freq]
    df = get_history(count=count, start_date="2024-2-3 09:30:00",end_date="2025-6-13 15:00:00")
    # print(freq,len(df))
    # print(df.head(1))
    # print(df.tail(1))
    # last_price = df['close'].iloc[-1]
    # print(last_price)
    high_poc_list, thin_regions_list, real_poc = analyze_volume(df, freq=freq, bin_size=1, sense=10, if_plt=False)
    poc_list_freq[freq]=high_poc_list
    thin_list_freq[freq] = thin_regions_list
    real_poc_freq[freq] = real_poc

last_price = df['close'].iloc[-1]
# print(last_price)
# 准备表格数据
table_data = []


# 原始表格数据
table_data = []
for freq in freqs:
    real_poc_info = f"Real POC: {real_poc_freq[freq][0]}"
    poc_info = "\n".join([f"{poc_price},ratio:{vol_ratio:.2%}" for poc_price, vol, vol_ratio in poc_list_freq[freq]])
    thin_info = "\n".join([f"{low}-{high + 1},{total_ratio:.2%}" for low, high, total_ratio in thin_list_freq[freq]])
    table_data.append([freq, real_poc_info, poc_info, thin_info])

# 构建 DataFrame
df = pd.DataFrame(table_data, columns=["周期", "真实POC", "POC分布", "成交量分布边缘"])

# print(table_data)

# print(df)
# 转置 DataFrame
transposed_df = df.transpose()

# 打印转置后的表格
print(tabulate(transposed_df, headers="keys", tablefmt="grid"))

def merge_adjacent_prices(prices, threshold=2.0):
    """
    将相近的价格合并为区间。
    
    参数:22
        prices (list): 浮点数列表，代表POC价格
        threshold (float): 相邻价格的最大差值，用于判断是否连续
        
    返回:
        list: 合并后的区间列表 [(start, end)]
    """
    if not prices:
        return []

    sorted_prices = sorted(set(prices))  # 去重排序
    intervals = []
    start = sorted_prices[0]

    for i in range(1, len(sorted_prices)):
        if sorted_prices[i] - sorted_prices[i - 1] > threshold:
            intervals.append((start, sorted_prices[i - 1]))
            start = sorted_prices[i]
    intervals.append((start, sorted_prices[-1]))

    return intervals

# 构建每个价格被哪些周期覆盖的映射
price_coverage = defaultdict(list)

# 遍历所有周期及其POC价格
for freq in freqs:
    for poc_price, vol, vol_ratio in poc_list_freq[freq]:
        # 将附近的价格都标记为该频率覆盖（±threshold）
        for p in np.arange(poc_price - 2, poc_price + 2, 1):  # 使用更细粒度的步长
            price_coverage[round(float(p), 1)].append(freq)

# print(price_coverage)
# 收集重叠价格对应的周期组
overlap_groups = defaultdict(set)

for price, freqs_covered in price_coverage.items():
    if len(freqs_covered) >= 2:  # 至少两个周期才考虑
        freqs_tuple = tuple(sorted(set(freqs_covered)))  # 去重并排序
        overlap_groups[freqs_tuple].add(round(price, 1))

# print(overlap_groups)
# 按照信号等级分类：重要信号和一般信号
all_signals = []
important_signals = []
general_signals = []
from collections import defaultdict

# 已定义 merge_adjacent_prices 函数（见前文）

for key, prices in overlap_groups.items():
    overlapping_pocs = []

    # Step 1: 收集当前组合下所有周期的POC
    for freq in key:
        for poc_price, _, _ in poc_list_freq[freq]:
            if any(abs(poc_price - p) <= 1 for p in prices):
                overlapping_pocs.append((freq, poc_price))

    # print("overlapping pocs:", overlapping_pocs)

    # Step 2: 构建 price -> freq 映射
    price_to_freqs = defaultdict(set)
    for freq, poc in overlapping_pocs:
        price_to_freqs[poc].add(freq)

    # Step 3: 提取所有价格用于合并区间
    all_poc_prices = list(price_to_freqs.keys())
    merged_intervals = merge_adjacent_prices(all_poc_prices)

    # Step 4: 构建输出结果
    matched_ranges = []
    for start, end in merged_intervals:
        # 收集该区间内所有价格的周期集合
        common_freqs = set()
        for p in np.arange(start - 1, end + 2, 1):  # 覆盖整个区间
            p = round(float(p), 1)
            if p in price_to_freqs:
                common_freqs.update(price_to_freqs[p])
        common_freqs = tuple(sorted(common_freqs))

        matched_ranges.append((start, end, common_freqs))

    # print("matched_ranges:", matched_ranges)
    count = len(key)
    if count >= 2:
        all_signals.extend(matched_ranges)

# 去重处理：如果一般信号的区间被重要信号覆盖，则剔除
covered_signals = []
all_signals.sort(key=lambda x: (-len(x[2]), x[0]))
# print(all_signals)
for current in all_signals:
    c_start, c_end, c_freqs = current
    is_covered = False
    for i_start, i_end, i_freqs in covered_signals:
        # 判断是否被重要信号区间完全包含
        if set(c_freqs).issubset(i_freqs) and i_start <= c_start <= c_end <= i_end:
            is_covered = True
            break
    if not is_covered:
        covered_signals.append(current)
        if len(c_freqs) >= 3:
            important_signals.append(current)
        else:
            general_signals.append(current)
# 替换为过滤后的结果
# general_signals = filtered_general_signals
print("POC重要信号:", important_signals)
print("POC一般信号:", general_signals)

# 输出结果
print("\n【多周期POC重叠分析】\n")
if len(important_signals) > 0:
    print("——— 重要信号（≥3个周期）———")
    for poc_start, poc_end, i_freqs in important_signals:
        print(f"重要信号 | 周期: {','.join(i_freqs)} | POC区间: {poc_start:.1f}-{poc_end+1:.1f}")

if len(general_signals):
    print("\n——— 一般信号（=2个周期）———")
    for poc_start, poc_end, g_freqs in general_signals:
        print(f"一般信号 | 周期: {','.join(g_freqs)} | POC区间: {poc_start:.1f}-{poc_end+1:.1f}")




########## 成交量分布边缘共振分析
print("\n\n########## 成交量分布边缘共振分析 ##########")

# print(thin_list_freq)
# 构建每个价格被哪些周期覆盖的映射（针对成交量低谷区间的 low 和 high）
thin_price_coverage = defaultdict(list)

# print(freqs)
for freq in freqs:
    for low, high, total_ratio in thin_list_freq[freq]:
        # 排除极值边界
        if high == 999999:
            high = low + 1
        elif low == 0:
            low = high - 1

        # 标记这个 low ~ high 范围内的所有价格点为该频率覆盖
        for p in np.arange(low, high + 2, 1):
            thin_price_coverage[round(float(p), 1)].append(freq)

# print(thin_price_coverage)
# 收集重叠组：price -> freq list → group by tuple(freq_list)
thin_overlap_groups = defaultdict(set)

for price, freqs_covered in thin_price_coverage.items():
    if len(freqs_covered) >= 2:  # 至少两个周期才考虑
        key = tuple(sorted(set(freqs_covered)))  # 去重排序
        thin_overlap_groups[key].add(round(price, 1))

# print(thin_overlap_groups)

def merge_intervals(intervals):
    """
    合并连续区间
    """
    if not intervals:
        return []

    sorted_intervals = sorted(intervals)
    merged = [list(sorted_intervals[0])]
    for current in sorted_intervals[1:]:
        last = merged[-1]
        if current[0] <= last[1]:  # 可以合并
            last[1] = max(last[1], current[1])
        else:
            merged.append(list(current))
    merged = [tuple(interval) for interval in merged]
    return merged


all_thin_signals = []

for key, prices in thin_overlap_groups.items():
    overlapping_intervals = set()

    # Step 1: 找出这些周期中包含这些价格的原始区间
    for freq in key:
        for low, high, _ in thin_list_freq[freq]:
                    # 排除极值边界
            if high == 999999:
                high = low + 1
            elif low == 0:
                low = high - 1
            if any(low <= p <= high for p in prices):
                overlapping_intervals.add((low, high))

    # print(overlapping_intervals)
    # Step 2: 合并相邻区间
    merged = merge_intervals(overlapping_intervals)

    # print(merged)
    # Step 3: 构造信号格式 (start, end, freqs)
    for interval in merged:
        all_thin_signals.append((interval[0], interval[1], key))

# print(all_thin_signals)
# 去重处理：如果区间被更强信号覆盖，则剔除
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

print("\n【多周期成交量分布边缘重叠分析】\n")
if len(important_thin_signals) > 0:
    print("——— 重要信号（≥3个周期）———")
    for low, high, i_freqs in important_thin_signals:
        print(f"重要信号 | 周期: {','.join(i_freqs)} | 重叠区间: {low:.1f}-{high+1:.1f}")

if len(general_thin_signals) > 0:
    print("\n——— 一般信号（=2个周期）———")
    for low, high, g_freqs in general_thin_signals:
        print(f"一般信号 | 周期: {','.join(g_freqs)} | 重叠区间: {low:.1f}-{high+1:.1f}")

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

# 调用绘图函数
plot_poc_and_volume_regions(poc_list_freq, real_poc_freq, thin_list_freq, last_price)

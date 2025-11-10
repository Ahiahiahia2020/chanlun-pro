import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from matplotlib.gridspec import GridSpec
from df_simulate import generate_simulated_data

def fully_vectorized_volume_distribution(df, bin_size=0.1):
    lows = np.floor(df['low'].values)
    highs = np.ceil(df['high'].values)
    volumes = df['volume'].values

    # 计算每个区间的 bin 数量
    lengths = ((highs - lows) / bin_size).astype(int)

    # 确保至少有一个 bin
    lengths[lengths <= 0] = 1  # 避免出现长度为0的区间

    # 创建每行的起始值重复多次的数组
    starts = np.repeat(lows, lengths)

    # 构建每个 bin 对应的偏移量：[0, bin_size, 2*bin_size, ...]
    max_length = lengths.max()
    offsets = np.tile(np.arange(max_length), (len(lengths), 1)) * bin_size

    # 截断到每个样本的实际长度
    all_offsets = np.concatenate([offsets[i, :lengths[i]] for i in range(len(lengths))])

    # 构建所有价格 bin
    all_prices = starts + all_offsets

    # 构建对应的成交量分配
    volume_per_bin = (volumes / lengths).repeat(lengths)

    # 统计每个价格 bin 的成交量总和
    unique_prices, inverse = np.unique(all_prices, return_inverse=True)
    summed_volumes = np.bincount(inverse, weights=volume_per_bin)

    # 构造 DataFrame
    volume_df = pd.DataFrame({
        'mid_price': unique_prices,
        'volume': summed_volumes
    })
    volume_df['volume_ratio'] = (volume_df['volume'] / volume_df['volume'].sum()).apply(lambda x: round(x,4))
    volume_df_sorted = volume_df.sort_values('mid_price').reset_index(drop=True)

    return volume_df_sorted
def analyze_volume(df, freq= "1m", bin_size=1, sense=10, if_plt=True):
    freq_map = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "60m": "60min",
        "1d": "D",
        "1w": "W"
    }
    freq = freq_map[freq]

    # 分箱处理
    volume_df_sorted = fully_vectorized_volume_distribution(df, bin_size=1)

    # 提取 mid_points 和 volumes_sum 用于绘图
    mid_points = volume_df_sorted['mid_price']
    volumes_sum = volume_df_sorted['volume'].values

    # 计算POC
    poc_row = volume_df_sorted.loc[volume_df_sorted['volume'].idxmax()]
    poc = poc_row['mid_price']
    poc_volume_ratio = poc_row['volume_ratio']
    # print(f"POC: {poc}, POC 占比: {poc_volume_ratio:.2%}")
    real_poc = (poc,poc_volume_ratio)
    # 设置dense_threshold
    dense_threshold = max(0.01,poc_volume_ratio / sense) # 初始定义为 POC 成交量占比的 10%
    # print(f"Dense Threshold: {dense_threshold:.2%}")
    # 识别成交量密集区
    dense_regions = []
    i = 0
    n_regions = len(volume_df_sorted)
    while i < n_regions:
        if volume_df_sorted.iloc[i]['volume_ratio'] < dense_threshold:
            i += 1
            continue

        start_idx = i
        j = i
        while j < n_regions and volume_df_sorted.iloc[j]['volume_ratio'] >= dense_threshold:
            j += 1
        end_idx = j - 1
        dense_regions.append((start_idx, end_idx))
        i = j


    # 识别每个高成交量区域的POC
    high_volume_poc = []
    for start_idx, end_idx in dense_regions:
        region = volume_df_sorted.iloc[start_idx:end_idx+1]
        poc_row = region.loc[region['volume'].idxmax()]
        high_volume_poc.append(
            (poc_row['mid_price'],poc_row['volume'],poc_row['volume_ratio'])
        )
    # print(f"High Volume Regions: {high_volume_poc}")

    # 识别低成交量区域
    low_volume_regions = []

    # 处理左侧的低成交量区域
    if dense_regions and dense_regions[0][0] > 0:
        region = volume_df_sorted.iloc[0:dense_regions[0][0]]
        lower = region['mid_price'].iloc[0]
        upper = region['mid_price'].iloc[-1]
        total_ratio = round(region['volume_ratio'].sum(), 4)
        lower = 0
        low_volume_regions.append((lower, upper, total_ratio))

    # 处理密集区之间的低成交量区域
    for i in range(1, len(dense_regions)):
        prev_end = dense_regions[i-1][1]
        curr_start = dense_regions[i][0]
        if curr_start > prev_end + 1:
            region = volume_df_sorted.iloc[prev_end+1:curr_start]
            lower = region['mid_price'].iloc[0]
            upper = region['mid_price'].iloc[-1]
            total_ratio = round(region['volume_ratio'].sum(), 4)
            low_volume_regions.append((lower, upper, total_ratio))

    # 处理右侧的低成交量区域
    if dense_regions and dense_regions[-1][1] < n_regions - 1:
        region = volume_df_sorted.iloc[dense_regions[-1][1]+1:]
        lower = region['mid_price'].iloc[0]
        upper = region['mid_price'].iloc[-1]
        total_ratio = round(region['volume_ratio'].sum(), 4)
        upper = 999999
        low_volume_regions.append((lower, upper, total_ratio))
    
    # print(f"Low Volume Regions: {low_volume_regions}")
            # 绘图部分（仅在if_plt=True时执行）
    if if_plt:
        fig = plt.figure(figsize=(14, 6))
        gs = GridSpec(1, 3, width_ratios=[2, 0, 1], figure=fig)

        ax_k = fig.add_subplot(gs[0])
        ax_center = fig.add_subplot(gs[1])
        ax_vr = fig.add_subplot(gs[2])

        # 绘制K线图
        def resample_kline(df, frequency='5min'):
            """
            将1分钟K线数据聚合为指定周期的K线数据
            
            参数:
                df (pd.DataFrame): 原始1分钟K线数据，索引为datetime
                frequency (str): 目标周期，如 '5min', '15min', '30min' 等
            
            返回:
                pd.DataFrame: 聚合后的K线数据
            """
            rules = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }
            resampled_df = df.resample(frequency).agg(rules).dropna()
            return resampled_df
        resampled_df = resample_kline(df, freq)
        # print(freq)
        mpf.plot(resampled_df, type='candle', ax=ax_k, style='charles', show_nontrading=False, xrotation=0)
        ax_k.set_title(f'{freq} K', fontsize=12, pad=20)
        # 绘制VRVP图
        ax_vr.barh(mid_points, volumes_sum, height=bin_size * 0.8,
                   color='skyblue', edgecolor='black', alpha=0.8)

        # 计算总成交量和阈值对应的成交量值
        total_volume = volume_df_sorted['volume'].sum()
        threshold_volume = total_volume * dense_threshold

        # 添加成交量阈值线
        ax_vr.axvline(x=threshold_volume, color='orange', linestyle='--', linewidth=1.5,
                      label=f'{dense_threshold * 100:.2f}% Threshold')

        # # 高亮低成交量区域
        for lower, upper, _ in low_volume_regions:
            indices = np.where((np.array(mid_points) >= lower) & (np.array(mid_points) <= upper))[0]
            mid_points_highlight = [mid_points[i] for i in indices]
            volumes_sum_highlight = [volumes_sum[i] for i in indices]
            ax_vr.barh(
                mid_points_highlight,
                volumes_sum_highlight,
                height=bin_size * 0.8,
                color='red',
                alpha=0.3,
                edgecolor='none'
            )

        # 添加图例
        ax_vr.legend()

        # 水平镜像VRVP图
        ax_vr.invert_xaxis()

        # 设置x轴标签
        ax_vr.xaxis.set_label_position('top')
        ax_vr.xaxis.tick_top()
        ax_vr.set_xlabel('Volume', fontsize=10)

        # 标注每个高成交量区域的POC（恢复原方案，仅优化字体和文本位置）
        for idx, (poc_price, vol, vol_ratio) in enumerate(high_volume_poc):
            
            # 添加POC价格文本（字体调大，位置右移）
            ax_vr.text(
                vol,
                poc_price, 
                f"{poc_price:.2f}", 
                va='center', 
                ha='left',  # 保持左对齐
                fontsize=10,  # 字体调大
                color='red'
            )



        # 配置共享Y轴
        ylim = ax_k.get_ylim()
        ax_vr.set_ylim(ylim)
        ax_center.set_ylim(ylim)

        # 配置中间轴
        ax_center.yaxis.set_ticks_position('left')
        ax_center.tick_params(axis='y', which='both', left=True, right=False)
        ax_center.spines['top'].set_visible(False)
        ax_center.spines['bottom'].set_visible(False)
        ax_center.spines['left'].set_visible(True)
        ax_center.spines['right'].set_visible(False)
        ax_center.set_ylabel('Price', rotation=270, labelpad=20)

        # 配置其他轴
        ax_k.yaxis.set_visible(False)
        ax_vr.yaxis.set_visible(False)

        # 自动调整布局
        plt.tight_layout()
        plt.subplots_adjust(wspace=0)
        plt.show()

    # 返回结果
    return high_volume_poc, low_volume_regions, real_poc

def display_signals(signal_type, important_signals, general_signals):
    """
    通用方法：显示不同类型的关键信号和一般信号的价格区间。

    参数:
        signal_type (str): 信号类型名称（例如 "POC", "成交量分布边缘"）
        important_signals (list): 关键信号列表 [(start, end, freqs)]
        general_signals (list): 一般信号列表 [(start, end, freqs)]
    """
    print(f"\n【多周期{signal_type}重叠分析】\n")

    if len(important_signals) > 0:
        print("——— 重要信号（≥3个周期）———")
        for start, end, freqs in important_signals:
            print(f"重要信号 | 周期: {','.join(freqs)} | 区间: {start:.1f}-{end + 1:.1f}")

    if len(general_signals) > 0:
        print("\n——— 一般信号（=2个周期）———")
        for start, end, freqs in general_signals:
            print(f"一般信号 | 周期: {','.join(freqs)} | 区间: {start:.1f}-{end + 1:.1f}")
            
if __name__ == '__main__':
    df = generate_simulated_data(n=1440)
    print(df)
    # 调用函数
    high_poc_list, thin_regions_list, real_poc = analyze_volume(df,freq="30m", bin_size=0.5, sense=10, if_plt=True)

    # 打印结果
    print("真实POC:")
    print(f"POC: {real_poc[0]}, POC 占比: {real_poc[1]:.2%}")
    print("高成交量区域的POC:")
    for idx, (poc_price, vol, vol_ratio) in enumerate(high_poc_list):
        print(f"区域 {idx+1}: 价格 {poc_price:.2f}, 成交量占比 {vol_ratio * 100:.2f}%")

    print("\n低成交量区域:")
    for idx, (lower, upper, total_ratio) in enumerate(thin_regions_list):
        print(f"区域 {idx+1}: [{lower:.2f},  {upper:.2f}], 总占比 {total_ratio * 100:.2f}%")

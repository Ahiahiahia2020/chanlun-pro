import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import datetime
import pandas as pd
from df_history import get_history
from vp_analyze import analyze_volume, fully_vectorized_volume_distribution
import matplotlib.pyplot as plt
import mplfinance as mpf
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


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
# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
import numpy as np

class HistoricalBacktestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("历史回测 - 多周期K线与成交量分布图")
        
        # 默认参数
        self.default_code = "SHSE.000300"
        self.default_market = "a"
        self.default_freqs = ["5m", "15m", "30m", "60m"]
        self.default_step = datetime.timedelta(hours=1)
        self.base_count = 30
        self.freq_map = {
            "1m": self.base_count,
            "5m": self.base_count * 4,
            "15m": self.base_count * 12,
            "30m": self.base_count * 22,
            "60m": self.base_count * 35,
            "1d": self.base_count * 160,
            "1w": self.base_count * 160 * 5,
            "1M": self.base_count * 160 * 22
        }
        
        # 当前状态
        self.current_code = self.default_code
        self.current_market = self.default_market
        self.current_end_date = None
        self.current_freqs = self.default_freqs.copy()
        self.kline_data_cache = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Label(input_frame, text="股票代码:").grid(row=0, column=0, sticky=tk.W)
        self.code_var = tk.StringVar(value=self.default_code)
        ttk.Entry(input_frame, textvariable=self.code_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=(5, 10))
        
        ttk.Label(input_frame, text="市场:").grid(row=0, column=2, sticky=tk.W)
        self.market_var = tk.StringVar(value=self.default_market)
        market_combo = ttk.Combobox(input_frame, textvariable=self.market_var, values=["a", "hk", "us", "futures", "currency"], width=10, state="readonly")
        market_combo.grid(row=0, column=3, sticky=tk.W, padx=(5, 10))
        
        # 修改为只需要截止日期
        ttk.Label(input_frame, text="截止日期:").grid(row=1, column=0, sticky=tk.W)
        self.end_date_var = tk.StringVar()
        DateEntry(input_frame, textvariable=self.end_date_var, date_pattern='yyyy-mm-dd', width=12).grid(row=1, column=1, sticky=tk.W, padx=(5, 10))
        # 修改为只需要截止时间
        ttk.Label(input_frame, text="截止时间:").grid(row=1, column=2, sticky=tk.W)
        self.end_time_var = tk.StringVar(value="15:00")
        ttk.Entry(input_frame, textvariable=self.end_time_var, width=12).grid(row=1, column=3, sticky=tk.W, padx=(5, 10))
            
    
        ttk.Label(input_frame, text="周期:").grid(row=2, column=0, sticky=tk.W)
        self.freq_vars = {}
        freq_frame = ttk.Frame(input_frame)
        freq_frame.grid(row=2, column=1, columnspan=3, sticky=tk.W)
        for i, freq in enumerate(["1m", "5m", "15m", "30m", "60m", "1d"]):
            var = tk.BooleanVar(value=(freq in self.default_freqs))
            self.freq_vars[freq] = var
            ttk.Checkbutton(freq_frame, text=freq, variable=var).pack(side=tk.LEFT)
            
        ttk.Label(input_frame, text="步长:").grid(row=3, column=0, sticky=tk.W)
        self.step_var = tk.StringVar(value="1小时")
        step_combo = ttk.Combobox(input_frame, textvariable=self.step_var, values=["1分钟","5分钟","10分钟","15分钟","30分钟", "1小时", "1天"], width=10, state="readonly")
        step_combo.grid(row=3, column=1, sticky=tk.W, padx=(5, 10))
        
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=4, column=0, columnspan=4, pady=(10, 0))
        ttk.Button(button_frame, text="加载数据并绘图", command=self.load_and_plot).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="后退", command=self.step_backward).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="前进", command=self.step_forward).pack(side=tk.LEFT, padx=(0, 5))
        
        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        
        self.info_label = ttk.Label(self.plot_frame, text="请输入参数并点击'加载数据并绘图'")
        self.info_label.pack(expand=True)
        
    def get_step_delta(self):
        step_map = {
            "1分钟": datetime.timedelta(minutes=1),
            "5分钟": datetime.timedelta(minutes=5),
            "10分钟": datetime.timedelta(minutes=10),
            "15分钟": datetime.timedelta(minutes=15),
            "30分钟": datetime.timedelta(minutes=30),
            "1小时": datetime.timedelta(hours=1),
            "1天": datetime.timedelta(days=1)
        }
        return step_map.get(self.step_var.get(), self.default_step)
            
    def load_kline_data(self):
        """从数据库加载指定周期的K线数据"""
        self.kline_data_cache = {}
        try:
            for freq in self.current_freqs:
                # start_date = self.start_date_map[freq]
                count = freq_map[freq]
                print(self.current_code,count,self.current_end_date.strftime("%Y-%m-%d %H:%M:%S"))
                df = get_history(
                    market=self.current_market,
                    code=self.current_code,
                    frequency='1m', # 始终获取1分钟数据
                    # start_date=start_date.strftime("%Y-%m-%d %H:%M:%S"),
                    count=count,
                    end_date=self.current_end_date.strftime("%Y-%m-%d %H:%M:%S")
                )
                # print(df.iloc[0]["timestamp"],df.iloc[-1]["timestamp"])
                if df is not None and not df.empty:
                    self.kline_data_cache[freq] = df
                else:
                    messagebox.showwarning("警告", f"未能获取到 {freq} 周期的基础数据。")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"加载K线数据时出错: {e}")
            return False
            
    def plot_kline_and_volume_profiles(self):
        """绘制多周期K线图和成交量分布图"""
        if not self.kline_data_cache:
            messagebox.showwarning("警告", "没有可用的数据进行绘图。")
            return
            
        try:
            for widget in self.plot_frame.winfo_children():
                widget.destroy()
                
            n_rows = len(self.current_freqs)
            fig = plt.figure(figsize=(14, 4 * n_rows))
            
            for i, freq in enumerate(self.current_freqs):
                df_1m = self.kline_data_cache[freq]
                if df_1m.empty:
                    continue
                
                # 分析成交量分布 (不绘图)
                high_poc_list, thin_regions_list, real_poc = analyze_volume(df_1m, freq=freq, bin_size=1, sense=10, if_plt=False)
                volume_df_sorted = fully_vectorized_volume_distribution(df_1m, bin_size=1)
                
                if volume_df_sorted.empty:
                    continue
                
                # 创建子图网格
                gs = GridSpec(n_rows, 3, width_ratios=[2, 0, 1], figure=fig, hspace=0.4)
                ax_k = fig.add_subplot(gs[i, 0])
                ax_center = fig.add_subplot(gs[i, 1])
                ax_vr = fig.add_subplot(gs[i, 2])
                
                # 绘制K线图
                def resample_kline(df, frequency):
                    rules = {
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }
                    # 使用 vp_analyze.py 中的映射
                    freq_map_mpf = {
                        "1m": "1min",
                        "5m": "5min",
                        "15m": "15min",
                        "30m": "30min",
                        "60m": "60min",
                        "1d": "D",
                        "1w": "W"
                    }
                    frequency = freq_map_mpf.get(frequency, frequency)
                    resampled_df = df.resample(frequency).agg(rules).dropna()
                    return resampled_df
                    
                resampled_df = resample_kline(df_1m, freq)
                mpf.plot(resampled_df, type='candle', ax=ax_k, style='charles', show_nontrading=False, xrotation=0)
                ax_k.set_title(f'{freq} K线', fontsize=12, pad=20)
                
                # 绘制VRVP图 (参考 vp_analyze.py)
                mid_points = volume_df_sorted['mid_price']
                volumes_sum = volume_df_sorted['volume'].values
                
                poc_volume_ratio = real_poc[1]
                dense_threshold = max(0.01, poc_volume_ratio / 10)
                threshold_volume = volume_df_sorted['volume'].sum() * dense_threshold
                
                ax_vr.barh(mid_points, volumes_sum, height=1 * 0.8,
                           color='skyblue', edgecolor='black', alpha=0.8)
                ax_vr.axvline(x=threshold_volume, color='orange', linestyle='--', linewidth=1.5,
                              label=f'{dense_threshold * 100:.2f}% 阈值')

                # 高亮低成交量区域
                for lower, upper, _ in thin_regions_list:
                    high_val = upper
                    low_val = lower
                    if upper == 999999:
                        high_val = lower + 1
                    if lower == 0:
                        low_val = upper - 1
                    indices = np.where((np.array(mid_points) >= low_val) & (np.array(mid_points) <= high_val))[0]
                    if len(indices) > 0:
                        mid_points_highlight = [mid_points[i] for i in indices]
                        volumes_sum_highlight = [volumes_sum[i] for i in indices]
                        ax_vr.barh(
                            mid_points_highlight,
                            volumes_sum_highlight,
                            height=1 * 0.8,
                            color='red',
                            alpha=0.3,
                            edgecolor='none'
                        )

                # 标注高成交量区域的POC
                for idx, (poc_price, vol, vol_ratio) in enumerate(high_poc_list):
                    ax_vr.plot(
                        vol,
                        poc_price, 
                        'ro', markersize=8
                    )
                    ax_vr.text(
                        vol,
                        poc_price, 
                        f"{poc_price:.2f}", 
                        va='center', 
                        ha='left',
                        fontsize=9,
                        color='red'
                    )

                ax_vr.legend()
                ax_vr.invert_xaxis()
                ax_vr.xaxis.set_label_position('top')
                ax_vr.xaxis.tick_top()
                ax_vr.set_xlabel('成交量', fontsize=10)
                
                # 配置共享Y轴
                ylim = ax_k.get_ylim()
                ax_vr.set_ylim(ylim)
                ax_center.set_ylim(ylim)

                ax_center.yaxis.set_ticks_position('left')
                ax_center.tick_params(axis='y', which='both', left=True, right=False)
                ax_center.spines['top'].set_visible(False)
                ax_center.spines['bottom'].set_visible(False)
                ax_center.spines['left'].set_visible(True)
                ax_center.spines['right'].set_visible(False)
                ax_center.set_ylabel('价格', rotation=270, labelpad=20)

                ax_k.yaxis.set_visible(False)
                ax_vr.yaxis.set_visible(False)

            fig.suptitle(f'{self.current_code} 多周期K线与成交量分布 - 截止日期: {self.current_end_date.strftime("%Y-%m-%d %H:%M:%S")}', fontsize=16)
            plt.tight_layout(rect=[0, 0.03, 1, 0.97])
            
            canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            messagebox.showerror("错误", f"绘制图表时出错: {e}")
            
    def load_and_plot(self):
        try:
            self.current_code = self.code_var.get()
            self.current_market = self.market_var.get()
            
            end_date_str = self.end_date_var.get()
            if not end_date_str:
                messagebox.showwarning("警告", "请选择截止日期。")
                return
                
            end_time_str = self.end_time_var.get()
            end_datetime_str = f"{end_date_str} {end_time_str}:00"
            self.current_end_date = datetime.datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M:%S")
            
            self.current_freqs = [freq for freq, var in self.freq_vars.items() if var.get()]
            if not self.current_freqs:
                messagebox.showwarning("警告", "请至少选择一个周期。")
                return
            if not self.load_kline_data():
                return
                
            self.plot_kline_and_volume_profiles()
            
        except ValueError:
            messagebox.showerror("错误", "日期格式无效。")
        except Exception as e:
            messagebox.showerror("错误", f"加载或绘图过程中发生未知错误: {e}")
            
    def step_backward(self):
        if not self.current_end_date:
            messagebox.showwarning("警告", "请先加载数据。")
            return
            
        step_delta = self.get_step_delta()
        self.current_end_date -= step_delta
        self.end_date_var.set(self.current_end_date.strftime("%Y-%m-%d"))
        self.end_time_var.set(self.current_end_date.strftime("%H:%M"))
        if not self.load_kline_data():
            self.current_end_date += step_delta
            self.end_date_var.set(self.current_end_date.strftime("%Y-%m-%d"))
            return
            
        self.plot_kline_and_volume_profiles()
        
    def step_forward(self):
        if not self.current_end_date:
            messagebox.showwarning("警告", "请先加载数据。")
            return
            
        step_delta = self.get_step_delta()
        self.current_end_date += step_delta
        self.end_date_var.set(self.current_end_date.strftime("%Y-%m-%d"))
        self.end_time_var.set(self.current_end_date.strftime("%H:%M"))
        if not self.load_kline_data():
            self.current_end_date -= step_delta
            self.end_date_var.set(self.current_end_date.strftime("%Y-%m-%d"))
            return
            
        self.plot_kline_and_volume_profiles()

if __name__ == "__main__":
    root = tk.Tk()
    app = HistoricalBacktestApp(root)
    root.mainloop()
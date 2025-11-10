# file: c:\chanlun20141115\chanlun-pro\notebook\mycode\charts_gui.py
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime
from df_history import get_history
from vp_analyze import analyze_volume

class ChartApp:
    def __init__(self, root):
        self.root = root
        self.root.title("多周期K线与成交量分布")

        # 日期输入
        self.label = ttk.Label(root, text="选择结束日期时间:")
        self.label.pack(pady=5)

        self.date_entry = ttk.Entry(root)
        self.date_entry.insert(0, "2025-06-13 15:00:00")
        self.date_entry.pack(pady=5)

        self.button = ttk.Button(root, text="更新图表", command=self.update_charts)
        self.button.pack(pady=10)

        # 图表区域
        self.fig, self.axes = plt.subplots(3, 2, figsize=(14, 10))
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack()

    def update_charts(self):
        end_date_str = self.date_entry.get()
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print("日期格式错误，请使用 YYYY-MM-DD HH:MM:SS")
            return

        freqs = ["30m", "15m", "5m"]

        for i, freq in enumerate(freqs):
            count = {
                "1m": 30,
                "5m": 120,
                "15m": 480,
                "30m": 960,
                "60m": 1920
            }.get(freq, 30)

            df = get_history(count=count, start_date="2024-02-03 09:30:00", end_date=end_date_str, freq=freq)

            # 绘制K线图
            self.plot_kline(self.axes[i, 0], df, freq)

            # 绘制成交量分布图
            self.plot_volume_distribution(self.axes[i, 1], df, freq)

        self.canvas.draw()

    def plot_kline(self, ax, df, freq):
        ax.clear()
        ax.set_title(f"{freq} K线图")
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))

        # K线图
        ax.plot(df.index, df['close'], label='Close', color='black')
        ax.fill_between(df.index, df['low'], df['high'], color='gray', alpha=0.3)

        ax.grid(True)

    def plot_volume_distribution(self, ax, df, freq):
        ax.clear()
        ax.set_title(f"{freq} 成交量分布")
        volume_df = analyze_volume(df, freq=freq, bin_size=1, sense=10, if_plt=False)[1]

        # 提取 mid_price 和 volume
        mid_points = [item[0] for item in volume_df]
        volumes = [item[1] for item in volume_df]

        ax.barh(mid_points, volumes, height=0.8, color='skyblue', edgecolor='black', alpha=0.8)
        ax.set_xlabel("成交量")
        ax.set_ylabel("价格")
        ax.grid(True, axis='x')


if __name__ == "__main__":
    root = tk.Tk()
    app = ChartApp(root)
    root.mainloop()
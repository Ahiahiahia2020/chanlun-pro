from chanlun.backtesting.backtest_klines import BackTestKlines
from chanlun import kcharts
from chanlun.cl_utils import query_cl_chart_config
from chanlun.exchange.exchange import *
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from chanlun.exchange.exchange_db import ExchangeDB
import time
from chanlun import cl
from tkhtmlview import HTMLLabel

market = 'a'
code = 'SH.600285'
start_date = '2021-02-02 15:00:00'
end_date = '2023-05-11 15:00:00'
frequencys = ['d']
ex = ExchangeDB(market)  # 读取数据库中的k线数据
cl_config = query_cl_chart_config(market, code)  # 读取缠论配置


class StockHistoryViewer:
    def __init__(self):
        """初始化查看器"""
        self.supported_periods = ['1m', '5m', '30m', '60m', 'd', '2d', 'w']
        self.setup_gui()
        
    def setup_gui(self):
        """设置图形界面"""
        self.root = tk.Tk()
        self.root.title("股票历史K线查看器")
        self.root.geometry("1200x800")
        
        # 创建输入框架
        input_frame = ttk.Frame(self.root, padding="10")
        input_frame.pack(fill=tk.X)
        
        # 股票代码输入
        ttk.Label(input_frame, text="股票代码:").pack(side=tk.LEFT, padx=5)
        self.code_var = tk.StringVar()
        self.code_entry = ttk.Entry(input_frame, textvariable=self.code_var)
        self.code_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(input_frame, text="(格式: SH.600000)").pack(side=tk.LEFT)
        
        # 周期选择
        ttk.Label(input_frame, text="K线周期:").pack(side=tk.LEFT, padx=5)
        self.period_var = tk.StringVar()
        period_combo = ttk.Combobox(input_frame, textvariable=self.period_var, 
                                  values=self.supported_periods, width=5)
        period_combo.pack(side=tk.LEFT, padx=5)
        period_combo.set(self.supported_periods[0])
        
        # 查询按钮
        ttk.Button(input_frame, text="查看K线", 
                  command=self.on_view_click).pack(side=tk.LEFT, padx=20)
        
        # 创建图表区域
        self.figure_frame = ttk.Frame(self.root)
        self.figure_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
    def on_view_click(self):
        """查看按钮点击事件处理"""
        code = self.code_var.get().strip()
        period = self.period_var.get()
        
        if self.validate_inputs(code, period):
            self.view_history(code, period)
        
    def validate_inputs(self, code: str, period: str) -> bool:
        """验证输入参数的有效性"""
        # 验证股票代码格式
        if not code.startswith(('SH.', 'SZ.')):
            messagebox.showerror("错误", "股票代码必须以'SH.'或'SZ.'开头")
            return False
            
        # 验证周期格式
        if period not in self.supported_periods:
            messagebox.showerror("错误", 
                f"不支持的周期类型。支持的周期包括: {', '.join(self.supported_periods)}")
            return False
            
        return True
        
    def get_history_data(self, code: str, period: str, start_date=None, end_date=None):
        """从数据库获取历史数据
        这里先用占位符，等待API提供后替换
        """
        # TODO: 实现实际的数据获取逻辑
        klines = ex.klines(code, frequency=period, start_date=start_date, end_date=end_date)
        klines = klines[:]
        print(period, '获取K线数据量：', len(klines))
        _s = time.time()
        cd = (cl.CL(code, period, cl_config).process_klines(klines))
        print('Run time: ', time.time() - _s)
        return cd

    def plot_kline(self, cd):
        """绘制K线图"""
        # 清除旧图表
        for widget in self.figure_frame.winfo_children():
            widget.destroy()
            
        # 生成 HTML 内容
        title = '%s - 【%s】 周期数据图表' % (cd.code, cd.frequency)
        html_content = kcharts.render_charts(title, cd)
        
        # 创建 HTMLLabel 小部件
        self.html_label = HTMLLabel(self.figure_frame, html=html_content)
        self.html_label.pack(fill=tk.BOTH, expand=True)
        
    def view_history(self, code: str, period: str, start_date=None, end_date=None):
        """主要接口：查看历史K线"""
        try:
            # 获取数据
            cd = self.get_history_data(code, period, start_date, end_date)
            if cd is None:
                messagebox.showwarning("警告", "未获取到数据")
                return
                
            # 绘制K线图
            self.plot_kline(cd)
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
            
    def run(self):
        """运行程序"""
        self.root.mainloop()

def main():
    viewer = StockHistoryViewer()
    viewer.run()

if __name__ == "__main__":
    main()
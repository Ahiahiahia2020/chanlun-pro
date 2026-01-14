import pickle
import pandas as pd
from gm.api import *
from tqdm.auto import tqdm
from chanlun import config, fun
from chanlun.exchange.exchange_db import ExchangeDB
import traceback
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from tqdm.auto import tqdm
import logging
from chanlun.backtesting.backtest_klines import BackTestKlines
from chanlun.cl_utils import *
from chanlun.db import db
from chanlun.zixuan import ZiXuan
from chanlun.config import get_data_path
from chanlun.xuangu import xuangu
import datetime
from chanlun.utils import send_fs_msg_mine
import talib
import os

# 如在远程执行，需要制定掘金终端地址  https://www.myquant.cn/docs/gm3_faq/154#b244aeed0032526e
set_serv_addr(config.GM_SERVER_ADDR)
# 设置token， 查看已有token ID,在用户-秘钥管理里获取
set_token(config.GM_TOKEN)

db_ex = ExchangeDB("a")

symbols = get_symbols(sec_type1=1010, sec_type2=101001)
run_codes = [_s["exchange"] + "." + _s["sec_id"] for _s in symbols]
def to_tdx_codes(_codes):
    return [_code.replace("SHSE.", "SH.").replace("SZSE.", "SZ.") for _code in _codes]
run_codes = to_tdx_codes(run_codes)
print("Sync Len : ", len(run_codes))

# 配置日志
current_time = datetime.datetime.now().strftime('%Y%m%d')
logging.basicConfig(
    filename=f'F:\\history_xuangu\\run_xuangu_{current_time}.log',  # 日志文件名自适应当前时间
    filemode='a',           # 文件模式
    format='%(asctime)s - %(levelname)s - %(message)s',  # 日志格式
    level=logging.INFO      # 日志级别
)

    
class HistoryXuangu(object):

    def __init__(self):
        # 选股市场
        self.market = "a"
        # 选股日期范围
        self.xg_start_date = "2024-01-01 09:00:00"
        self.xg_end_date = "2025-12-27 15:00:00"
        # 选股周期
        self.freqencys = ["w","d"]
        # 缠论配置
        self.cl_config = query_cl_chart_config(self.market, "SH.000300")

        # 加入的自选
        self.zx = ZiXuan(self.market)
        self.zx_group = "测试选股"
        self.zx.add_zx_group(self.zx_group)

        # # 清除自选与标记
        self.zx.clear_zx_stocks(self.zx_group)
        # db.marks_del(self.market, "XG")
        # 选股结果保存文件 确保有这个目录
        print( get_data_path())
        self.xg_result_path = "F:\\history_xuangu"
        # logging.info(f"选股结果保存文件 {self.xg_result_path}")
        self.xuangu_date = set()
        self.signal = 0
        self.bottom_price = 0
        self.neck_price = 0

    # 三周期选股，此处只选大周期和中周期，大周期默认周线，中周期默认日线
    # 第一步：大周期趋势过滤（周线）- 解决“做多还是做空”的问题

    # 做多条件（必须同时满足）：
    # 价格位置： 收盘价 > 20周移动平均线。
    # 趋势方向： 本周的20周均线数值 > 上周的20周均线数值。这确保了我们所顺的“大势”是正在发生的、动态的上升趋势。
    # 第二步：中周期选股与定位（日线）- 解决“在哪买”的问题

    # 在满足周线条件的股票池中，寻找日线级别出现 “明确的底部右侧第二个低点”形态，该形态的定义如下：

    # 结构：
    # 存在一个清晰的底部（前期显著低点）。
    # 股价从底部反弹后，再次回调，形成第二个低点。
    # 量化规则：
    # 价格差： 两个低点的价格相差不超过1.5%。
    # 时间差： 两个低点的时间间隔不少于10个交易日。
    # 颈线： 连接两个低点之间的反弹高点，形成一条颈线。颈线可以是水平或略微倾斜。
    # 成交量特征： 在形成第二个低点的过程中，成交量必须呈现明显的萎缩，表明抛压竭尽。
    # 此时，该股进入密切监控名单。
    def xuangu_by_code(self, code: str, date_str="2025-01-01"):
        """
        给定一个股票代码，执行该股票的历史选股
        """

        # 初始化代码的回测类
        bk = BackTestKlines(
            self.market,
            start_date=self.xg_start_date,
            end_date=self.xg_end_date,
            frequencys=self.freqencys,
            cl_config=self.cl_config,
        )
        bk.init(code, self.freqencys[-1])
        # 清空标记
        db.marks_del_all_by_code(self.market, code)
        xg_res = []
        last_xd_end_date = set()
        while bk.next():
            # 每根k线进行回放执行
            try:
                if self.signal == 0:
                    # logging.info(f"开始处理股票代码 {code}")
                    is_ok = False  # 记录当前是否被选中
                    # 获取当前k线
                    high_klines = bk.klines(code, frequency=bk.frequencys[0])
                    # 周线不足22根，跳过
                    if len(high_klines) <= 22:
                        continue
                    # 获取当前缠论数据对象
                    high_cd = bk.get_cl_data(code, bk.frequencys[0])
                    high_klines = high_cd.get_src_klines()
                    high_last_k = high_klines[-1]
                    # pre_k = klines[-2]

                    closes = np.array([_k.c for _k in high_klines])
                    # ma5 = talib.MA(closes, timeperiod=5)
                    ma20 = talib.MA(closes, timeperiod=20)
                    # 大级别满足要求
                    if  not ((high_last_k.c > ma20[-1]) and (ma20[-1] > ma20[-2]) ):
                        continue

                # 中级别形态识别
                mid_cd = bk.get_cl_data(code, bk.frequencys[1])
                klines = mid_cd.get_src_klines()
                last_k = klines[-1]
                kdate = last_k.date
                # pre_k = klines[-2]
                if self.signal == 1:
                    if last_k.c < self.bottom_price:
                        self.signal = 2
                        msg = f"{last_k.c}跌破W底{self.bottom_price},形态失效,sig{self.signal}"
                        self.signal = 0
                        print(msg)
                        db.marks_add(
                        self.market,
                        code.replace("SHSE.", "SH.").replace("SZSE.", "SZ."),
                        "",
                        "",
                        fun.datetime_to_int(kdate),
                        "XG",
                        msg,
                        "earningUp",
                        "green",
                        )
                    elif last_k.c > self.neck_price:
                        self.signal = 5
                        msg = f"{last_k.date},{last_k.c}突破颈线{self.neck_price},sig{self.signal}"
                        self.signal = 0
                        print(msg)
                        db.marks_add(
                        self.market,
                        code.replace("SHSE.", "SH.").replace("SZSE.", "SZ."),
                        "",
                        "",
                        fun.datetime_to_int(kdate),
                        "XG",
                        msg,
                        "earningUp",
                        "yellow",
                        )
                bis = mid_cd.get_bis()
                reference_date = pd.Timestamp(date_str).tz_localize('UTC')
                if kdate < reference_date:
                    continue
                if len(bis) <= 3:
                    continue
                last_bi = bis[-1]
                if last_bi.type == "up":
                    continue
                if last_bi.end.k.date in self.xuangu_date:
                    continue
                pre_bi = bis[-2]
                prepre_bi = bis[-3]
                if prepre_bi.end.k.date in self.xuangu_date and self.signal == 1:
                    self.signal = 3
                    msg = f"震荡延续,sig{self.signal}"
                    self.signal = 0
                    print(msg)
                    db.marks_add(
                    self.market,
                    code.replace("SHSE.", "SH.").replace("SZSE.", "SZ."),
                    "",
                    "",
                    fun.datetime_to_int(kdate),
                    "XG",
                    msg,
                    "earningUp",
                    "green",
                    )
                k_delta = last_k.index - last_bi.end.k.klines[-1].index
                amounts = np.array([_k.a for _k in klines])
                ma5_a = talib.MA(amounts, timeperiod=5)
                # W底的下跌笔完成且两个低点价格差不超过1.5%
                if last_bi.is_done() and prepre_bi.high > pre_bi.high and abs(last_bi.low - pre_bi.low) / pre_bi.low < 0.015 and last_bi.end.k.a < ma5_a[-1 - k_delta]:
                    self.neck_price = last_bi.high
                    neck_date = last_bi.start.k.date
                    self.xuangu_date.add(last_bi.end.k.date)
                    self.signal = 1
                    self.bottom_price = min(last_bi.low, pre_bi.low)
                    if last_k.c >=  self.neck_price:
                        self.signal = 9
                        print("当天突破颈线，后续跟踪回踩")
                    msg = "股票{};{}颈线位{}于{};笔结束日期:{};检出日期：{};w_price:{};k_delta:{},sig:{};".format(high_cd.get_code(),mid_cd.get_frequency(),self.neck_price,neck_date,last_bi.end.k.date,kdate,self.bottom_price,k_delta,self.signal)
                    print(msg)
                    self.signal= 1
                    # send_fs_msg_mine("选股","选股：",msg)
                    # 记录选股信息
                    xg_res.append(
                        {
                            "code": code,
                            "neck_price": self.neck_price,
                            "neck_date": neck_date,
                            "last_bi_end_date": last_bi.end.k.date,
                            "kdate": kdate,
                        }
                    )
                    # 添加到自选，在图表中添加记录
                    self.zx.add_stock(self.zx_group, code, None)
                    db.marks_add(
                        self.market,
                        code.replace("SHSE.", "SH.").replace("SZSE.", "SZ."),
                        "",
                        "",
                        fun.datetime_to_int(kdate),
                        "XG",
                        msg,
                        "earningUp",
                        "red",
                    )
                    logging.info(msg)

            except Exception as e:
                print(f"{code} 选股异常")
                print(traceback.format_exc())
                logging.error(f"{code} 选股异常: {e},{traceback.format_exc()}")

        # 保存选股结果
        filepath = f"{self.xg_result_path}\\xg_{code}.pkl"
        with open(filepath, "wb") as fp:
            pickle.dump(xg_res, fp)
        # print(klines)
        return True


if __name__ == "__main__":
    # 要执行历史选股的股票列表
    # run_codes = ["SZ.301131", "SZ.300265", "SZ.300991", "SZ.300455", "SH.603018", "SH.601155"]
    db_ex = ExchangeDB("a")
    # 实例化
    hxg = HistoryXuangu()

    print("开始选股")
    print(f"{hxg.xg_start_date} ~ {hxg.xg_end_date}")

    # TODO 测试单个选股
    # hxg.xuangu_by_code('SH.600396')

    # # # TODO 多进程执行选股，根据自己 cpu 核数来调整
    with ProcessPoolExecutor(
        max_workers=22, mp_context=get_context("spawn")
    ) as executor:
        bar = tqdm(total=len(run_codes))
        for _ in executor.map(
            hxg.xuangu_by_code,
            run_codes,
        ):
            bar.update(1)

    print("Done")

    

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
from chanlun import fun
from chanlun.backtesting.backtest_klines import BackTestKlines
from chanlun.cl_utils import (
    query_cl_chart_config,
)
from chanlun.db import db
from chanlun.zixuan import ZiXuan
from chanlun.config import get_data_path
from chanlun.xuangu import xuangu
import datetime

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
    filename=f'run_xuangu_{current_time}.log',  # 日志文件名自适应当前时间
    filemode='a',           # 文件模式
    format='%(asctime)s - %(levelname)s - %(message)s',  # 日志格式
    level=logging.INFO      # 日志级别
)

class HistoryXuangu(object):

    def __init__(self):
        # 选股市场
        self.market = "a"
        # 选股日期范围
        self.xg_start_date = "2002-09-01 15:00:00"
        self.xg_end_date = "2024-12-27 15:00:00"
        # 选股周期
        self.freqencys = ["d"]
        # 缠论配置
        self.cl_config = query_cl_chart_config(self.market, "SH.603826")

        # 加入的自选
        self.zx = ZiXuan(self.market)
        self.zx_group = "测试选股"
        # 清除自选与标记
        self.zx.clear_zx_stocks(self.zx_group)
        db.marks_del(self.market, "XG")

        # 选股结果保存文件 确保有这个目录
        self.xg_result_path = get_data_path() / "history_xuangu"
        # logging.info(f"选股结果保存文件 {self.xg_result_path}")

    def xuangu_by_code(self, code: str, date_str="2024-12-25"):
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

        xg_res = []
        last_xd_end_date = set()
        while bk.next():
            # 每根k线进行回放执行
            try:
                # logging.info(f"开始处理股票代码 {code}")
                is_ok = False  # 记录当前是否被选中
                # 获取当前k线
                klines = bk.klines(code, frequency=bk.frequencys[0])
                if len(klines) <= 100:
                    continue
                # 获取当前缠论数据对象
                cd = bk.get_cl_data(code, bk.frequencys[0])
                lines = cd.get_xds()
                if (len(lines) < 5):
                    continue
                msgs = ""
                line = lines[-1]
                kdate = cd.get_src_klines()[-1].date
                reference_date = pd.Timestamp(date_str).tz_localize('UTC')
                # print(kdate)
                if (len(lines) >= 5 
                    and line.type == 'down'
                    and (min(lines[-5].high,lines[-3].high,line.high) > max(lines[-5].low,lines[-3].low,line.low))
                    and lines[-2].high == lines[-2].end_line.high
                    and line.low == line.end_line.low
                    and line.low > lines[-3].low 
                    and line.end.done
                    #and line.end.k.date > reference_date

                ):

                    if (line.end_line.index - line.start_line.index <=5) \
                        and line.low == line.end_line.end.val :
                        if line.end_line.index - line.start_line.index == 4:
                            bis = cd.get_bis()
                            bi_4 = bis[line.start_line.index + 3]
                            if bi_4.mmd_exists(["3sell"]) :
                                xc_ld_bc = xuangu.compare_xingcheng_ld(bis[line.start_line.index + 2],line.end_line)
                            else :
                                xc_ld_bc = xuangu.compare_xingcheng_ld(line.start_line,line.end_line)
                        else:
                            xc_ld_bc = xuangu.compare_xingcheng_ld(line.start_line,line.end_line)
                        if xc_ld_bc:
                            # print("{}周期{}段内笔行程背驰,线段结束时间：{}".format(cd.get_code(),cd.get_frequency(),line.end.k.date))
                            deas_xd = cd.get_idx()['macd']['dea'][line.start_line.start.k.k_index:line.end_line.end.k.k_index + 1]
                            if ((len(deas_xd) > 0) and deas_xd[-1] <= min(deas_xd)): #负数 
                                # print("线段结束时def值新低：{:.2f}".format(deas_xd[-1]))
                                macds_xd = cd.get_idx()['macd']['hist'][line.start_line.start.k.k_index:line.end_line.end.k.k_index + 1]
                                macds_bi = cd.get_idx()['macd']['hist'][line.end_line.start.k.k_index:line.end_line.end.k.k_index + 1]
                                macds_bi_last = macds_bi[int(len(macds_bi)/2):]
                                if abs(min(macds_bi_last)) < abs(min(macds_xd)): #柱子高度不创新高
                                    # print("线段结束MACD柱子高度不创新高，形成一买")
                                        # print(last_xd_end_date)
                                    if line.end.k.date not in last_xd_end_date:
                                        last_xd_end_date.add(line.end.k.date)
                                        msg = "{}周期{}形态符合要求且形成一买，线段结束时间：{},检出时间{}\n".format(cd.get_code(),cd.get_frequency(),line.end.k.date,kdate)                                    
                                        print(msg)
                                        msgs += msg
                                        is_ok = True



                if is_ok:
                    # 记录选股信息
                    xg_res.append(
                        {
                            "code": code,
                        }
                    )
                    # 添加到自选，在图表中添加记录
                    self.zx.add_stock(self.zx_group, code, None)
                    db.marks_add(
                        self.market,
                        code.replace("SHSE.", "SH.").replace("SZSE.", "SZ."),
                        "",
                        "",
                        fun.datetime_to_int(cd.get_src_klines()[-1].date),
                        "XG",
                        msgs,
                        "earningUp",
                        "red",
                    )
                    logging.info(msgs)

            except Exception as e:
                print(f"{code} 选股异常")
                print(traceback.format_exc())
                logging.error(f"{code} 选股异常: {e},{traceback.format_exc()}")

        # 保存选股结果
        with open(self.xg_result_path / f"xg_{code}.pkl", "wb") as fp:
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
    # hxg.xuangu_by_code('SH.600269')

    # TODO 多进程执行选股，根据自己 cpu 核数来调整
    with ProcessPoolExecutor(
        max_workers=20, mp_context=get_context("spawn")
    ) as executor:
        bar = tqdm(total=len(run_codes))
        for _ in executor.map(
            hxg.xuangu_by_code,
            run_codes,
        ):
            bar.update(1)

    print("Done")

    

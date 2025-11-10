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
from chanlun.cl_utils import *
from chanlun.db import db
from chanlun.zixuan import ZiXuan
from chanlun.config import get_data_path
from chanlun.xuangu import xuangu
import datetime
from chanlun.utils import send_fs_msg_mine


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



def xingchenglidu(line: LINE) -> list:
    """
    计算线的行程力度（取绝对值）

    行程力度 = dy / dx
        dy = 终点与起点的绝对值差异
        dx = 线段之间的k线数量
    """
    if line.end.val == line.start.val:
        return 0

    dy = abs(line.end.val - line.start.val)
    dx = line.end.k.k_index - line.start.k.k_index
    return [dy, dx, dy/dx]

def compare_xingcheng_ld(one_line: LINE, two_line: LINE):
    """
    比较两个线的力度，后者小于前者，返回 True
    :param one_line:
    :param two_line:
    :return:
    """
    dy1, dx1, ld1 = xingchenglidu(one_line)
    dy2, dx2, ld2 = xingchenglidu(two_line)
    if ( (dy2 > dy1) and  (ld2 < ld1)):
        return True
    else:
        return False
    
class HistoryXuangu(object):

    def __init__(self):
        # 选股市场
        self.market = "a"
        # 选股日期范围
        self.xg_start_date = "2017-01-01 09:00:00"
        self.xg_end_date = "2025-12-27  09:00:00"
        # 选股周期
        self.freqencys = ["d"]
        # 缠论配置
        self.cl_config = query_cl_chart_config(self.market, "SH.000300")

        # 加入的自选
        self.zx = ZiXuan(self.market)
        self.zx_group = "测试选股"
        # 清除自选与标记
        self.zx.clear_zx_stocks(self.zx_group)
        db.marks_del(self.market, "XG")

        # 选股结果保存文件 确保有这个目录
        self.xg_result_path = get_data_path() / "history_xuangu"
        logging.info(f"选股结果保存文件 {self.xg_result_path}")
        self.codes_info = {}

    def xuangu_by_code(self, code: str, datestr="2019-01-01"):
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
                xds = cd.get_xds()
                if len(xds) < 5 :
                    continue
                bis = cd.get_bis()

                reference_date = pd.Timestamp(datestr).tz_localize('UTC')
                msg = "股票代码：{}，选股周期{},".format(cd.get_code(),cd.get_frequency())
                xc_ld_bc = False
                if (xds[-1].type == 'down' and len(xds) >= 5):
                    xds = xds[-5:]
                else :
                    continue
                xd = xds[-1]
                xd01 = xds[0]
                xd12 = xds[1]
                xd23 = xds[2]
                xd34 = xds[3]
                xd45 = xds[4]
                xd01_dy, xd01_dx, xd01_ld = xingchenglidu(xd01)
                xd12_dy, xd12_dx, xd12_ld = xingchenglidu(xd12)
                xd23_dy, xd23_dx, xd23_ld = xingchenglidu(xd23)
                xd34_dy, xd34_dx, xd34_ld = xingchenglidu(xd34)
                xd45_dy, xd45_dx, xd45_ld = xingchenglidu(xd45)
                xds_low = min([_x.low for _x in xds])
                xds_high = max([_x.high for _x in xds ])

                if (
                    (min(xds[-5].high,xds[-3].high,xd.high) > max(xds[-5].low,xds[-3].low,xd.low))
                    and xds[-2].high == xds[-2].end_line.high
                    and xd.low == xd.end_line.low
                    and xd.low > xds[-5].low 
                    and xd.end.done
                    #and line.end.k.date > reference_date
                ):
                    if (
                        xds[-5].high == max(xds[-5].high,xds[-3].high,xd.high)
                        and xd45_ld < xd01_ld
                    ):
                        msg += "模型1，"
                    elif (
                        xds[-3].high == max(xds[-5].high,xds[-3].high,xd.high) 
                        and xd12_dy <= xd01_dy * 2
                        and xd45_dy < xd01_dy
                        and xd45_dy < xd23_dy
                        and xd45_ld < xd01_ld
                    ):
                        msg += "模型2，"
                    else:
                        continue

                    if (xd.end_line.index - xd.start_line.index <= 5) \
                        and xd.low == xd.end_line.end.val :
                        bis = cd.get_bis()[xd.start_line.index:]
                        if xd.end_line.index - xd.start_line.index == 4:
                            bi_4 = bis[3]
                            if bi_4.mmd_exists(["3sell"]) :
                                xc_ld_bc = compare_xingcheng_ld(bis[2],xd.end_line)
                            else :
                                xc_ld_bc = compare_xingcheng_ld(xd.start_line,xd.end_line)
                        else:
                            xc_ld_bc = compare_xingcheng_ld(xd.start_line,xd.end_line)
                        if xc_ld_bc:
                            deas_xd = cd.get_idx()['macd']['dea'][xd.start_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
                            if ((len(deas_xd) > 0) and deas_xd[-1] <= min(deas_xd)): #负数 
                                macds_xd = cd.get_idx()['macd']['hist'][xd.start_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
                                macds_bi = cd.get_idx()['macd']['hist'][xd.end_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
                                macds_bi_last = macds_bi[int(len(macds_bi)/2):]
                                if abs(min(macds_bi_last)) < abs(min(macds_xd)) : #柱子高度不创新高
                                    is_most = abs(min(macds_bi_last)) > abs(min(macds_bi))
                                    if code not in self.codes_info:
                                        self.codes_info[code] = {
                                            "last_xd_end_date": set(),
                                        }
                                    if xd.end.k.date not in self.codes_info[code]['last_xd_end_date']:
                                        delta = cd.get_src_klines()[-1].index - xd.end.k.k_index
                                        if cd.get_frequency() == 'd' and  delta > 3:
                                            continue
                                        self.codes_info[code]['last_xd_end_date'].add(xd.end.k.date)                              
                                        is_ok = True
                                        msg += "线段结束时间：{},检出时间{}\n".format(xd.end.k.date,cd.get_src_klines()[-1].date)
                                        print(msg)
                                    # logging.info(msg)

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
    # hxg.xuangu_by_code('SH.600016')

    # TODO 多进程执行选股，根据自己 cpu 核数来调整
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

    

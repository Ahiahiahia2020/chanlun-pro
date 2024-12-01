#:  -*- coding: utf-8 -*-
import json
import time

from chanlun import zixuan
from chanlun.cl_interface import *
from chanlun.cl_utils import query_cl_chart_config
from chanlun.exchange.exchange_tdx import ExchangeTDX
from chanlun.xuangu import xuangu
from chanlun.trader.online_market_datas import OnlineMarketDatas
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from tqdm.auto import tqdm

"""
沪深A股 选股程序
不要在这个文件进行修改，请 copy 并命名为 其他程序名 进行修改并运行，维护自己写的选股程序
"""

"""
沪深A股 选股程序
不要在这个文件进行修改，请 copy 并命名为 其他程序名 进行修改并运行，维护自己写的选股程序
"""

ex = ExchangeTDX()

"""
运行的周期，根据自己的选股方法，来设置周期参数
"""
frequencys = ["d"]
# frequencys = ['2d', "60m"]
frequencys = ["d","30m"]
"""
这里设置选股缠论计算的参数，要与前台展示的配置一致，不然这里选出的股票符合条件，前台页面有可能看不到
"""
cl_config = query_cl_chart_config("a", "SH.000001")

"""
获取缠论数据对象
"""
mk_datas = OnlineMarketDatas(
    "a", frequencys, ex, cl_config, use_cache=False
)  # 选股无需使用缓存，使用缓存会占用大量内存

"""
直接放入自选组
这个需要确保在 config.py 中有进行配置
"""
zx = zixuan.ZiXuan("a")
# zx_group = "测试选股-" + datetime.datetime.now().strftime("%Y%m%d-%H%M")
# zx_group = "日线形态选股-" + datetime.datetime.now().strftime("%Y%m%d-%H%M")
zx_group = "段内笔背驰-" + datetime.datetime.now().strftime("%Y%m%d-%H%M")
print(zx_group)
# 清空选股自选
zx.clear_zx_stocks(zx_group)
zx.add_zx_group(zx_group)

def xuangu_by_code(code: str):
    try:
        """
        这里使用自己需要的选股条件方法进行判断 ***
        """
        
        # xg_res = xuangu.xg_single_xingcheng(code, mk_datas,datestr="2024-11-27")
        # xg_res = xuangu.xg_high_level_xingtai(code, mk_datas,datestr="2024-11-28")
        
        # xg_res = xuangu.xg_high_level_xingtai_plus(code, mk_datas,datestr="2024-11-28")
        
        xg_res = xuangu.xg_double_xingcheng(code, mk_datas,datestr="2024-11-27")
        # xg_res = xuangu.xg_single_find_3buy_by_zhuanzhe(code, mk_datas)
        if xg_res is not None:
            stocks = ex.stock_info(code)
            tqdm.write(
                "【%s - %s 】 出现机会：%s"
                % (stocks["code"], stocks["name"], xg_res["msg"])
            )
            zx.add_stock(zx_group, stocks["code"], stocks["name"])

        """
        这里也可以在写其他的选股条件，执行多个选股策略；复制以上的并改变选股条件 ***
        """
        # ...
    except Exception as e:
        print("Code : %s Run Exception : %s" % (code, e))


if __name__ == "__main__":
    

    _stime = time.time()
    # 多进程进行选股操作（不能开太多，避免 tdx 服务进行限制）
    with ProcessPoolExecutor(
        max_workers=5, mp_context=get_context("spawn")
    ) as executor:
        """
        运行的股票代码
        """
        codes = ex.all_stocks()
        codes = [
            _s["code"] for _s in codes if _s["code"][0:5] in ["SH.60", "SZ.00", "SZ.30"]
        ]
        # select_group = "测试选股-20241125-2216"
        # codes_info = zx.zx_stocks(select_group)
        # codes = [_s["code"] for _s in codes_info]
        print("运行股票数量：", len(codes))

        bar = tqdm(total=len(codes), desc="选股进度")
        for _r in executor.map(xuangu_by_code, codes):
            bar.update(1)

    zx_groups = zx.get_zx_groups()
    zx_names = [_zx["name"] for _zx in zx.zixuan_list]
    for zx_name in zx_names:
        # if '日线形态' in zx_name:
        if len(zx.zx_stocks(zx_name)) == 0:
            print("删除无用的自选组：%s" % zx_name)
            zx.del_zx_group(zx_name)
    zx_groups = zx.get_zx_groups()
    zx_names = [_zx["name"] for _zx in zx.zixuan_list]
    print(zx_names)
    print("运行时间：%s" % (time.time() - _stime))
    print("Done")

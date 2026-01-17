from typing import List, Union
import numpy as np
import talib as ta
import pandas as pd
from chanlun.backtesting.base import POSITION, Dict, MarketDatas, Operation, Strategy
from chanlun import fun
from chanlun.db import db
class Strategy3FreqTupo(Strategy):
    """
    三周期
    """

    def __init__(
        self, max_loss_rate=None, date_str="2023-07-01"
    ):
        super().__init__()
        self.date_str = date_str
        self.xuangu_date = set()
        self.signal = 0
        self.bottom_price = 0
        self.neck_price = 0
        self.k_delta = 0
        self.info = {}
        # 最大亏损比例
        self.max_loss_rate = 2 if max_loss_rate is None else max_loss_rate
        db.marks_del_all_by_code(market="a", code="SH.000300")

    def open(
        self, code, market_data: MarketDatas, poss: Dict[str, POSITION]
    ) -> List[Operation]:
        """
        开仓监控，返回开仓配置
        """
        opts = []

        if self.signal == 999:
            return opts
        # 中级别已有信号，进入低级别找入场机会
        if self.signal == 1:
            low_cd = market_data.get_cl_data(code, market_data.frequencys[-1])
            klines = low_cd.get_src_klines()
            last_k = klines[-1]
            pre_k = klines[-2]
            kdate = last_k.date
            amounts = np.array([_k.a for _k in klines])
            ma20_amount = ta.MA(amounts, 20)
            self.info['a_by_pre'] = last_k.a / pre_k.a
            self.info['a_by_ma39'] = last_k.a / ma20_amount[-2]
            # 小级别放量突破中级别颈线位，买入做多
            if (
                last_k.c > self.neck_price
                and pre_k.c <= self.neck_price 
                and last_k.a > pre_k.a * 3
                and last_k.a > ma20_amount[-2] * 3
                and (last_k.h - last_k.c) / (last_k.h - pre_k.c) < 0.5
            ):
                #上引线占比
                k_value = (last_k.h - last_k.c) / (last_k.h - pre_k.c)
                self.info["k_value"] = k_value
                loss_price = min(pre_k.l,last_k.l)  - self.stop_atr * 1.5
                self.target_price = self.neck_price + (self.neck_price - self.bottom_price)
                self.target_rate = (self.target_price - last_k.c) / (last_k.c - loss_price)
                self.info["target_rate"] = self.target_rate
                open_pos_rate = self.get_open_pos_rate(self.max_loss_rate, last_k.c, loss_price)
                self.info["open_pos_rate"] = open_pos_rate  # 记录开仓占比
                self.info["open_k_date"] = kdate
                opts.append(
                    Operation(
                        code,
                        "buy",
                        "1buy",
                        loss_price,
                        self.info,
                        f"价格突破{self.neck_price}，做多买入{open_pos_rate}",
                        pos_rate=open_pos_rate,
                        open_uid=f"{code}_{self.neck_date}",
                    )
                )
                db.marks_add(
                        market_data.market,
                        code.replace("SHSE.", "SH.").replace("SZSE.", "SZ."),
                        "",
                        "",
                        fun.datetime_to_int(kdate),
                        "B",
                        f"价格突破{self.neck_price}，做多买入{open_pos_rate}",
                        "earningUp",
                        "red",
                    )
                self.signal = 999
                return opts
        # 只在最开始做高级别选股
        if self.signal == 0:
            # 获取当前k线
            high_cd = market_data.get_cl_data(code, market_data.frequencys[0])
            high_klines = high_cd.get_src_klines()
            # 周线不足22根，跳过
            if len(high_klines) <= 22:
                return opts
            high_last_k = high_klines[-1]
            closes = np.array([_k.c for _k in high_klines])
            ma20 = ta.MA(closes, timeperiod=20)
            # 大级别满足要求
            if  not ((high_last_k.c > ma20[-1]) and (ma20[-1] > ma20[-2]) ):
                return opts

        # 中级别形态识别
        mid_cd = market_data.get_cl_data(code,  market_data.frequencys[1])
        mid_klines = mid_cd.get_src_klines()
        last_k = mid_klines[-1]
        kdate = last_k.date

        # 如果已有中级别形态信号，判断信号是否还有效
        if self.signal == 1:
            # 底线跌破，形态失效
            if last_k.c < self.bottom_price:
                self.signal = 2
                msg = f"{last_k.c}跌破W底{self.bottom_price},形态失效,sig{self.signal}"
                self.signal = 0
                return opts
            
            # 颈线突破，形态结束，需等后续回踩，暂不开发
            # TODO: 待完善回踩逻辑
            elif last_k.c >= self.neck_price:
                self.signal = 5
                msg = f"{last_k.date},{last_k.c}突破颈线{self.neck_price},sig{self.signal}"
                self.signal = 0
                print(msg)

        bis = mid_cd.get_bis()
        reference_date = pd.Timestamp(self.date_str).tz_localize('UTC')
        # print(f"{kdate},{reference_date}")
        if kdate < reference_date:
            return opts
        if len(bis) <= 3:
            return opts
        last_bi = bis[-1]
        if last_bi.type == "up":
            return opts
        if last_bi.end.k.date in self.xuangu_date:
            return opts
        pre_bi = bis[-2]
        prepre_bi = bis[-3]
        if prepre_bi.end.k.date in self.xuangu_date and self.signal == 1:
            self.signal = 3
            msg = f"震荡延续,sig{self.signal}"
            self.signal = 0
            print(msg)
        self.k_delta = last_k.index - last_bi.end.k.klines[-1].index
        amounts = np.array([_k.a for _k in mid_klines])
        ma5_a = ta.MA(amounts, timeperiod=5)
        # W底的下跌笔完成且两个低点价格差不超过1.5%,成交量低于之前5日均值
        # print(f"{kdate},{last_bi.is_done()},{prepre_bi.high > pre_bi.high},w底{round(abs(last_bi.low - pre_bi.low) / pre_bi.low,2)},成交量比{round(last_bi.end.k.a / ma5_a[-1 - self.k_delta],2)},")
        if last_bi.is_done() and prepre_bi.high > pre_bi.high and abs(last_bi.low - pre_bi.low) / pre_bi.low < 0.015 and last_bi.end.k.a < ma5_a[-1 - self.k_delta]:
            print("符合日线形态")
            self.neck_price = last_bi.high
            self.neck_date = last_bi.start.k.date
            self.xuangu_date.add(last_bi.end.k.date)
            self.signal = 1
            self.bottom_price = min(last_bi.low, pre_bi.low)
            self.info["neck_price"] = self.neck_price
            self.info["bottom_price"] = self.bottom_price
            self.stop_atr = Strategy.idx_atr(mid_cd, end_datetime=last_bi.end.k.date)[-1]
            if last_k.c >=  self.neck_price:
                self.signal = 9
                print("当天突破颈线，后续跟踪回踩")
                # TODO: 待完善回踩逻辑
            msg = "股票{};{}颈线位{}于{};笔结束日期:{};检出日期：{};w_price:{};k{},s{};" \
                .format(high_cd.get_code(),mid_cd.get_frequency(),self.neck_price,fun.datetime_to_str(self.neck_date, "%Y-%m-%d"),fun.datetime_to_str(last_bi.end.k.date, "%Y-%m-%d"),\
                    fun.datetime_to_str(kdate, "%Y-%m-%d"),self.bottom_price,self.k_delta,self.signal)
            print(msg)
            self.signal= 1
                
        return opts


    def close(
        self, code, mmd: str, pos: POSITION, market_data: MarketDatas
    ) -> Union[Operation, None, List[Operation]]:
        """
        持仓监控，返回平仓配置
        """
        opts = []
        if pos.balance == 0:
            return None
        self.if_close = False
        low_cd = market_data.get_cl_data(code, market_data.frequencys[-1])
        klines = low_cd.get_src_klines()
        price = klines[-1].c
        kdate = klines[-1].date
        open_k_date = self.info["open_k_date"]  # 开仓当天日期
        open_next_klines = [_k for _k in klines if _k.date > open_k_date]

        # 止盈止损检查
        loss_opt = self.check_loss(mmd, pos, price)
        if loss_opt is not None:
            return loss_opt

        if price >= self.target_price:
            self.signal = 0
            opts.append(
                Operation(
                    code,
                    "sell",
                    "1sell",
                    0,
                    self.info,
                    f"达到目标价{self.target_price}，平仓",
                    pos_rate=pos.now_pos_rate,
                    close_uid=f"{code}_{self.target_price}",
                )
            )
        # 持仓后，第二个5分钟向上线段不突破第一个5分钟向上线段最高点后，5分钟向下笔完成时平仓
        low_xds = low_cd.get_xds()
        last_xd = low_xds[-1]

        for i in range(len(low_xds) - 1,0,-1):
            if low_xds[i].start.k.date <= open_k_date:
                break
        last_xds = low_xds[i:]
        if len(last_xds)< 3 or last_xd.type == "down":
            return opts
        low_bis = low_cd.get_bis()
        last_bi = low_bis[-1]
        if last_xds[-1].high < last_xds[-2].high and last_bi.type == "down" and last_bi.is_done():
            opts.append(
                Operation(
                    code,
                    "sell",
                    "2sell",
                    0,
                    self.info,
                    f"线段{last_xd.end.k.date},笔{last_bi.end.k.date}",
                    pos_rate=pos.now_pos_rate,
                    close_uid=f"5分钟线段二卖",
                )
            )
            
            if not self.if_close:
                db.marks_add(
                market_data.market,
                code.replace("SHSE.", "SH.").replace("SZSE.", "SZ."),
                "",
                "",
                fun.datetime_to_int(kdate),
                "S",
                f"5分钟线段二卖",
                "earningDown",
                "green",
            )
            self.if_close = True
        

        # TODO 收盘最大盈利回调5%，止盈
        if True and len(open_next_klines) > 0:
            nex_k_high = max([_k.h for _k in open_next_klines])
            nex_k_callback_rate = (price - nex_k_high) / nex_k_high * 100
            if nex_k_callback_rate <= -5:
                opts.append(
                    Operation(
                        code,
                        "sell",
                        mmd,
                        msg=f"最高价格 {nex_k_high} 回调 ({nex_k_callback_rate}) -5%，止盈",
                        close_uid="利润回调5%",
                    )
                )
            if nex_k_callback_rate <= -10:
                opts.append(
                    Operation(
                        code,
                        "sell",
                        mmd,
                        msg=f"最高价格 {nex_k_high} 回调 ({nex_k_callback_rate}) -10%，止盈",
                        close_uid="利润回调10%",
                    )
                )
            if nex_k_callback_rate <= -15:
                opts.append(
                    Operation(
                        code,
                        "sell",
                        mmd,
                        msg=f"最高价格 {nex_k_high} 回调 ({nex_k_callback_rate}) -15%，止盈",
                        close_uid="利润回调15%",
                    )
                )
            if nex_k_callback_rate <= -20:
                opts.append(
                    Operation(
                        code,
                        "sell",
                        mmd,
                        msg=f"最高价格 {nex_k_high} 回调 ({nex_k_callback_rate}) -20%，止盈",
                        close_uid="利润回调20%",
                    )
                )
            if nex_k_callback_rate <= -30:
                opts.append(
                    Operation(
                        code,
                        "sell",
                        mmd,
                        msg=f"最高价格 {nex_k_high} 回调 ({nex_k_callback_rate}) -30%，止盈",
                        close_uid="利润回调30%",
                    )
                )
            if nex_k_callback_rate <= -50:
                opts.append(
                    Operation(
                        code,
                        "sell",
                        mmd,
                        msg=f"最高价格 {nex_k_high} 回调 ({nex_k_callback_rate}) -50%，止盈",
                        close_uid="利润回调50%",
                    )
                )

       

        return opts


if __name__ == "__main__":
    from chanlun.backtesting.backtest_klines import BackTestKlines
    from chanlun.cl_utils import query_cl_chart_config

    market = "a"
    freqs = ["w","d", "30m"]
    code = "SZ.000530"
    start_date = "2024-01-01 09:00:00"
    end_date = "2025-12-31 15:30:00"
    cl_config = query_cl_chart_config(market, code)

    btk = BackTestKlines(market, start_date, end_date, freqs, cl_config)
    btk.init(code, freqs[-1])

    STR = Strategy3FreqTupo()

    open_res = STR.open(code, btk, {})
    print(open_res)

    # pos = POSITION(code, '3sell', 'sell', 100, 9000, 1000, 0, None, info={
    #     'open_date': fun.str_to_datetime('2022-06-13 08:00:00')
    # })
    # close_res = STR.close(code, pos.mmd, pos, btk)
    # print(close_res)

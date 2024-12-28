import datetime

from chanlun.exchange.exchange_binance import ExchangeBinance
from chanlun import utils
from chanlun.db import db
from chanlun import zixuan
from chanlun.backtesting.base import Operation, POSITION
from chanlun.backtesting.backtest_trader import BackTestTrader

"""
指定使用 binance 接口
"""


class TraderCurrency(BackTestTrader):
    """
    数字货币交易者
    """

    def __init__(self, name, log=None):
        super().__init__(name=name, mode="real", market="currency", log=log)

        self.ex = ExchangeBinance()

        # 分仓数
        self.poss_max = 5
        # 使用的杠杆倍数
        self.leverage = 20

        self.zx = zixuan.ZiXuan("currency")

    # 做多买入
    def open_buy(self, code, opt: Operation, amount: float = None):
        try:
            positions = self.ex.positions()
            if len(positions) >= self.poss_max:
                utils.send_fs_msg(
                    "currency",
                    "数字货币交易提醒",
                    f"{code} open buy 下单失败，达到最大开仓数量",
                )
                return False
            balance = self.ex.balance()
            open_usdt = balance["free"] / (self.poss_max - len(positions)) * 0.98
            ticks = self.ex.ticks([code])
            amount = (open_usdt / ticks[code].last) * self.leverage
            print(code,amount,self.leverage)
            res = self.ex.order(code, "open_long", amount, {"leverage": self.leverage})
            if res is False:
                utils.send_fs_msg(
                    "currency", "数字货币交易提醒", f"{code} open buy 下单失败"
                )
                return False
            msg = f"开多仓 {code} 价格 {res['price']} 数量 {open_usdt} 原因 {opt.msg}"
            utils.send_fs_msg("currency", "数字货币交易提醒", msg)

            self.zx.add_stock("我的持仓", code, code)

            # 保存订单记录到 数据库 中
            db.order_save(
                "currency",
                code,
                code,
                "open_long",
                res["price"],
                res["amount"],
                opt.msg,
                datetime.datetime.now(),
            )

            return {"price": res["price"], "amount": res["amount"]}
        except Exception as e:
            utils.send_fs_msg(
                "currency", "数字货币交易提醒", f"{code} open buy 异常: {str(e)}"
            )
            return False

    # 做空卖出
    def open_sell(self, code, opt: Operation, amount: float = None):
        try:
            positions = self.ex.positions()
            if len(positions) >= self.poss_max:
                utils.send_fs_msg(
                    "currency",
                    "数字货币交易提醒",
                    f"{code} open sell 下单失败，达到最大开仓数量",
                )
                return False
            balance = self.ex.balance()
            open_usdt = balance["free"] / (self.poss_max - len(positions)) * 0.98

            ticks = self.ex.ticks([code])
            amount = (open_usdt / ticks[code].last) * self.leverage
            res = self.ex.order(code, "open_short", amount, {"leverage": self.leverage})
            if res is False:
                utils.send_fs_msg(
                    "currency", "数字货币交易提醒", f"{code} open sell 下单失败"
                )
                return False
            msg = f"开空仓 {code} 价格 {res['price']} 数量 {open_usdt} 原因 {opt.msg}"
            utils.send_fs_msg("currency", "数字货币交易提醒", msg)
            self.zx.add_stock("我的持仓", code, code)

            # 保存订单记录到 数据库 中
            db.order_save(
                "currency",
                code,
                code,
                "open_short",
                res["price"],
                res["amount"],
                opt.msg,
                datetime.datetime.now(),
            )

            return {"price": res["price"], "amount": res["amount"]}
        except Exception as e:
            utils.send_fs_msg(
                "currency", "数字货币交易提醒", f"{code} open sell 异常: {str(e)}"
            )
            return False

    # 做多平仓
    def close_buy(self, code, pos: POSITION, opt: Operation):
        try:
            hold_position = self.ex.positions(code)
            if len(hold_position) == 0:
                return {"price": pos.price, "amount": pos.amount}
            hold_position = hold_position[0]

            res = self.ex.order(code, "close_long", pos.amount)
            if res is False:
                utils.send_fs_msg("currency", "数字货币交易提醒", f"{code} 下单失败")
                return False
            msg = "平多仓 %s 价格 %s 数量 %s 盈亏 %s (%.2f%%) 原因 %s" % (
                code,
                res["price"],
                res["amount"],
                hold_position["unrealizedPnl"],
                hold_position["percentage"],
                opt.msg,
            )
            utils.send_fs_msg("currency", "数字货币交易提醒", msg)

            self.zx.del_stock("我的持仓", code)

            # 保存订单记录到 数据库 中
            db.order_save(
                "currency",
                code,
                code,
                "close_long",
                res["price"],
                res["amount"],
                opt.msg,
                datetime.datetime.now(),
            )

            return {"price": res["price"], "amount": res["amount"]}
        except Exception as e:
            utils.send_fs_msg(
                "currency", "数字货币交易提醒", f"{code} close buy 异常: {str(e)}"
            )
            return False

    # 做空平仓
    def close_sell(self, code, pos: POSITION, opt: Operation):
        try:
            hold_position = self.ex.positions(code)
            if len(hold_position) == 0:
                return {"price": pos.price, "amount": pos.amount}
            hold_position = hold_position[0]

            res = self.ex.order(code, "close_short", pos.amount)
            if res is False:
                utils.send_fs_msg("currency", "数字货币交易提醒", f"{code} 下单失败")
                return False
            msg = "平空仓 %s 价格 %s 数量 %s 盈亏 %s (%.2f%%) 原因 %s" % (
                code,
                res["price"],
                res["amount"],
                hold_position["unrealizedPnl"],
                hold_position["percentage"],
                opt.msg,
            )
            utils.send_fs_msg("currency", "数字货币交易提醒", msg)

            self.zx.del_stock("我的持仓", code)

            # 保存订单记录到 数据库 中
            db.order_save(
                "currency",
                code,
                code,
                "close_short",
                res["price"],
                res["amount"],
                opt.msg,
                datetime.datetime.now(),
            )

            return {"price": res["price"], "amount": res["amount"]}
        except Exception as e:
            utils.send_fs_msg(
                "currency", "数字货币交易提醒", f"{code} close sell 异常: {str(e)}"
            )
            return False
        
if __name__ == "__main__":
    TR = TraderCurrency("Currency")
    code = "BTC/USDT"
    # opt_buy = Operation(
    #             code=code,
    #             opt="buy",
    #             mmd="",
    #             loss_price=91845,
    #             info={
    #             },
    #             msg="test",
    #         )
    # TR.open_buy(code, opt_buy) ##做多买入

    opt_sell = Operation(
                code=code, opt="sell", mmd="", msg="test——做多平仓"
            )
    
    pos = POSITION(code, "")
    pos.price=92786.5
    pos.amount=0.002
    TR.close_buy(code, pos=pos  ,opt = opt_sell)
    # 测试做空
    # code2 = "DOGE/USDT"
    # opt = Operation(
    #             code=code,
    #             opt="sell",
    #             mmd="",
    #             loss_price=0.033,
    #             info={
    #             },
    #             msg="test",
    #         )
    # TR.open_sell(code, opt) ##做空买入


    # TR.open_sell(code2, opt = opts[0])
    # positions = TR.ex.positions()
    # print(positions)
    # opt_sell = Operation(
    #             code=code2, opt="buy", mmd="", msg="test——做空平仓"
    #         )
    # pos = POSITION(code2, "")
    # pos.price=0.37241
    # pos.amount=45
    # TR.close_sell(code2, pos=pos  ,opt = opt_sell)
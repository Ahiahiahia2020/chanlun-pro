import itertools
import talib
from chanlun.cl_utils import *
from chanlun.cl_interface import Config
from chanlun.backtesting.base import MarketDatas
from chanlun.utils import send_fs_msg_mine
"""
根据缠论数据，选择自己所需要的形态方法集合
"""

direction_types = {"long": ["down"], "short": ["up"]}
mmd_types = {
    "long": ["1buy", "2buy", "3buy", "l2buy", "l3buy"],
    "short": ["1sell", "2sell", "3sell", "l2sell", "l3sell"],
}


def get_opt_types(opt_type: list = []):
    if len(opt_type) == 0:
        opt_type = ["long"]
    opt_direction = list(
        itertools.chain.from_iterable([direction_types[x] for x in opt_type])
    )
    opt_mmd = list(itertools.chain.from_iterable([mmd_types[x] for x in opt_type]))
    return opt_direction, opt_mmd


def xg_single_xd_and_bi_mmd(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    线段和笔都有出现买点
    周期：单周期
    适用市场：沪深A股
    作者：WX
    """
    opt_direction, opt_mmd = get_opt_types(opt_type)

    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(cd.get_xds()) == 0 or len(cd.get_bis()) == 0:
        return None
    xd = cd.get_xds()[-1]
    bi = cd.get_bis()[-1]

    if xd.mmd_exists(opt_mmd, "|") and bi.mmd_exists(opt_mmd, "|"):
        return {
            "code": code,
            "msg": f"线段买点 【{xd.line_mmds('|')}】 笔买点【{bi.line_mmds('|')}】",
        }
    return None


def xg_multiple_xd_bi_mmd(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    选择 高级别线段，低级别笔 都出现买点，或者 高级别线段和高级别笔 都出现 背驰 的条件
    高级别线段买点或背驰，并且次级别笔买点或背驰
    周期：两个周期
    适用市场：沪深A股
    作者：WX
    """
    opt_direction, opt_mmd = get_opt_types(opt_type)

    # 先判断高级别的
    high_data = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(high_data.get_xds()) == 0 or len(high_data.get_bis()) == 0:
        return None
    high_xd = high_data.get_xds()[-1]
    if high_xd.type not in opt_direction or low_bi.type not in opt_direction:
        return None

    # 再判断低级别的
    low_data = mk_datas.get_cl_data(code, mk_datas.frequencys[1])
    if len(low_data.get_xds()) == 0 or len(low_data.get_bis()) == 0:
        return None
    low_bi = low_data.get_bis()[-1]
    if (high_xd.mmd_exists(opt_mmd, "|") or high_xd.bc_exists(["pz", "qs"], "|")) and (
        low_bi.mmd_exists(opt_mmd, "|") or low_bi.bc_exists(["pz", "qs"], "|")
    ):
        return {
            "code": code,
            "msg": f"{high_data.get_frequency()} 线段买点【{high_xd.line_mmds('|')}】背驰【{high_xd.line_bcs('|')}】 {low_data.get_frequency()} 笔买点【{low_bi.line_mmds('|')}】背驰【{low_bi.line_bcs('|')}】",
        }

    return None


def xg_single_xd_bi_zs_zf_5(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    上涨线段的 第一个 笔中枢， 突破 笔中枢， 大涨 5% 以上的股票
    周期：单周期
    适用市场：沪深A股
    作者：Jiang Haoquan
    """
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])

    if len(cd.get_xds()) == 0 or len(cd.get_bi_zss()) == 0:
        return None
    xd = cd.get_xds()[-1]
    bi_zs = cd.get_bi_zss()[-1]
    kline = cd.get_klines()[-1]

    if (
        xd.type == "up"
        and xd.start.index == bi_zs.lines[0].start.index
        and kline.h > bi_zs.zg >= kline.l
        and (kline.c - kline.o) / kline.o > 0.05
    ):
        return {
            "code": cd.get_code(),
            "msg": "线段向上，当前K线突破中枢高点，并且涨幅大于 5% 涨幅",
        }

    return None


def xg_single_xd_bi_23_overlapped(
    code: str, mk_datas: MarketDatas, opt_type: list = []
):
    """
    上涨线段的 第一个 笔中枢， 突破 笔中枢后 23买重叠的股票
    周期：单周期
    适用市场：沪深A股
    作者：Jiang Haoquan
    """
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(cd.get_xds()) == 0 or len(cd.get_bi_zss()) == 0:
        return None
    xd = cd.get_xds()[-1]
    bi_zs = cd.get_bi_zss()[-1]
    bi = cd.get_bis()[-1]
    bi_2 = cd.get_bis()[-2]
    bi_3 = cd.get_bis()[-3]

    overlapped_23_bi = bi.mmd_exists(["2buy"]) and bi.mmd_exists(["3buy"])
    overlapped_23_bi_2 = (
        bi_2.mmd_exists(["2buy"])
        and bi_2.mmd_exists(["3buy"])
        and bi_td(bi, cd) is True
    )
    overlapped_23_bi_3 = (
        bi_3.mmd_exists(["2buy"])
        and bi_3.mmd_exists(["3buy"])
        and bi.mmd_exists(["l3buy"])
    )

    if (
        xd.type == "up"
        and xd.start.index == bi_zs.lines[0].start.index
        and overlapped_23_bi
        or overlapped_23_bi_2
        or overlapped_23_bi_3
    ):
        return {
            "code": cd.get_code(),
            "msg": "线段向上，当前笔突破中枢高点后 2，3 买重叠",
        }

    return None


def xg_single_day_bc_and_up_jincha(
    code: str, mk_datas: MarketDatas, opt_type: list = []
):
    """
    日线级别，倒数第二个向下笔背驰（笔背驰、盘整背驰、趋势背驰），后续macd在水上金叉
    """
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(cd.get_bis()) <= 5 or len(cd.get_xds()) == 0 or len(cd.get_bi_zss()) == 0:
        return None
    xd = cd.get_xds()[-1]
    bis = cd.get_bis()
    bi_zs = cd.get_bi_zss()[-1]
    # 获取所有下跌笔
    down_bis = [bi for bi in bis if bi.type == "down"]
    if len(down_bis) < 2:
        return None
    if xd.type != "down":
        return None

    # 下跌笔不能再创新低
    if down_bis[-1].low < down_bis[-2].low:
        return None

    # 当前黄白线要在零轴上方
    macd_dif = cd.get_idx()["macd"]["dif"][-1]
    macd_dea = cd.get_idx()["macd"]["dea"][-1]
    if macd_dif < 0 or macd_dea < 0:
        return None

    # 倒数第二下跌笔要出背驰
    if down_bis[-2].bc_exists(["pz", "qs"]) is False:
        return None

    # 最后一个中枢 黄白线要上穿零轴
    zs_macd_info = cal_zs_macd_infos(bi_zs, cd)
    if zs_macd_info.dif_up_cross_num == 0 and zs_macd_info.dea_up_cross_num == 0:
        return None

    macd_infos = cal_klines_macd_infos(
        down_bis[-1].start.k.klines[0], cd.get_klines()[-1], cd
    )
    if macd_infos.gold_cross_num > 0:
        return {
            "code": cd.get_code(),
            "msg": f"前down笔背驰 {down_bis[-2].line_bcs()} macd 在零轴之上，后续又出现金叉，可关注",
        }
    return None


def xg_multiple_low_level_12mmd(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    选择 高级别出现背驰or买卖点，并且低级别出现一二类买卖点
    周期：三个周期
    适用市场：沪深A股
    作者：WX
    """
    opt_direction, opt_mmd = get_opt_types(opt_type)

    high_data = mk_datas.get_cl_data(code, mk_datas.frequencys[0])

    if len(high_data.get_bis()) == 0:
        return None
    # 高级别向下，并且有背驰or买卖点
    high_bi = high_data.get_bis()[-1]
    if high_bi.type not in opt_direction:
        return None
    if len(high_bi.line_bcs("|")) == 0 and len(high_bi.line_mmds("|")) == 0:
        return None

    low_data_1 = mk_datas.get_cl_data(code, mk_datas.frequencys[1])
    low_data_2 = mk_datas.get_cl_data(code, mk_datas.frequencys[2])
    if len(low_data_1.get_bis()) == 0 or len(low_data_2.get_bis()) == 0:
        return None

    # 获取高级别底分型后的低级别笔
    start_datetime = high_bi.end.klines[0].date
    low_bis: List[BI] = []
    for _bi in low_data_1.get_bis():
        if _bi.end.k.date > start_datetime:
            low_bis.append(_bi)
    for _bi in low_data_2.get_bis():
        if _bi.end.k.date > start_datetime:
            low_bis.append(_bi)

    # 遍历低级别的笔，找是否有一二类买点
    exists_12_mmd = False
    for _bi in low_bis:
        if _bi.mmd_exists(
            ["1buy", "2buy"] if high_bi.type == "down" else ["1sell", "2sell"], "|"
        ):
            exists_12_mmd = True
            break

    if exists_12_mmd:
        return {
            "code": high_data.get_code(),
            "msg": f"{high_data.get_frequency()} 背驰 {high_bi.line_bcs('|')} 买点 {high_bi.line_mmds('|')} 并且低级别出现12类买卖点",
        }

    return None


def xg_single_bi_1mmd(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    获取笔的一类买卖点
    周期：单周期
    适用市场：沪深A股
    作者：WX
    """
    opt_direction, opt_mmd = get_opt_types(opt_type)

    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(cd.get_bis()) == 0:
        return None
    bi = cd.get_bis()[-1]
    if bi.type not in opt_direction:
        return None
    for _zs_type, _mmds in bi.zs_type_mmds.items():
        for _m in _mmds:
            if _m.name == "1buy" and _m.zs.line_num < 9:
                return {
                    "code": cd.get_code(),
                    "msg": f"{cd.get_frequency()} 出现本级别笔一买",
                }

    return None


def xg_single_bi_2mmd(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    获取笔的二类买卖点
    周期：单周期
    适用市场：沪深A股
    作者：WX
    """
    opt_direction, opt_mmd = get_opt_types(opt_type)
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(cd.get_bis()) == 0:
        return None
    bi = cd.get_bis()[-1]
    if bi.type not in opt_direction:
        return None
    for _zs_type, _mmds in bi.zs_type_mmds.items():
        for _m in _mmds:
            if _m.name == "2buy" and _m.zs.line_num < 9:
                return {
                    "code": cd.get_code(),
                    "msg": f"{cd.get_frequency()} 出现本级别笔二买",
                }

    return None


def xg_single_bi_3mmd(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    获取笔的三类买卖点
    周期：单周期
    适用市场：沪深A股
    作者：WX
    """
    opt_direction, opt_mmd = get_opt_types(opt_type)
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(cd.get_bis()) == 0:
        return None
    bi = cd.get_bis()[-1]
    if bi.type not in opt_direction:
        return None
    for _zs_type, _mmds in bi.zs_type_mmds.items():
        for _m in _mmds:
            if _m.name == "3buy" and _m.zs.line_num < 9:
                return {
                    "code": cd.get_code(),
                    "msg": f"{cd.get_frequency()} 出现本级别笔三买",
                }

    return None


def xg_single_bcmmd_next_di_fx_verif(
    code: str, mk_datas: MarketDatas, opt_type: list = []
):
    """
    笔出现买点或下跌背驰，并且后续出现底分型验证，则提示
    周期：单周期
    适用市场：沪深A股
    作者：WX
    """
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(cd.get_bis()) == 0:
        return None
    bi = last_done_bi(cd)
    if bi.type != "down":
        return None

    for bc in bi.bcs:
        if bc.type in ["pz", "qs"] and bc.zs.line_num <= 9:
            zs_macd_info = cal_zs_macd_infos(bc.zs, cd)
            if zs_macd_info.dif_up_cross_num > 0 or zs_macd_info.dea_up_cross_num > 0:
                end_di_fx = [
                    _fx
                    for _fx in cd.get_fxs()
                    if (_fx.type == "di" and _fx.index > bi.end.index and _fx.done)
                ]
                if len(end_di_fx) == 0:
                    return None
                end_fx = end_di_fx[0]
                if (
                    cd.get_cl_klines()[-1].index - end_fx.k.index <= 3
                    and end_fx.val > bi.end.val
                ):
                    return {
                        "code": cd.get_code(),
                        "msg": f"{cd.get_frequency()} 出现背驰 {bi.line_bcs()}，并且后续出现验证底分型，可关注",
                    }

    return None


def xg_multiple_zs_tupo_low_3buy(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    高级别中枢突破，在低级别有三买
    所谓横有多长竖有多长
    找一个高级别（比如日线）大级别中枢窄幅震荡（大于9笔的中枢），在 macd 零轴上方，低一级别出现三类买点的股票
    周期：双周期
    适用市场：沪深A股
    作者：WX
    """
    high_cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(high_cd.get_bi_zss()) == 0:
        return None
    high_last_bi_zs = high_cd.get_bi_zss()[-1]
    if (
        high_last_bi_zs.done is True
        or high_last_bi_zs.line_num < 9
        or high_last_bi_zs.zf() <= 50
    ):
        return None
    # macd 黄白线要在上方
    high_dif = high_cd.get_idx()["macd"]["dif"][-1]
    high_dea = high_cd.get_idx()["macd"]["dea"][-1]
    if high_dif < 0 or high_dea < 0:
        return None

    # 低级别笔三买
    low_cd = mk_datas.get_cl_data(code, frequency=mk_datas.frequencys[1])
    if len(low_cd.get_bis()) == 0:
        return None

    low_last_bi = low_cd.get_bis()[-1]
    if low_last_bi.mmd_exists(["3buy"]):
        return {
            "code": high_cd.get_code(),
            "msg": f"{high_cd.get_frequency()} 中枢有可能突破，低级别出现三买，进行关注",
        }

    return None


def xg_single_pre_bi_tk_and_3buy(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    在三买点前一笔，有跳空缺口
    说明突破中枢的力度比较大，可以重点关注
    周期：单周期
    使用市场：沪深A股
    作者：WX
    """
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(cd.get_bis()) < 5:
        return None
    pre_bi = cd.get_bis()[-2]
    now_bi = cd.get_bis()[-1]
    # 之前一笔要出现向上跳空缺口
    up_qk_num, _ = bi_qk_num(cd, pre_bi)
    if up_qk_num <= 0:
        return None
    # 出现三类买点，并且前笔的高点大于等于中枢的 gg 点
    for mmd in now_bi.mmds:
        if mmd.name == "3buy" and pre_bi.high >= mmd.zs.gg:
            return {
                "code": cd.get_code(),
                "msg": f"三买前一笔出现 {up_qk_num} 缺口，可重点关注",
            }
    return None


def xg_single_find_3buy_by_1buy(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    找三买点，前提是前面中枢内有一类买卖点
    （不同的中枢配置，筛选的条件会有差异）
    周期：单周期
    使用市场：沪深A股
    作者：WX
    """
    opt_direction, opt_mmd = get_opt_types(opt_type)

    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(cd.get_bis()) <= 5:
        return None

    if len(cd.get_bi_zss()) < 2:
        return None

    # 前面有一买有以下几种情况
    # 三买出现在一个大的中枢上方，在中枢内部有一买 （标准中枢情况会出现）
    # 在三买中枢与前一个中枢之间，有个一买（段内中枢有可能出现）
    # ......

    bi = cd.get_bis()[-1]
    if bi.type not in opt_direction:
        return None
    for _zs_type, _mmds in bi.zs_type_mmds.items():
        for _m in _mmds:
            if _m.name not in ["3buy", "3sell"]:
                continue
            for _l in _m.zs.lines:
                if _l.mmd_exists(
                    ["1buy"] if bi.type == "down" else ["1sell"], _zs_type
                ):
                    return {
                        "code": cd.get_code(),
                        "msg": f"出现三买，并且之前有出现一买",
                    }
    return None


def xg_single_find_3buy_by_zhuanzhe(
    code: str, mk_datas: MarketDatas, opt_type: list = []
):
    """
    找三买点，之前段内要有是一个下跌趋势，后续下跌趋势结束，出现转折中枢的三买
    （缠论的笔中枢配置要是段内中枢）
    周期：单周期
    使用市场：沪深A股
    作者：WX
    """
    opt_direction, opt_mmd = get_opt_types(opt_type)
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if (
        len(cd.get_bis()) <= 5
        or len(cd.get_xds()) < 2
        or len(cd.get_bi_zss(Config.ZS_TYPE_DN.value)) < 3
    ):
        return None
    # 在三买中枢之前的两个中枢，要是趋势下跌
    bi = cd.get_bis()[-1]
    if bi.type not in opt_direction:
        return None
    if bi.mmd_exists(["3buy"] if bi.type == "down" else ["3sell"], "|") is False:
        return None
    dn_zss = cd.get_bi_zss(Config.ZS_TYPE_DN.value)
    if (
        cd.zss_is_qs(dn_zss[-2], dn_zss[-1]) == "down"
        or cd.zss_is_qs(dn_zss[-3], dn_zss[-2]) == "down"
    ):
        return {"code": cd.get_code(), "msg": "出现三买，并且之前有下跌趋势"}
    return None


def xg_single_ma_250(code: str, mk_datas: MarketDatas, opt_type: list = []):
    """
    找最新价格在 ma 250 线的上下
    周期：单周期
    使用市场：沪深A股
    作者：WX
    """
    opt_direction, opt_mmd = get_opt_types(opt_type)
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    closes = np.array([_k.c for _k in cd.get_src_klines()])
    ma250 = talib.MA(closes, timeperiod=250)
    close = cd.get_src_klines()[-1].c
    if "up" in opt_direction and close > ma250[-1]:
        return {"code": cd.get_code(), "msg": "最新价格高于250日均线"}
    if "down" in opt_direction and close < ma250[-1]:
        return {"code": cd.get_code(), "msg": "最新价格低于250日均线"}
    return None


def xg_single_bi_1buy_next_l3buy_mmd(
    code: str, mk_datas: MarketDatas, opt_type: list = []
):
    """
    笔1buy后的中枢[类三买/类二买]
    周期：单周期
    适用市场：沪深A股
    作者：WX
    """
    opt_direction, opt_mmd = get_opt_types(opt_type)

    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    if len(cd.get_bis()) == 0:
        return None
    bi = cd.get_bis()[-1]

    if bi.type == "up":  # 笔向上，跳过
        return None

    # 找寻前面的一买笔
    bi_by_1buy = None
    for _bi in cd.get_bis()[::-1]:
        if _bi.mmd_exists(["1buy"], "|"):
            bi_by_1buy = _bi
            break

    if bi_by_1buy is None:  # 没有找到有一买
        return None

    # 一买后的笔创建一个中枢，如果没有中枢或多余1个中枢都是不符合条件的
    zs_lines = cd.get_bis()[bi_by_1buy.index + 1 :]
    # 一买后续有大于9笔，那就不找了
    if len(zs_lines) > 9:
        return None
    zs = cd.create_dn_zs("bi", zs_lines)
    if len(zs) != 1:
        return None

    zs = zs[0]
    if bi.index not in [_l.index for _l in zs.lines]:  # 当前笔不在创建的中枢内
        return None

    # 过滤中枢的起始笔不是一买后的第一个笔
    if zs.lines[0].index != zs_lines[0].index:
        return None

    # 中枢线段的最低点
    zs_min_price = min([_l.low for _l in zs.lines[1:]])

    zss_by_1buy = []  # 一买的中枢，根据配置的不用，可能会有多个
    for _zs_type, _mmds in bi_by_1buy.zs_type_mmds.items():
        for _m in _mmds:
            if _m.name == "1buy":
                zss_by_1buy.append(_m.zs)
    for _zs_1buy in zss_by_1buy:
        # 一买后续中枢低点不能低于一买中枢的中心
        _zs_1buy_mid_price = _zs_1buy.zg - (_zs_1buy.zg - _zs_1buy.zd) / 2
        if zs_min_price > _zs_1buy_mid_price:
            return {
                "code": cd.get_code(),
                "msg": f"一买后形成中枢，且中枢低点 {zs_min_price} 高于 一买中枢的中心 {_zs_1buy_mid_price}",
            }

    return None





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

def xg_single_xingcheng(code: str, mk_datas: MarketDatas, datestr: str = '2024-11-27'):
    import logging
    from typing import List
    logging.basicConfig(filename='xg_single_xingcheng.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    """
    找行程力度背驰的股票
    逻辑:
         0、要有至少5段重叠
         0.1、 到最后一个向下段之前，前面一共要有5段，如果包括最新的向上段，那么一共要有6段
         0.2、 最后一个向下段，区间既不是新高也不是新低
         0.3、 第一段起点要求为近期最高点
         1、最后这一段不创新低
         2、找股票已经存在的最后2个线段,(确保一上一下)
         3、获取向下线段
         4、线段内不能超过5笔
         5、判断段内是否在第四笔上方出现笔三卖
         5.1、如果有笔3S，判断段内第三笔与最后一笔是否行程背驰
         5.2、如果没有笔3S，判断线段内第一笔和最后一笔行程是否背驰
         6、判断黄线最低点出现在线段结束
         7、判断MACD柱子的最高点不是出现在线段最后一笔的后二分之一内
         8、判断线段结束日期大于2024-09-01
         9、判断线段最后一笔末端要创新低
         99、都满足则选出该股票加入自选
    周期：单周期
    使用市场:沪深A股
    作者:ZRY
    """
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[1])
    xds = cd.get_xds()
    bis = cd.get_bis()
    reference_date = pd.Timestamp(datestr).tz_localize('UTC')
    msg = "股票代码：{}，选股周期{},".format(cd.get_code(),cd.get_frequency())
    xc_ld_bc = False
    if (xds[-1].type == 'down' and len(xds) >= 5):
        xds = xds[-5:]
    elif (xds[-1].type == 'up' and len(xds) >=6):
        xds = xds[-6:-1]
    else :
        return None
    xd = xds[-1]
    xd1 = xds[0]
    xd2 = xds[2]
    
    xds_low = min([_x.low for _x in xds])
    xds_high = max([_x.high for _x in xds ])
    if (xd1.high == xds_high) \
        and (xd2.high < xds_high) \
        and ((xd.low > xds_low ) and (xd.high < xds_high)) \
        and (xd.end_line.index - xd.start_line.index <=5) \
        and xd.end_line.low == xd.end_line.end.val \
        and (reference_date <= xd.end_line.end.k.date):
        if xd.end_line.index - xd.start_line.index == 4:
            bi_4 = bis[xd.start_line.index + 3]
            if bi_4.mmd_exists(["3sell"]) :
                print('{}段内第四笔三卖'.format(cd.get_code()))
                msg += "段内笔三卖，"
                xc_ld_bc = compare_xingcheng_ld(bis[xd.start_line.index + 2],xd.end_line)
            else :
                xc_ld_bc = compare_xingcheng_ld(xd.start_line,xd.end_line)
        else:
            xc_ld_bc = compare_xingcheng_ld(xd.start_line,xd.end_line)
        if xc_ld_bc:
            msg += "段内笔行程背驰,线段结束时间：{}".format(xd.end.k.date)
            deas_xd = cd.get_idx()['macd']['dea'][xd.start_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
            if ((len(deas_xd) > 0) and deas_xd[-1] <= min(deas_xd)): #负数 
                msg += ",线段结束时def值新低：{:.2f}".format(deas_xd[-1])
                macds_xd = cd.get_idx()['macd']['hist'][xd.start_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
                macds_bi = cd.get_idx()['macd']['hist'][xd.end_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
                macds_bi_last = macds_bi[int(len(macds_bi)/2):]
                if len(macds_bi_last) and abs(min(macds_bi_last)) < abs(min(macds_xd)): #柱子高度不创新高
                    msg += ",线段结束MACD柱子高度不创新高"
                    logging.info(msg)
                    return {"code": cd.get_code(), "msg": msg, }
    return None

def xg_single_xingcheng_0304(code: str, mk_datas: MarketDatas, datestr: str = '2024-11-27'):
    import logging
    from typing import List
    logging.basicConfig(filename='xg_single_xingcheng.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    """
    找行程力度背驰的股票
    逻辑:
         0、要有至少5段重叠
         0.1、 到最后一个向下段之前,前面一共要有5段,如果包括最新的向上段,那么一共要有6段
         0.2、 最后一个向下段，区间既不是新高也不是新低
         0.3、 第一段起点要求为近期最高点
         1、最后这一段不创新低
         2、找股票已经存在的最后2个线段,(确保一上一下)
         3、获取向下线段
         4、线段内不能超过5笔
         5、判断段内是否在第四笔上方出现笔三卖
         5.1、如果有笔3S,判断段内第三笔与最后一笔是否行程背驰
         5.2、如果没有笔3S,判断线段内第一笔和最后一笔行程是否背驰
         6、判断黄线最低点出现在线段结束
         7、判断MACD柱子的最高点不是出现在线段最后一笔的后二分之一内
         8、判断线段结束日期大于指定日期
         9、判断线段最后一笔末端要创新低
         2025-3-4:新增 
            向下线段起点从0开始0-1,1-2,2-3,3-4,4-5,4-5
            4可以比2低,0要比2,4都高,
            4-5的斜率小于0-1,
            1-2的行程不超过0-1的2倍,
            4-5的行程同时小于0-1,2-3
         99、都满足则选出该股票加入自选
    周期：单周期
    使用市场:沪深A股
    作者:ZRY
    """
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[-1])
    xds = cd.get_xds()
    bis = cd.get_bis()
    reference_date = pd.Timestamp(datestr).tz_localize('UTC')
    msg = "股票代码：{}，选股周期{},".format(cd.get_code(),cd.get_frequency())
    xc_ld_bc = False
    if (xds[-1].type == 'down' and len(xds) >= 5):
        xds = xds[-5:]
    elif (xds[-1].type == 'up' and len(xds) >=6):
        xds = xds[-6:-1]
    else :
        return None
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
        (xd01.high == xds_high) 
        and (xd12.high < xds_high) 
        and ((xd.low > xds_low ) 
        and (xd.high < xds_high))
        and xd12_dy < xd01_dy * 2
        and xd45_dy < xd01_dy and xd45_dy < xd23_dy
        and xd45_ld < xd01_ld
        and (xd.end_line.index - xd.start_line.index <=5)
        and xd.end_line.low == xd.end_line.end.val
        and (reference_date <= xd.end_line.end.k.date)
    ):
        if xd.end_line.index - xd.start_line.index == 4:
            bi_4 = bis[xd.start_line.index + 3]
            if bi_4.mmd_exists(["3sell"]) :
                print('{}段内第四笔三卖'.format(cd.get_code()))
                msg += "段内笔三卖，"
                xc_ld_bc = compare_xingcheng_ld(bis[xd.start_line.index + 2],xd.end_line)
            else :
                xc_ld_bc = compare_xingcheng_ld(xd.start_line,xd.end_line)
        else:
            xc_ld_bc = compare_xingcheng_ld(xd.start_line,xd.end_line)
        if xc_ld_bc:
            msg += "段内笔行程背驰,线段结束时间：{}".format(xd.end.k.date)
            deas_xd = cd.get_idx()['macd']['dea'][xd.start_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
            if ((len(deas_xd) > 0) and deas_xd[-1] <= min(deas_xd)): #负数 
                msg += ",线段结束时def值新低：{:.2f}".format(deas_xd[-1])
                macds_xd = cd.get_idx()['macd']['hist'][xd.start_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
                macds_bi = cd.get_idx()['macd']['hist'][xd.end_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
                macds_bi_last = macds_bi[int(len(macds_bi)/2):]
                if len(macds_bi_last) and abs(min(macds_bi_last)) < abs(min(macds_xd)): #柱子高度不创新高
                    msg += ",线段结束MACD柱子高度不创新高"
                    logging.info(msg)
                    return {"code": cd.get_code(), "msg": msg, }
    return None

def xg_double_xingcheng(code: str, mk_datas: MarketDatas, datestr: str = '2024-11-27'):
    import logging
    from typing import List
    logging.basicConfig(filename='xg_double_xingcheng.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    """
    找行程力度背驰的股票
    逻辑:
        大周期逻辑：
        至少6段走势 下上下上下（上）
        1、最后一个向下段，不是新低

        小周期逻辑：
         0、要有至少5段重叠
         0.1、 到最后一个向下段之前，前面一共要有5段，如果包括最新的向上段，那么一共要有6段
         0.2、 最后一个向下段，区间既不是新高也不是新低
         0.3、 第一段起点要求为近期最高点
         1、最后这一段不创新低
         2、找股票已经存在的最后2个线段,(确保一上一下)
         3、获取向下线段
         4、线段内不能超过5笔
         5、判断段内是否在第四笔上方出现笔三卖
         5.1、如果有笔3S，判断段内第三笔与最后一笔是否行程背驰
         5.2、如果没有笔3S，判断线段内第一笔和最后一笔行程是否背驰
         6、判断黄线最低点出现在线段结束
         7、判断MACD柱子的最高点不是出现在线段最后一笔的后二分之一内
         8、判断线段结束日期大于指定日期，例如2024-09-01
         9、判断线段最后一笔末端要创新低
         99、都满足则选出该股票加入自选
    周期：双周期
    使用市场:沪深A股
    作者:ZRY
    """
    high_cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    xds = high_cd.get_xds()
    if (xds[-1].type == 'down' and len(xds) >= 5):
        xds = xds[-5:]
    elif (xds[-1].type == 'up' and len(xds) >=6):
        xds = xds[-6:-1]
    else :
        return None
    xd3 = xds[-1]
    xd2 = xds[-3]
    xd1 = xds[-5]
    xds_low = min([_x.low for _x in xds])
    xds_high = max([_x.high for _x in xds ])
    # print(xd1,xd2,xd3)
    if (xd3.low > xds_low) :
        # and (xd3.high > xd2.high) 
        
        msg = "股票代码：{}，大周期{}不创新低,".format(high_cd.get_code(),high_cd.get_frequency())
        low_cd = mk_datas.get_cl_data(code, frequency=mk_datas.frequencys[1])
        xds = low_cd.get_xds()
        bis = low_cd.get_bis()
        reference_date = pd.Timestamp(datestr).tz_localize('UTC')
        msg += "小周期{},".format(low_cd.get_frequency())
        xc_ld_bc = False
        if (xds[-1].type == 'down' and len(xds) >= 5):
            xds = xds[-5:]
        elif (xds[-1].type == 'up' and len(xds) >=6):
            xds = xds[-6:-1]
        else :
            return None
        xd = xds[-1]
        xd1 = xds[0]
        xd2 = xds[2]
        
        xds_low = min([_x.low for _x in xds])
        xds_high = max([_x.high for _x in xds ])
        if (xd1.high == xds_high) \
            and (xd2.high < xds_high) \
            and ((xd.low > xds_low ) and (xd.high < xds_high)) \
            and (xd.end_line.index - xd.start_line.index <=5) \
            and xd.end_line.low == xd.end_line.end.val \
            and (reference_date <= xd.end_line.end.k.date):
            if xd.end_line.index - xd.start_line.index == 4:
                bi_4 = bis[xd.start_line.index + 3]
                if bi_4.mmd_exists(["3sell"]) :
                    print('{}段内第四笔三卖'.format(cd.get_code()))
                    msg += "段内笔三卖，"
                    xc_ld_bc = compare_xingcheng_ld(bis[xd.start_line.index + 2],xd.end_line)
                else :
                    xc_ld_bc = compare_xingcheng_ld(xd.start_line,xd.end_line)
            else:
                xc_ld_bc = compare_xingcheng_ld(xd.start_line,xd.end_line)
            if xc_ld_bc:
                msg += "段内笔行程背驰,线段结束时间：{}".format(xd.end.k.date)
                deas_xd = low_cd.get_idx()['macd']['dea'][xd.start_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
                if ((len(deas_xd) > 0) and deas_xd[-1] <= min(deas_xd)): #负数 
                    msg += ",线段结束时def值新低：{:.2f}".format(deas_xd[-1])
                    macds_xd = low_cd.get_idx()['macd']['hist'][xd.start_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
                    macds_bi = low_cd.get_idx()['macd']['hist'][xd.end_line.start.k.k_index:xd.end_line.end.k.k_index + 1]
                    macds_bi_last = macds_bi[int(len(macds_bi)/2):]
                    if len(macds_bi_last) and abs(min(macds_bi_last)) < abs(min(macds_xd)): #柱子高度不创新高
                        msg += ",线段结束MACD柱子高度不创新高"
                        logging.info(msg)
                        return {"code": low_cd.get_code(), "msg": msg, }
        return None

def xg_high_level_xingtai(code: str, mk_datas: MarketDatas, datestr: str = '2024-11-27'):
    import logging
    from typing import List
    logging.basicConfig(filename='xg_high_level_xingtai.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    """
    找大周期形态好的股票
    逻辑:
        大周期逻辑：
        至少8段走势 上下上下上下上下（上） 从前往后依次命名为xd1,xd2……xd7,xd8
        1、从最后一段 线段下(xd8)往前推,前面至少有8个线段
        2、xd5或xd7创新高
        3、xd7高点不低于xd1和xd3
        4、xd1起点是最低点
        5、xd2或xd4低点是次低点
        6、xd6低点不低于xd2及xd4
        7、xd6终点是xd8终点
        8、xd8低点不低于xd6
        9、线段结束日期大于指定日期,例如2024-11-01
        10、【加分项】xd6的低点不低于xd2,xd3,xd4形成的中枢 中点
        
    周期：单周期
    使用市场:沪深A股
    作者:ZRY
    """
    reference_date = pd.Timestamp(datestr).tz_localize('UTC')
    high_cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    xds = high_cd.get_xds()
    if (xds[-1].type == 'down' and len(xds) >= 8):
        xds = xds[-8:]
    elif (xds[-1].type == 'up' and len(xds) >=9):
        xds = xds[-9:-1]
    else :
        return None
    xd1 = xds[0]
    xd2 = xds[1]
    xd3 = xds[2]
    xd4 = xds[3]
    xd5 = xds[4]
    xd6 = xds[5]
    xd7 = xds[6]
    xd8 = xds[7]
    xds_low = min([_x.low for _x in xds[1:]])
    xds_high = max([_x.high for _x in xds ])
    # print(xd1,xd2,xd3)
    if(
        (xd5.high >= xds_high or xd7.high >= xds_high) and
        xd7.high >= xd1.high and
        xd7.high >= xd3.high and
        xd1.low < xds_low and
        (xd2.low <= xds_low or xd4.low <= xds_low) and
        xd6.low > xd2.low and
        xd6.low > xd4.low and
        xd8.low > xd6.low and
        xd8.end.k.date >= reference_date
    ):
        msg = "股票代码：{}，大周期{}形态好,最后一段截止日期:{}".format(high_cd.get_code(),high_cd.get_frequency(),xd8.end.k.date)
        if(xd6.low > (max(xd2.low,xd4.low) + 1/2 * (min(xd1.high,xd3.high) - max(xd2.low,xd4.low)))):
            msg += "低点位于之前中枢上半区以上，更好!"
        logging.info(msg)
        return {"code": high_cd.get_code(), "msg": msg, }
    return None

def xg_high_level_xingtai_plus(code: str, mk_datas: MarketDatas, datestr: str = '2024-11-27'):
    import logging
    from typing import List
    logging.basicConfig(filename='xg_high_level_xingtai.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    """
    找大周期形态好的股票
    逻辑:
        大周期逻辑：
        至少8段走势 上下上下上下上下（上） 从前往后依次命名为xd1,xd2……xd7,xd8
        1、从最后一段 线段下(xd8)往前推,前面至少有8个线段
        2、xd5或xd7创新高
        3、xd7高点不低于xd1和xd3
        4、xd1起点是最低点
        5、xd2或xd4低点是次低点
        6、xd6低点不低于xd2及xd4
        7、xd6终点是xd8终点
        8、xd8低点不低于xd6
        9、线段结束日期大于指定日期,例如2024-11-01
        10、【加分项】xd6的低点不低于xd2,xd3,xd4形成的中枢 中点
        
    周期：单周期
    使用市场:沪深A股
    作者:ZRY
    """
    reference_date = pd.Timestamp(datestr).tz_localize('UTC')
    high_cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    xds = high_cd.get_xds()
    if (xds[-1].type == 'down' and len(xds) >= 8):
        xds = xds[-8:]
    elif (xds[-1].type == 'up' and len(xds) >=9):
        xds = xds[-9:-1]
    else :
        return None
    xd1 = xds[0]
    xd2 = xds[1]
    xd3 = xds[2]
    xd4 = xds[3]
    xd5 = xds[4]
    xd6 = xds[5]
    xd7 = xds[6]
    xd8 = xds[7]
    xds_low = min([_x.low for _x in xds[1:]])
    xds_high = max([_x.high for _x in xds ])
    # print(xd1,xd2,xd3)
    if(
        (xd5.high >= xds_high or xd7.high >= xds_high) and
        xd7.high >= xd1.high and
        xd7.high >= xd3.high and
        xd1.low < xds_low and
        (xd2.low <= xds_low or xd4.low <= xds_low) and
        xd6.low > xd2.low and
        xd6.low > xd4.low and
        xd8.low > xd6.low and
        xd8.end.k.date >= reference_date and
        xd6.low > (max(xd2.low,xd4.low) + 1/2 * (min(xd1.high,xd3.high) - max(xd2.low,xd4.low)))
    ):
        msg = "股票代码：{}，大周期{}形态好,重心上移，最后一段截止日期:{}".format(high_cd.get_code(),high_cd.get_frequency(),xd8.end.k.date)
        logging.info(msg)
        return {"code": high_cd.get_code(), "msg": msg, }
    return None

def xg_single_ma_5_5k(code: str, mk_datas: MarketDatas, datestr: str = '2024-11-27'):
    """
    358选股方法,第二版优化，周线使用
    1、最后一个笔,要求是上升笔,(说明站上5均线，且还未形成下降笔)
    2、上升笔结束到最后一个交易周期,中间一共4根k线（说明上升笔后未创新高，数5根k线）
    3、整个笔的涨幅,要求控制在50%-60%


    #第一版
    1、 收盘站上ma5日线纳入观察
    2、 等不创新高后,数4根k线
    3、 第5根k线开盘买入
    4、 止损第4根k线最低点
    5、 止盈 跌破3日均线
    周期：单周期,默认周线
    使用市场:沪深A股
    作者：缠门缠哥
    """
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    closes = np.array([_k.c for _k in cd.get_src_klines()])
    ma5 = talib.MA(closes, timeperiod=5)
    # ma3 = talib.MA(closes, timeperiod=3)
    bi = cd.get_bis()[-1]
    if (bi.type == "up" 
        and (bi.end.k.c > ma5[bi.end.k.k_index])
        and ((bi.high - bi.low) <= 0.6 * bi.low) 
        and ((bi.high - bi.low) >= 0.5 * bi.low)
        and (cd.get_src_klines()[-1].date - bi.end.k.date == datetime.timedelta(weeks=4))
        ):
            msg = "股票代码：{},符合选股条件".format(cd.get_code())
            return {"code": cd.get_code(), "msg":msg}
    return None

def xg_single_ma_5_8k(code: str, mk_datas: MarketDatas, datestr: str = '2024-11-27'):
    """
    358选股-8k方法，周线使用
    1、获取最后一个上升笔,8k可能已经有下降笔，那就找倒数第二笔
    2、上升笔结束到最后一个交易周期,中间一共7根k线（说明上升笔后未创新高，数8根k线）
    3、整个笔的涨幅,要求控制在50%-60%
    周期：单周期,默认周线
    使用市场:沪深A股
    作者：缠门缠哥
    """
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    closes = np.array([_k.c for _k in cd.get_src_klines()])
    ma5 = talib.MA(closes, timeperiod=5)
    # ma3 = talib.MA(closes, timeperiod=3)
    bi = cd.get_bis()[-1]
    if (bi.type != "up"):
        bi = cd.get_bis()[-2]
    if ((bi.end.k.c > ma5[bi.end.k.k_index])
    # and ((bi.high - bi.low) <= 0.6 * bi.low) 
    # and ((bi.high - bi.low) >= 0.5 * bi.low)
    and (cd.get_src_klines()[-1].date - bi.end.k.date == datetime.timedelta(weeks=7))
    ):
        msg = "股票代码：{},符合选股条件".format(cd.get_code())
        return {"code": cd.get_code(), "msg":msg}
    return None

def xg_double_xingtai_dnbbc(code: str, mk_datas: MarketDatas, datestr: str = '2025-02-14'):
    import logging
    from typing import List
    logging.basicConfig(filename='xg_double_xingtai_dnbbc.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    reference_date = pd.Timestamp(datestr).tz_localize('UTC')
    cd = mk_datas.get_cl_data(code, mk_datas.frequencys[0])
    all_lines = cd.get_xds()
    msgs = ""
    for i in range(4,len(all_lines)):
        # print("loop:%d"%i)
        lines = all_lines[:i]
        line = lines[-1]
        kdate = cd.get_src_klines()[-1].date
        # kdate = line.end.k.date
        #自定义增加段内笔背驰形成一买点
        #判断是线段类型,不是笔也不是走势段
        """
        判断行程力度背驰逻辑:
         4、线段内不能超过5笔
         5、判断段内是否在第四笔上方出现笔三卖
         5.1、如果有笔3S，判断段内第三笔与最后一笔是否行程背驰
         5.2、如果没有笔3S，判断线段内第一笔和最后一笔行程是否背驰
         6、判断黄线最低点出现在线段结束
         7、判断MACD柱子的最高点不是出现在线段最后一笔的后二分之一内
         9、判断线段最后一笔末端要创新低
        """
        ##extra 增加选股判断打印
        xuangu_flag = False

        if (len(lines) >= 5 
            and line.type == 'down'
            and (min(lines[-5].high,lines[-3].high,line.high) > max(lines[-5].low,lines[-3].low,line.low))
            and lines[-2].high == lines[-2].end_line.high
            and line.low == line.end_line.low
            and line.low > lines[-3].low 
            and line.end.done

        ):
            xuangu_flag = True

        if (line.end_line.index - line.start_line.index <=5) \
            and line.end.k.date >= reference_date \
            and line.low == line.end_line.end.val :
            if line.end_line.index - line.start_line.index == 4:
                bis = cd.get_bis()
                bi_4 = bis[line.start_line.index + 3]
                if bi_4.mmd_exists(["3sell"]) :
                    xc_ld_bc = compare_xingcheng_ld(bis[line.start_line.index + 2],line.end_line)
                else :
                    xc_ld_bc = compare_xingcheng_ld(line.start_line,line.end_line)
            else:
                xc_ld_bc = compare_xingcheng_ld(line.start_line,line.end_line)
            if xc_ld_bc:
                # print("{}周期{}段内笔行程背驰,线段结束时间：{}".format(cd.get_code(),cd.get_frequency(),line.end.k.date))
                deas_xd = cd.get_idx()['macd']['dea'][line.start_line.start.k.k_index:line.end_line.end.k.k_index + 1]
                if ((len(deas_xd) > 0) and deas_xd[-1] <= min(deas_xd)): #负数 
                    # print("线段结束时def值新低：{:.2f}".format(deas_xd[-1]))
                    macds_xd = cd.get_idx()['macd']['hist'][line.start_line.start.k.k_index:line.end_line.end.k.k_index + 1]
                    macds_bi = cd.get_idx()['macd']['hist'][line.end_line.start.k.k_index:line.end_line.end.k.k_index + 1]
                    macds_bi_last = macds_bi[int(len(macds_bi)/2):]
                    if len(macds_bi_last) and abs(min(macds_bi_last)) < abs(min(macds_xd)): #柱子高度不创新高
                        # print("线段结束MACD柱子高度不创新高，形成一买")
                        if xuangu_flag:
                            msg = "{}周期{}形态符合要求且形成一买，线段结束时间：{},检出时间{}\n".format(cd.get_code(),cd.get_frequency(),line.end.k.date,kdate)
                            print(msg)
                            logging.info(msg)
                            msgs += msg
                            send_fs_msg_mine("xuangu","选股：",msg)
    if len(msgs) > 0:
        return {"code": cd.get_code(), "msg": msgs, }
    else :
        return None

def interact():
    """执行后进入repl模式"""
    import code
    code.InteractiveConsole(locals=globals()).interact()
    
if __name__ == "__main__":
    from chanlun.exchange.exchange_tdx import ExchangeTDX
    from chanlun.cl_utils import query_cl_chart_config
    from chanlun.exchange.exchange import *
    from chanlun.trader.online_market_datas import OnlineMarketDatas

    market = "a"
    # code = "SH.601991"
    # code = "SZ.300926"
    # code = "SZ.301099"
    code = "SH.601333"
    # code = "SH.603818"
    code = "SZ.300044"
    
    frequencys = ['d']

    # frequencys = ['2d', '60m']
    ex = ExchangeTDX()
    cl_config = query_cl_chart_config(market, code)


    """
    获取缠论数据对象
    """
    mk_datas = OnlineMarketDatas(
        "a", frequencys, ex, cl_config, use_cache=False
    )  # 选股无需使用缓存，使用缓存会占用大量内存

    # xg_res = xg_single_xingcheng(code, mk_datas)
    # print(xg_res)

    # xg_res2 = xg_double_xingcheng(code, mk_datas)
    # print(xg_res2)
    # xg_res = xg_high_level_xingtai(code, mk_datas, datestr="2024-11-28")
    xg_res = xg_double_xingtai_dnbbc(code, mk_datas)
    print(xg_res)
    # interact()



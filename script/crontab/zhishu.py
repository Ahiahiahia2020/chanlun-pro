from xtquant import xtdata
# coding=utf-8
from xtquant import xtdata
# 获取板块列表
ret_sector_list = xtdata.get_sector_list()
print(f'获取板块目录: {ret_sector_list}')
# 根据板块列表找查询指数索引名称
ret_sector_data = xtdata.get_stock_list_in_sector('沪深指数')
print(f'获取板块合约: {ret_sector_data}')

#获取板块目录: ['上期所', '上证A股', '上证B股', '上证期权', '上证转债', '中金所', '京市A股', '创业板', '大商所', '沪市ETF', '沪市债券', '沪市基金', '沪市指数', '沪深A股', '沪深B股', '沪深ETF', '沪深京A股', '沪深债券', '沪深基金', '沪深指数', '沪深转债', '深市ETF', '深市债券', '深市基金', '深市指数', '深证A股', '深证B股', '深证期权', '深证转债', '科创板', '科创板CDR', '能源中心', '连续合约', '郑商所', '香港联交所指数', '香港联交所股票']

# '沪深ETF', '沪深基金', '沪深指数'
ret_sector_data = xtdata.get_stock_list_in_sector('沪深指数')
print(f'获取板块合约: {ret_sector_data}')

ret_sector_data = xtdata.get_stock_list_in_sector('沪深ETF')
print(f'获取板块合约: {ret_sector_data}')

ret_sector_data = xtdata.get_stock_list_in_sector('沪深指数')
print(f'获取板块合约: {ret_sector_data}')
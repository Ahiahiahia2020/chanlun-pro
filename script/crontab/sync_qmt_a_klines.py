# 证券账户信息
SECURITY = "GuoJin"
ACCOUNT_TYPE = "STOCK"
USER_NAME = "Ahiahiahia"
USER_ID = "8886930430" # 证券账户ID
USERDATA_MINI_PATH = r'D:\qmt_guojin\userdata_mini' # qmt用户数据路径


## xtdata提供和MiniQmt的交互接口，本质是和MiniQmt建立连接，由MiniQmt处理行情数据请求，再把结果回传返回到python层。使用的行情服务器以及能获取到的行情数据和MiniQmt是一致的，要检查数据或者切换连接时直接操作MiniQmt即可。

## 对于数据获取接口，使用时需要先确保MiniQmt已有所需要的数据，如果不足可以通过补充数据接口补充，再调用数据获取接口获取。

## 对于订阅接口，直接设置数据回调，数据到来时会由回调返回。订阅接收到的数据一般会保存下来，同种数据不需要再单独补充。

# 代码讲解
# 从本地python导入xtquant库，如果出现报错则说明安装失败

from multiprocessing import Process
from xtquant import xtdata
import time


# 将股票列表分成20组
def split_list(lst, n):
    if len(lst) < n:
        n = len(lst)
    chunks = [lst[i::n] for i in range(n)]
    return chunks


def download_stock_group_increment(stock_group):
    for stock_code in stock_group:

        period_list = ['1d','5m']
        for period in period_list:
            # print(period)   
            xtdata.download_history_data(stock_code, period)

if __name__ == '__main__':
    # 获取沪深A股全部股票的代码
    # stock_list = xtdata.get_stock_list_in_sector("沪深A股")
    zhishu_list = xtdata.get_stock_list_in_sector('沪深指数')
    stock_list = zhishu_list

    zhishu_name = []
    for zhishu in zhishu_list:
        zhishu_dic = xtdata.get_instrument_detail(zhishu)
        print(zhishu_dic['InstrumentName'])
        zhishu_name.append(zhishu_dic)

    
    # print(len(stock_list))
    # process_list = []
    # i = 1
    # stock_groups = split_list(stock_list, 20)
    # print(f"总共有{len(stock_groups)}组股票")
    # for stock_group in stock_groups:
    #     print(f"开始下载第{i}组股票，包含{len(stock_group)}只股票")
    #     p = Process(target=download_stock_group_increment, args=(stock_group,))
    #     p.start()
    #     process_list.append(p)
    #     i += 1
        
    # for i, p in enumerate(process_list):
    #     print(f"等待第{i+1}组股票下载完成...")
    #     p.join()
    #     print(f"第{i+1}组股票下载完成")
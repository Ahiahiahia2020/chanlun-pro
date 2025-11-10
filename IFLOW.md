# 项目概述

这是一个基于缠论的市场行情分析工具，名为“缠论市场 WEB 分析工具”。它提供了一系列功能，包括缠论图表展示、行情数据下载、行情监控、回测和实盘交易等。支持多种市场，如沪深股市、港股、美股、期货和数字货币。

项目的核心是使用 Python 实现的缠论计算逻辑，能够对 K 线数据进行处理，识别分型、笔、线段、中枢、走势段、背驰和买卖点等缠论元素。计算采用逐 Bar 方式，支持增量更新，这对于提高回测效率至关重要。

该项目不仅提供 Web 界面进行图表展示和交互，还支持通过 Jupyter Notebook 进行策略研究和回测，以及与掘金量化等平台集成进行回测和仿真。此外，还具备行情监控和消息推送功能。

## 技术栈

*   **核心语言**: Python 3.7+
*   **主要依赖库**:
    *   数据处理: `pandas`, `numpy`
    *   网络请求: `requests`
    *   数据库: `pymysql`, `redis`, `sqlalchemy`
    *   图表绘制: `pyecharts`, `matplotlib`
    *   Web 框架: `Django`, `Flask`
    *   定时任务: `apscheduler`
    *   缠论计算: `TA-Lib` (技术指标), 自研缠论核心逻辑 (`src/chanlun/cl.py`)
    *   其他: `ccxt` (数字货币), `futu-api` (富途), `baostock` (A股), `ib_insync` (盈透), `akshare` (A股/期货/港股等)
*   **部署**: 项目似乎使用 `gevent` 或 `tornado` 作为 Web 服务器。

## 目录结构

*   `src/chanlun`: 核心 Python 代码库。
    *   `backtesting`: 回测和交易相关模块。
    *   `exchange`: 各个交易市场的数据接口封装。
    *   `strategy`: 用户自定义策略存放目录。
    *   `trader`: 实盘交易接口实现。
    *   `tools`: 辅助工具。
    *   `xuangu`: 选股相关功能。
    *   `cl.py`: 缠论核心计算逻辑 (受 PyArmor 保护)。
    *   `cl_utils.py`: 缠论相关的辅助函数。
    *   `base.py`: 基础枚举和类定义。
*   `notebook`: Jupyter Notebook 文件，用于策略开发、回测和数据分析。
*   `script`: 各种脚本，包括数据同步 (`crontab`) 和实盘交易启动脚本 (`trader`)。
*   `web`: Web 前端和后端代码，包括 Demo、Web 分析工具和图表展示。
*   `cookbook`: 项目文档。
*   `joinquant`: 聚宽平台相关的代码和示例。

# 构建、运行与测试

## 环境准备

1.  **Python 版本**: 项目要求 Python 3.7 或更高版本。
2.  **依赖安装**: 使用 `pip install -r requirements.txt` 安装所有依赖。注意 `requirements.txt` 中包含了许多金融数据接口库和 Web 框架。
3.  **TA-Lib 安装**: `TA-Lib` 库可能需要单独安装。项目 `package` 目录下提供了不同 Python 版本的 `.whl` 文件，可以尝试使用 `pip install package/TA_Lib-xxxxx.whl` 进行安装。
4.  **数据库**: 项目使用 MySQL 和 Redis。需要配置好数据库连接信息，通常在 `src/chanlun/config.py` (或 `.demo` 文件) 中。

## 运行方式

项目功能模块化，不同的功能有不同的运行入口：

1.  **Web 服务**:
    *   Web 服务代码位于 `web` 目录下。具体启动方式需要查看 `web` 目录下的配置和启动脚本（如 `script/chanlun_web.config.js` 可能是前端构建配置）。
    *   后端 API 可能是基于 Flask 或 Django 实现的。

2.  **数据同步**:
    *   使用 `script/crontab` 目录下的脚本将行情数据同步到本地 MySQL 数据库。
    *   例如，同步 A 股数据: `python script/crontab/reboot_sync_gm_a_klines.py` (或 `sync_gm_a_klines.py`)。需要配置好相应的交易所 API Key。

3.  **策略回测**:
    *   主要通过 Jupyter Notebook 进行。参考 `notebook` 目录下的回测示例文件，如 `回测_数字货币策略.ipynb`。
    *   回测核心逻辑在 `src/chanlun/backtesting` 中。需要先确保本地数据库中有足够的历史数据。

4.  **实盘交易**:
    *   使用 `script/trader` 目录下的脚本启动实盘交易。
    *   例如，启动 A 股实盘: `python script/trader/reboot_trader_a_stock.py`。需要配置好交易账户信息。

5.  **选股脚本**:
    *   使用 `script/crontab/run_history_xuangu.py` 或其他选股脚本进行本地选股。

## 测试

*   项目文档中没有明确提到单元测试框架或测试命令。
*   回测本身可以看作是对策略逻辑的一种验证。
*   可以通过 Jupyter Notebook (`notebook` 目录) 手动验证缠论计算结果和策略信号。

# 开发约定

## 代码结构与模块

*   **核心缠论逻辑**: 位于 `src/chanlun/cl.py`，该文件经过 PyArmor 加密保护。
*   **策略开发**: 策略应继承 `src/chanlun/backtesting/base.py` 中的 `Strategy` 类，并实现 `open` 和 `close` 方法。建议将自定义策略文件命名为 `my_*.py` 以避免被 Git 跟踪。
*   **实盘交易**: 实盘交易类应继承 `src/chanlun/backtesting/backtest_trader.py` 中的 `Trader` 类，并实现具体的交易方法。
*   **数据接口**: 不同市场的数据获取封装在 `src/chanlun/exchange` 目录下。

## 缠论计算

*   采用逐 Bar 计算方式，支持增量更新。
*   计算结果包括分型、笔、线段、中枢、走势段、背驰、买卖点等。
*   计算配置可以通过 `cl_config` 参数传递，具体选项可参考相关文档。

## 配置文件

*   主要配置文件位于 `src/chanlun/config.py` (或 `.demo` 文件)。需要根据实际情况修改数据库连接、API Key 等信息。

## 文档

*   详细的使用说明和功能介绍位于 `cookbook/docs` 目录下。
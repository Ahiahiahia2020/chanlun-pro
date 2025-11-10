from flask import Flask, request, jsonify
from vp_signal_multi import analyze_and_generate_signals
import pandas as pd

app = Flask(__name__)

@app.route('/api/get_chart_data', methods=['POST'])
def get_chart_data():
    """
    获取K线和成交量分布数据的API接口
    输入：
        start_date: 开始日期时间
        end_date: 结束日期时间
        frequencies: 周期列表
    输出：
        包含K线数据和成交量分布数据的JSON对象
    """
    data = request.json
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    frequencies = data.get('frequencies', ['30m', '10m', '5m'])
    
    # 调用分析函数获取数据
    result = analyze_and_generate_signals(freqs=frequencies, end_date=end_date)
    
    # 获取K线数据
    kline_data = {}
    for freq in frequencies:
        count = freq_map[freq]
        df = get_history(count=count, start_date=start_date, end_date=end_date)
        kline_data[freq] = {
            'dates': df.index.tolist(),
            'open': df['open'].tolist(),
            'close': df['close'].tolist(),
            'high': df['high'].tolist(),
            'low': df['low'].tolist(),
            'volume': df['volume'].tolist()
        }
    
    # 返回数据结构
    return jsonify({
        'kline_data': kline_data,
        'volume_analysis': {
            'poc_list': result['important_signals'],
            'thin_regions': result['important_thin_signals']
        }
    })

if __name__ == '__main__':
    app.run(debug=True)
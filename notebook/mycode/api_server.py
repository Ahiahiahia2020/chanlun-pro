# file: c:\chanlun20141115\chanlun-pro\notebook\mycode\api_server.py
from flask import Flask, request, jsonify
import pandas as pd
from vp_signal_multi import analyze_and_generate_signals
from df_history import get_history

app = Flask(__name__)

@app.route('/api/get_chart_data')
def get_chart_data():
    end_date = request.args.get('end_date')
    freq = request.args.get('frequency', '30m')

    # 获取K线数据
    count = {
        "1m": 30,
        "5m": 120,
        "15m": 480,
        "30m": 960,
        "60m": 1920
    }.get(freq, 30)

    df = get_history(count=count, start_date="2024-2-3 09:30:00", end_date=end_date, freq=freq)
    kline_data = {
        'dates': df.index.tolist(),
        'values': df[['open', 'high', 'low', 'close']].values.tolist()
    }

    # 获取成交量分布数据
    _, _, _ = analyze_volume(df, freq=freq, bin_size=1, sense=10, if_plt=False)
    volume_data = {
        'dates': df.index.tolist(),
        'volume': df['volume'].tolist()
    }

    return jsonify({
        'kline_data': {freq: kline_data},
        'volume_data': {freq: volume_data}
    })

if __name__ == '__main__':
    app.run(debug=True)
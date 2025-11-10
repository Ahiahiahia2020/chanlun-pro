function renderKLineChart(containerId, chartData) {
  const chart = echarts.init(document.getElementById(containerId));
  
  // 准备K线数据格式
  const data = chartData.dates.map((date, i) => [
    date,
    chartData.open[i],
    chartData.close[i],
    chartData.low[i],
    chartData.high[i]
  ]);
  
  const option = {
    title: {
      text: `K线图 (${containerId.replace('kline-', '')})`
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params) => {
        return `${params[0].name}<br>` +
               `O: ${params[1].value[1]} ` +
               `C: ${params[1].value[2]}<br>` +
               `H: ${params[1].value[3]} ` +
               `L: ${params[1].value[4]}`
      }
    },
    grid: {
      bottom: 80
    },
    xAxis: {
      type: 'category',
      data: chartData.dates,
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: false }
    },
    yAxis: {
      scale: true,
      splitLine: { show: false }
    },
    dataZoom: [{
      type: 'inside',
      start: 95,
      end: 100
    }, {
      show: true,
      type: 'slider',
      y: 30,
      height: 20,
      start: 95,
      end: 100
    }],
    series: [{
      name: 'K线',
      type: 'candlestick',
      data: data,
      itemStyle: {
        color: '#ec0000',
        color0: '#26a69a',
        borderColor: null,
        borderColor0: null
      },
      markPoint: {
        data: [{
          name: 'POC信号',
          type: 'min',
          value: -2,
          xAxis: 3,
          yAxis: 10
        }]
      }
    }]
  };
  
  chart.setOption(option);
  return chart;
}
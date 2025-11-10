function renderVolumeChart(containerId, chartData, volumeAnalysis) {
  const chart = echarts.init(document.getElementById(containerId));
  
  // 准备成交量数据
  const volumeData = chartData.dates.map((date, i) => ({
    name: date,
    value: [date, chartData.volume[i]]
  }));
  
  const option = {
    title: {
      text: `成交量分布 (${containerId.replace('volume-', '')})`
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        return `${params[0].name}<br>成交量: ${params[0].value[1]}`
      }
    },
    grid: {
      bottom: 80
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chartData.dates,
      axisLabel: { show: false },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
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
      name: '成交量',
      type: 'bar',
      data: volumeData,
      itemStyle: {
        color: '#26a69a'
      },
      markArea: {
        data: volumeAnalysis.thin_regions
          .filter(signal => signal[2].includes(containerId.replace('volume-', '')))
          .map(signal => [{
            x: signal[0],
            y: 'min'
          }, {
            x: signal[1],
            y: 'max'
          }])
      }
    }]
  };
  
  chart.setOption(option);
  return chart;
}
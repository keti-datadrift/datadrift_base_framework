<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Temperature Comparison</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/6.2.0/d3.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
            margin: 0;
            padding: 0;
        }
        .container {
            width: 100%;
            max-width: 900px;
            margin: 50px auto;
            background-color: #fff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        h1 {
            text-align: center;
            color: #333;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>Temperature Comparison: 2024 vs Historical Average</h1>
    <div id="chart"></div>
</div>

<script>
    // CSV 파일 경로 (같은 서버에 있다고 가정)
    const csvFilePath = 'data/seoul_19071001.csv';
    const targetYear = 2024;

    // CSV 파일 읽기
    d3.csv(csvFilePath).then(function(data) {
        // 날짜 포맷 변경 및 년, 월-일 추출
        data.forEach(function(d) {
            d['날짜'] = new Date(d['날짜']);
            d['연도'] = d['날짜'].getFullYear();
            d['월-일'] = d3.timeFormat('%m-%d')(d['날짜']);
            d['평균기온(℃)'] = +d['평균기온(℃)'];
        });

        // 전체 연도에 대한 월-일별 평균 기온 계산
        const overallAvgTemp = d3.rollup(
            data,
            v => d3.mean(v, d => d['평균기온(℃)']),
            d => d['월-일']
        );

        // 특정 연도의 데이터 필터링
        const targetYearData = data.filter(d => d['연도'] == targetYear);

        // 전체 평균 및 특정 연도의 데이터를 맞춰서 배열로 변환
        const overallTemp = Array.from(overallAvgTemp.values());
        const targetTemp = Array.from(overallAvgTemp.keys()).map(key => {
            const entry = targetYearData.find(d => d['월-일'] === key);
            return entry ? entry['평균기온(℃)'] : null;
        });

        // 차이 계산
        const tempDiff = targetTemp.map((temp, index) => temp - overallTemp[index]);

        // 차트 데이터
        const days = Array.from(overallAvgTemp.keys());

        // Plotly 그래프 생성
        const trace1 = {
            x: days,
            y: overallTemp,
            mode: 'lines+markers',
            name: 'Historical Avg Temp',
            line: {color: 'blue'},
            marker: {size: 4},
            connectgaps: true  // 끊어진 선 연결
        };

        const trace2 = {
            x: days,
            y: targetTemp,
            mode: 'lines+markers',
            name: '2024 Temp',
            line: {color: 'orange'},
            marker: {size: 4},
            connectgaps: true  // 끊어진 선 연결
        };

        const trace3 = {
            x: days,
            y: tempDiff,
            mode: 'lines+markers',
            name: 'Difference (2024 - Avg)',
            line: {color: 'red', dash: 'dash'},
            marker: {size: 4, symbol: 'star'},
            connectgaps: true  // 끊어진 선 연결
        };

        const layout = {
            title: '2024 vs Historical Average Daily Temperature',
            xaxis: {
                title: 'Date (Month-Day)',
                tickvals: days.filter((_, i) => i % 30 === 0), // X축 레이블 간격 조정
            },
            yaxis: {title: 'Temperature (℃)'},
            showlegend: true,
            width: 850,
            height: 500
        };

        Plotly.newPlot('chart', [trace1, trace2, trace3], layout);
    });
</script>

</body>
</html>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Time Series Chart</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
</head>
<body>
    <div>
        <canvas id="timeSeriesChart"></canvas>
    </div>

    <script>
        // Fetch the time series data from the API
        fetch('/api/time-series')
            .then(response => response.json())
            .then(data => {
                const labels = data.map(item => new Date(item.recorded_at));
                const values = data.map(item => item.value);

                // Create the chart
                const ctx = document.getElementById('timeSeriesChart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Value over Time',
                            data: values,
                            fill: true,
                            borderColor: 'rgba(75, 192, 192, 1)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        scales: {
                            x: {
                                type: 'time',  // X 축에 시간 데이터 사용
                                time: {
                                    //unit: 'day',  // 축의 단위를 일 단위로 설정
                                    //unit: 'hour',  // 축의 단위를 시간 단위로 설정
                                    unit: 'minute',  // 축의 단위를 분 단위로 설정
                                    tooltipFormat: 'yyyy-MM-dd HH:mm',  // 툴팁에서 표시될 시간 형식
                                    displayFormats: {
                                        day: 'yyyy-MM-dd'  // X 축에 표시될 시간 형식
                                    }
                                },
                                ticks: {
                                    source: 'auto',  // 자동으로 눈금 생성
                                    autoSkip: false,  // 자동으로 눈금을 건너뛸지 여부
                                    maxTicksLimit: 10  // 눈금의 최대 개수
                                },
                                title: {
                                    display: true,
                                    text: 'Date'  // X 축의 제목
                                }
                            },
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Value'  // Y 축의 제목
                                }
                            }
                        }
                    }
                });
            });
    </script>
</body>
</html>
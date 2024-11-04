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
                            fill: false,
                            borderColor: 'rgba(75, 192, 192, 1)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        scales: {
                            x: {
                                type: 'time',  // Use time scale
                                time: {
                                    unit: 'day'
                                }
                            },
                            y: {
                                beginAtZero: true
                            }
                        }
                    }
                });
            });
    </script>
</body>
</html>
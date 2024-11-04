<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2x2 Plotly Multimodal Data Visualization</title>
    <!-- Plotly.js CDN -->
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

    <style>
        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            font-family: Arial, sans-serif;
        }

        /* 전체 레이아웃을 위한 그리드 */
        .main-container {
            display: grid;
            grid-template-rows: auto auto 1fr;
            grid-gap: 20px;
            padding: 20px;
        }

        /* 헤더 섹션 */
        .header {
            width: 100%;
            text-align: left;
            background-color: rgba(0, 0, 0, 0.0); /* 배경색 투명도 설정 */
            color: white;
            padding: 20px;
            padding-left: 5vw;
            font-size: 20px;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1); /* 그림자 효과 */
        }

        /* 썸네일 갤러리 섹션 */
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            grid-gap: 1px;
            width: 100%;
        }

        .gallery img {
            width: 100px;
            height: 120px;
            object-fit: cover;
            border-radius: 3px;
            transition: transform 0.2s; /* 이미지에 마우스오버 시 확대 효과 */
        }

        .gallery img:hover {
            transform: scale(1.25); /* 마우스오버 시 확대 */
        }

        /* 2x2 차트 섹션 */
        .chart-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            grid-gap: 10px;
        }

        .chart {
            width: 100%;
            height: 400px;
            background-color: lightgray;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 18px;
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- 설명 섹션 -->
        <div class="header">
            <font color='#aaffaa'> 분석 내용 </font> : 차량 번호판 인식을 위한 데이터 드리프트 시뮬레이션 데이터 (다차원 가우시안 분포)<br/>
            <font color='#aaffaa'> 이미지 수 </font> : 10,000개 <br/>
            <font color='#aaffaa'> 설명 </font> : 벡터공간에서 특성이 서로 다른 데이터 클래스 분석 가능 <br/>
        </div>    
        <!-- 2x2 섹션을 위한 div 컨테이너 -->
        <div class='chart-grid'>
            <div id="plot-3d" class='chart'></div>   <!-- 좌상단 3D 그래프 -->
            <div id="plot-x" class='chart'></div>    <!-- 우상단 X축 기준 2D 그래프 -->
            <div id="plot-y" class='chart'></div>    <!-- 좌하단 Y축 기준 2D 그래프 -->
            <div id="plot-z" class='chart'></div>    <!-- 우하단 Z축 기준 2D 그래프 -->
        </div>
    </dif>

    <script>
        // 데이터를 비동기적으로 로드 (multimodal_embedding_vectors.csv는 이미 생성된 파일로 가정)
        fetch('plotly/multimodal_embedding_vectors.csv')
            .then(response => response.text())
            .then(csvData => {
                // CSV 데이터를 행 단위로 파싱
                const rows = csvData.split('\n').slice(1);  // 첫 번째 행은 헤더이므로 제외
                const x = [], y = [], z = [];

                rows.forEach(row => {
                    const [xi, yi, zi] = row.split(',');
                    x.push(parseFloat(xi));
                    y.push(parseFloat(yi));
                    z.push(parseFloat(zi));
                });

                // 좌상단 3D 산포도
                const trace3D = {
                    x: x,
                    y: y,
                    z: z,
                    mode: 'markers',
                    marker: {
                        size: 3,
                        color: z,  // z값에 따라 색상 변경
                        colorscale: 'Viridis',
                        opacity: 0.8
                    },
                    type: 'scatter3d'
                };

                // 우상단 X축 기준 2D 산포도 (Y vs Z)
                const traceX = {
                    x: y,
                    y: z,
                    mode: 'markers',
                    marker: {
                        size: 3,
                        color: z,  // z값에 따라 색상 변경
                        colorscale: 'Viridis',
                        opacity: 0.8
                    },
                    type: 'scatter'
                };

                // 좌하단 Y축 기준 2D 산포도 (X vs Z)
                const traceY = {
                    x: x,
                    y: z,
                    mode: 'markers',
                    marker: {
                        size: 3,
                        color: z,  // z값에 따라 색상 변경
                        colorscale: 'Viridis',
                        opacity: 0.8
                    },
                    type: 'scatter'
                };

                // 우하단 Z축 기준 2D 산포도 (X vs Y)
                const traceZ = {
                    x: x,
                    y: y,
                    mode: 'markers',
                    marker: {
                        size: 3,
                        color: z,  // z값에 따라 색상 변경
                        colorscale: 'Viridis',
                        opacity: 0.8
                    },
                    type: 'scatter'
                };

                // 각 섹션에 차트 렌더링
                Plotly.newPlot('plot-3d', [trace3D], { title: 'Data in Embedding Space' });
                Plotly.newPlot('plot-x', [traceX], { title: 'Y vs Z (X axis projection)', xaxis: {title: 'Y'}, yaxis: {title: 'Z'} });
                Plotly.newPlot('plot-y', [traceY], { title: 'X vs Z (Y axis projection)', xaxis: {title: 'X'}, yaxis: {title: 'Z'} });
                Plotly.newPlot('plot-z', [traceZ], { title: 'X vs Y (Z axis projection)', xaxis: {title: 'X'}, yaxis: {title: 'Y'} });
            })
            .catch(error => console.error('Error loading CSV data:', error));
    </script>
</body>
</html>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2x3 Plotly Multimodal Data Visualization</title>
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
            transition: transform 0.1s; /* 이미지에 마우스오버 시 확대 효과 */
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
            <font color='#aaffaa'> 분석 내용 </font> : 차량 번호판 인식을 위한 한글이미지 학습데이터 분석 <br/>
            <font color='#aaffaa'> 임베딩 모델 </font> : ViT-B/32 <br/>
            <font color='#aaffaa'> 이미지 수 </font> : 18,738개 <br/>
            <font color='#aaffaa'> 차원축소 방법 </font> : UMAP(Uniform Manifold Approximation and Projection), PCA(Principal Component Analysis) <br/>
        </div>

        <!-- 썸네일 갤러리 섹션 -->
        <div class="gallery">
            <img src="images/hangul/01.jpg" alt="number image">
            <img src="images/hangul/02.jpg" alt="number image">
            <img src="images/hangul/03.jpg" alt="number image">
            <img src="images/hangul/04.jpg" alt="number image">
            <img src="images/hangul/05.jpg" alt="number image">
            <img src="images/hangul/06.jpg" alt="number image">
            <img src="images/hangul/07.jpg" alt="number image">
            <img src="images/hangul/08.jpg" alt="number image">
            <img src="images/hangul/09.jpg" alt="number image">
            <img src="images/hangul/10.jpg" alt="number image">
            <img src="images/hangul/11.jpg" alt="number image">
            <img src="images/hangul/12.jpg" alt="number image">
        </div>

       <!-- 2x3 섹션을 위한 div 컨테이너 -->
       <div>
            <img width = 90% src="images/cm3a.png">
            <!--
            <div id="plot-3d" class='chart'></div>
            <div id="plot-x" class='chart'></div>
            <div id="plot-y" class='chart'></div>
            <div id="plot-z" class='chart'></div>
            -->
        </div>
    </div>

    <script>
        // CSV 데이터를 비동기적으로 불러오기 (임베딩 벡터 CSV 파일)
        fetch('plotly/hangul-1st.csv')
            .then(response => response.text())
            .then(csvData => {
                const rows = csvData.split('\n').slice(1); // 첫 번째 행은 헤더이므로 제외
                const x = [], y = [], z = [], labels = [];
                const labelMap = {};  // 레이블을 숫자형으로 매핑하기 위한 객체
                let labelIndex = 0;

                rows.forEach(row => {
                    const values = row.split(',');
                    if (values.length > 512) {
                        x.push(parseFloat(values[0]));  // 첫 번째 벡터 값
                        y.push(parseFloat(values[1]));  // 두 번째 벡터 값
                        z.push(parseFloat(values[2]));  // 세 번째 벡터 값

                        const label = values[512].trim();  // 레이블 값
                        if (!(label in labelMap)) {
                            labelMap[label] = labelIndex++;  // 레이블을 숫자로 매핑
                        }
                        labels.push(labelMap[label]);  // 숫자형 레이블 추가
                    }
                });

                // 좌상단 3D 산포도
                const trace3D = {
                    x: x,
                    y: y,
                    z: z,
                    mode: 'markers',
                    marker: {
                        size: 3,
                        color: labels,  // 숫자형 레이블을 기반으로 색상 구분
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
                        color: labels,  // 숫자형 레이블을 기반으로 색상 구분
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
                        color: labels,  // 숫자형 레이블을 기반으로 색상 구분
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
                        color: labels,  // 숫자형 레이블을 기반으로 색상 구분
                        colorscale: 'Viridis',
                        opacity: 0.8
                    },
                    type: 'scatter'
                };

                // 각 섹션에 차트 렌더링
                //Plotly.newPlot('plot-3d', [trace3D], { title: 'Data in Embedding Space' });
                //Plotly.newPlot('plot-x', [traceX], { title: 'Y vs Z (X axis projection)', xaxis: {title: 'Y'}, yaxis: {title: 'Z'} });
                //Plotly.newPlot('plot-y', [traceY], { title: 'X vs Z (Y axis projection)', xaxis: {title: 'X'}, yaxis: {title: 'Z'} });
                //Plotly.newPlot('plot-z', [traceZ], { title: 'X vs Y (Z axis projection)', xaxis: {title: 'X'}, yaxis: {title: 'Y'} });
            })
            .catch(error => console.error('Error loading CSV data:', error));


        // UMAP 결과를 비동기적으로 불러오기
        fetch('plotly/hangul-1st_umap_projection.csv')
            .then(response => response.text())
            .then(csvData => {
                const rows = csvData.split('\n').slice(1); // 첫 번째 행은 헤더이므로 제외
                const umap_x = [], umap_y = [], umap_labels = [];

                rows.forEach(row => {
                    const values = row.split(',');
                    if (values.length > 2) {
                        umap_x.push(parseFloat(values[0]));  // UMAP1 값
                        umap_y.push(parseFloat(values[1]));  // UMAP2 값
                        umap_labels.push(values[2].trim());  // 레이블 값
                    }
                });

                // 각 고유한 레이블에 고유한 색상 매핑을 수동으로 설정
                const uniqueLabels = [...new Set(umap_labels)];
                    const colorMap = {};
                    uniqueLabels.forEach((label, index) => {
                        colorMap[label] = `hsl(${index * (360 / uniqueLabels.length)}, 70%, 50%)`; // HSL로 고유한 색상 생성
                });

                const colors = umap_labels.map(label => colorMap[label]); // 각 레이블에 맞는 색상 적용

                // UMAP 산포도
                const traceUMAP = {
                    x: umap_x,
                    y: umap_y,
                    mode: 'markers',
                    marker: {
                        size: 3,
                        color: colors,
                        colorscale: 'Viridis',
                        opacity: 0.8
                    },
                    type: 'scatter'
                };

                Plotly.newPlot('plot-umap', [traceUMAP], { title: 'UMAP Projection', xaxis: {title: 'UMAP1'}, yaxis: {title: 'UMAP2'} });
            })
            .catch(error => console.error('Error loading UMAP data:', error));

        // PCA 결과를 비동기적으로 불러오기
        fetch('plotly/hangul-1st_pca_projection.csv')
            .then(response => response.text())
            .then(csvData => {
                const rows = csvData.split('\n').slice(1); // 첫 번째 행은 헤더이므로 제외
                const pca_x = [], pca_y = [], pca_labels = [];

                rows.forEach(row => {
                    const values = row.split(',');
                    if (values.length > 2) {
                        pca_x.push(parseFloat(values[0]));  // PCA1 값
                        pca_y.push(parseFloat(values[1]));  // PCA2 값
                        pca_labels.push(values[2].trim());  // 레이블 값
                    }
                });

                // 각 고유한 레이블에 고유한 색상 매핑을 수동으로 설정
                const uniqueLabels = [...new Set(pca_labels)];
                const colorMap = {};
                uniqueLabels.forEach((label, index) => {
                    colorMap[label] = `hsl(${index * (360 / uniqueLabels.length)}, 70%, 50%)`; // HSL로 고유한 색상 생성
                });

                const colors = pca_labels.map(label => colorMap[label]); // 각 레이블에 맞는 색상 적용

                // PCA 산포도
                const tracePCA = {
                    x: pca_x,
                    y: pca_y,
                    mode: 'markers',
                    marker: {
                        size: 3,
                        color: colors,
                        colorscale: 'Viridis',
                        opacity: 0.8
                    },
                    type: 'scatter'
                };

                Plotly.newPlot('plot-pca', [tracePCA], { title: 'PCA Projection', xaxis: {title: 'PCA1'}, yaxis: {title: 'PCA2'} });
            })
            .catch(error => console.error('Error loading PCA data:', error));
    </script>
</body>
</html>
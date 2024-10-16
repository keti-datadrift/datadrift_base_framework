<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DD 정량목표 진행율 (D3.JS 사용)</title>
    <style>
        .progress-container {
            display: flex;
            align-items: center;
            margin: 10px 0;
        }
        .progress-bar {
            width: 70%;
            background-color: #ddd;
            border-radius: 10px;
            margin: 0 10px;
            position: relative;
            height: 30px;
        }
        .progress-fill {
            height: 100%;
            text-align: center;
            line-height: 30px;
            color: white;
            border-radius: 10px;
        }
        .title {
            width: 15%;
            text-align: right;
        }
        .image-container {
            width: 15%;
            height: 30px;
        }
        .image-container img {
            height: 100%;
        }
    </style>
</head>
<body>

<center>
<h1>DD 정량목표 진행율</h1>
</center>
<div id="chart"></div>

<!-- D3.js 라이브러리 -->
<script src="https://d3js.org/d3.v7.min.js"></script>

<script>
    // config.json에서 스프레드시트 ID를 읽어오는 함수
    function loadConfig() {
        return fetch('config/config.json')
            .then(response => response.json());
    }

    // config.json을 불러와서 Google Sheets 데이터 가져오기
    loadConfig().then(config => {
        const spreadsheetID = config.spreadsheetID; // config.json에서 스프레드시트 ID 가져오기
        const apiUrl = `https://docs.google.com/spreadsheets/d/${spreadsheetID}/gviz/tq?tqx=out:json`;

        // Google Sheets 데이터 가져오기
        fetch(apiUrl)
            .then(response => response.text()) // JSONP 형식으로 데이터가 반환되므로 text()로 가져옵니다.
            .then(dataText => {
                // Google Sheets JSONP 데이터를 파싱
                const jsonData = JSON.parse(dataText.substr(47).slice(0, -2)); // JSONP 형식을 JSON으로 변환
                const rows = jsonData.table.rows;

                // 스프레드시트 데이터를 원하는 형식으로 포맷
                const formattedData = rows.map(row => ({
                    title: row.c[0].v,         // 제목
                    goal: +row.c[1].v,         // 목표값
                    current: +row.c[2].v,      // 현재 달성값
                    imageUrl: row.c[3].v,      // 대표이미지 URL
                    link: row.c[4].v           // URL 링크
                }));

                // 데이터를 시각화하는 함수를 호출
                drawChart(formattedData);
            });
    });

    // 데이터를 바탕으로 진행률 막대와 이미지를 그리는 함수
    function drawChart(data) {
        const container = d3.select("#chart");

        data.forEach(d => {
            // 진행률을 계산하고 100% 이상이면 100%로 제한
            let percentage = (d.current / d.goal) * 100;
            if (percentage > 100) {
                percentage = 100;
            }

            // 각 항목을 포함하는 div 생성
            const row = container.append("div").attr("class", "progress-container");

            // 제목과 링크 추가
            row.append("div")
                .attr("class", "title")
                .append("a")
                .attr("href", d.link)
                .attr("target", "_blank")  // 링크를 새 창에서 열기
                .text(d.title);

            // 진행률 바 추가
            const progressBar = row.append("div").attr("class", "progress-bar");

            // 진행률을 채우는 요소
            progressBar.append("div")
                .attr("class", "progress-fill")
                .style("width", percentage + "%")
                .style("background-color", d.current >= d.goal ? "green" : "steelblue")
                .text(Math.round((d.current / d.goal) * 100) + "%" + " (" + d.current + " / " + d.goal + ")");

            // 대표 이미지 추가
            row.append("div")
                .attr("class", "image-container")
                .append("img")
                .attr("src", d.imageUrl)
                .attr("alt", d.title);
        });
    }
</script>

</body>
</html>
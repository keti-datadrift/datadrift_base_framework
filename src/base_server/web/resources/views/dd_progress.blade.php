<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>D3.js Google Sheets Data</title>
    <style>
        /* 차트 스타일 설정 */
        .bar {
            fill: steelblue;
        }
        .bar-label {
            font: 12px sans-serif;
            fill: black;
        }
    </style>
</head>
<body>

<h1>Google Sheets Data Visualization with D3.js</h1>

<div id="chart"></div>

<!-- D3.js 라이브러리 -->
<script src="https://d3js.org/d3.v7.min.js"></script>

<script>
    // Google Sheets 데이터 가져오기 (스프레드시트 ID로 교체)
    const spreadsheetID = '1TU9Wgmwi27kF0-duVucWHf97_dvcRlamC6XD5-4XmCI'; // 여기에 스프레드시트 ID를 넣으세요
    const apiUrl = `https://docs.google.com/spreadsheets/d/${spreadsheetID}/gviz/tq?tqx=out:json`;

    fetch(apiUrl)
        .then(response => response.text())  // Google API는 JSONP 형태로 데이터를 반환하므로 text()로 가져옵니다.
        .then(dataText => {
            // Google Sheets JSONP 데이터를 정리하는 작업
            const jsonData = JSON.parse(dataText.substr(47).slice(0, -2));  // JSONP 형태를 JSON으로 변환

            const formattedData = jsonData.table.rows.map(row => {
                return {
                    title: row.c[0].v,      // 제목
                    goal: +row.c[1].v,      // 목표값
                    current: +row.c[2].v    // 현재 달성값
                };
            });

            // 데이터를 시각화하는 함수를 호출
            drawChart(formattedData);
        });

    function drawChart(data) {
        const margin = { top: 40, right: 20, bottom: 40, left: 100 };
        const width = 800 - margin.left - margin.right;
        const height = 500 - margin.top - margin.bottom;

        const svg = d3.select("#chart")
            .append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", `translate(${margin.left}, ${margin.top})`);

        // X축 스케일
        const x = d3.scaleLinear()
            .domain([0, d3.max(data, d => Math.max(d.goal, d.current))])
            .range([0, width]);

        // Y축 스케일
        const y = d3.scaleBand()
            .domain(data.map(d => d.title))
            .range([0, height])
            .padding(0.1);

        // 목표값 막대 (회색)
        svg.selectAll(".bar-goal")
            .data(data)
            .enter()
            .append("rect")
            .attr("class", "bar-goal")
            .attr("x", 0)
            .attr("y", d => y(d.title))
            .attr("width", d => x(d.goal))
            .attr("height", y.bandwidth())
            .attr("fill", "#ddd");

        // 현재 달성값 막대 (파란색)
        svg.selectAll(".bar-current")
            .data(data)
            .enter()
            .append("rect")
            .attr("class", "bar-current")
            .attr("x", 0)
            .attr("y", d => y(d.title))
            .attr("width", d => x(d.current))
            .attr("height", y.bandwidth())
            .attr("fill", "steelblue");

        // X축
        svg.append("g")
            .attr("transform", `translate(0, ${height})`)
            .call(d3.axisBottom(x));

        // Y축
        svg.append("g")
            .call(d3.axisLeft(y));
    }
</script>

</body>
</html>
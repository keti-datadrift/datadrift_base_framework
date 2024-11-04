<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Time Series Chart with D3.js</title>
    <style>
        .line {
            fill: none;
            stroke: steelblue;
            stroke-width: 2px;
        }

        .axis-label {
            font-size: 12px;
        }

        .axis path,
        .axis line {
            fill: none;
            shape-rendering: crispEdges;
        }

        .x.axis path {
            display: none;
        }
    </style>
</head>
<body>

<h1>Time Series Chart using D3.js</h1>

<div id="chart"></div>

<!-- D3.js 라이브러리 -->
<script src="https://d3js.org/d3.v7.min.js"></script>

<script>
    // 차트 크기 설정
    const margin = { top: 20, right: 30, bottom: 30, left: 40 };
    const width = 960 - margin.left - margin.right;
    const height = 500 - margin.top - margin.bottom;

    // SVG 설정
    const svg = d3.select("#chart")
        .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    // X축과 Y축 스케일 설정
    const x = d3.scaleTime().range([0, width]);
    const y = d3.scaleLinear().range([height, 0]);

    // 라인 생성 함수
    const line = d3.line()
        .x(d => x(new Date(d.recorded_at)))
        .y(d => y(d.value));

    // 데이터를 가져와서 시각화
    fetch('/api/time-series')
        .then(response => response.json())
        .then(data => {
            // X, Y 도메인 설정
            x.domain(d3.extent(data, d => new Date(d.recorded_at)));
            y.domain([0, d3.max(data, d => d.value)]);

            // X축 생성
            svg.append("g")
                .attr("transform", `translate(0, ${height})`)
                .call(d3.axisBottom(x).ticks(10).tickFormat(d3.timeFormat("%Y-%m-%d")))
                .selectAll("text")
                .attr("transform", "rotate(-45)")
                .style("text-anchor", "end");

            // Y축 생성
            svg.append("g")
                .call(d3.axisLeft(y));

            // 라인 추가
            svg.append("path")
                .datum(data)
                .attr("class", "line")
                .attr("d", line);
        })
        .catch(error => console.error(error));
</script>

</body>
</html>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Donut Chart Visualization</title>
    <style>
        svg {
            font: 10px sans-serif;
        }
        .arc text {
            font: 12px sans-serif;
            text-anchor: middle;
        }
        .arc path {
            stroke: #fff;
        }
    </style>
</head>
<body>

<h1>Goal Achievement Donut Chart</h1>

<div id="chart"></div>

<!-- D3.js 라이브러리 -->
<script src="https://d3js.org/d3.v7.min.js"></script>

<script>
    const data = [
        { title: "Task 1", goal: 100, current: 80 },
        { title: "Task 2", goal: 200, current: 150 },
        { title: "Task 3", goal: 300, current: 250 }
    ];

    function drawDonutChart(data) {
        const width = 300, height = 300, radius = Math.min(width, height) / 2;
        const color = d3.scaleOrdinal(["steelblue", "#ddd"]);

        const arc = d3.arc()
            .outerRadius(radius - 10)
            .innerRadius(radius - 70);

        const pie = d3.pie()
            .sort(null)
            .value(d => d.value);

        const chart = d3.select("#chart").selectAll("svg")
            .data(data)
            .enter()
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", `translate(${width / 2},${height / 2})`);

        chart.each(function(d) {
            const g = d3.select(this);

            const pieData = [
                { value: d.current, type: "current" },
                { value: d.goal - d.current, type: "remaining" }
            ];

            const gArc = g.selectAll(".arc")
                .data(pie(pieData))
                .enter()
                .append("g")
                .attr("class", "arc");

            gArc.append("path")
                .attr("d", arc)
                .style("fill", (d, i) => color(i));

            g.append("text")
                .attr("text-anchor", "middle")
                .attr("dy", "0.35em")
                .text(`${Math.round((d.current / d.goal) * 100)}%`);
        });
    }

    //drawDonutChart(data);
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
            drawDonutChart(formattedData);
        });


</script>

</body>
</html>
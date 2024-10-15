<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bar Chart Race</title>
    <style>
        body {
            font-family: sans-serif;
        }
        .bar {
            fill-opacity: 0.7;
        }
        .bar-label {
            font: 12px sans-serif;
            fill: black;
        }
        .title {
            font-size: 24px;
        }
        .axis-label {
            font-size: 12px;
        }
    </style>
</head>
<body>

<div id="chart"></div>

<!-- D3.js 라이브러리 -->
<script src="https://d3js.org/d3.v7.min.js"></script>

<script>
    // 차트 크기 설정
    const margin = { top: 40, right: 30, bottom: 40, left: 100 };
    const width = 800 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    const svg = d3.select("#chart")
        .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", `translate(${margin.left}, ${margin.top})`);

    const x = d3.scaleLinear().range([0, width]);
    const y = d3.scaleBand().range([0, height]).padding(0.1);

    const color = d3.scaleOrdinal(d3.schemeCategory10);

    let currentIndex = 0;
    let dates = [];
    let groupedData = {};

    // 데이터를 가져와서 차트 렌더링
    fetch('/api/bar-chart-race-data')
        .then(response => response.json())
        .then(data => {
            // 날짜별로 데이터를 그룹화
            groupedData = d3.group(data, d => d.date);
            dates = Array.from(groupedData.keys());

            const maxValue = d3.max(data, d => d.value);
            x.domain([0, maxValue]);

            // 차트 애니메이션 시작
            nextStep();
            setInterval(nextStep, 2000);
        });

    function update(date) {
        const currentData = groupedData.get(date);

        y.domain(currentData.map(d => d.category));

        const bars = svg.selectAll(".bar")
            .data(currentData, d => d.category);

        bars.enter()
            .append("rect")
            .attr("class", "bar")
            .attr("x", 0)
            .attr("y", d => y(d.category))
            .attr("width", 0)  // 초기 너비
            .attr("height", y.bandwidth())
            .attr("fill", d => color(d.category))
            .merge(bars)
            .transition()
            .duration(1000)
            .attr("width", d => x(d.value))
            .attr("y", d => y(d.category));

        bars.exit().remove();

        const labels = svg.selectAll(".bar-label")
            .data(currentData, d => d.category);

        labels.enter()
            .append("text")
            .attr("class", "bar-label")
            .attr("x", 5)
            .attr("y", d => y(d.category) + y.bandwidth() / 2 + 5)
            .merge(labels)
            .transition()
            .duration(1000)
            .attr("x", d => x(d.value) + 5)
            .attr("y", d => y(d.category) + y.bandwidth() / 2 + 5)
            .text(d => `${d.category}: ${d.value}`);

        labels.exit().remove();

        svg.selectAll(".title").remove();
        svg.append("text")
            .attr("class", "title")
            .attr("x", width / 2)
            .attr("y", -10)
            .attr("text-anchor", "middle")
            .text(`Date: ${date}`);
    }

    function nextStep() {
        update(dates[currentIndex]);
        currentIndex = (currentIndex + 1) % dates.length;
    }
</script>

</body>
</html>
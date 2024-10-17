<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analysis Results</title>
    <style>
        body {
            font-family: Arial, sans-serif;
        }

        .result-container {
            width: 100%;
            max-width: 800px;
            margin: 20px auto;
        }

        .result-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
            width: 100%;
        }

        .result-title {
            font-weight: bold;
            margin-bottom: 10px;
        }

        .chart-container {
            width: 100%;
            height: 300px;
        }

        svg {
            width: 100%;
            height: 300px;
        }
    </style>
</head>
<body>

    <div class="result-container">
        @foreach($analyses as $analysis)
            <div class="result-card">
                <div class="result-title">{{ $analysis->title }}</div>
                <div class="result-content">
                    @if($analysis->type == 'text')
                        <p>{{ $analysis->content }}</p>
                    @elseif($analysis->type == 'chart')
                        <div id="chart-{{ $analysis->id }}" class="chart-container"></div>
                    @endif
                </div>
            </div>
        @endforeach
    </div>

    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            @foreach($analyses as $analysis)
                @if($analysis->type == 'chart')
                    createBarChart('#chart-{{ $analysis->id }}', {!! $analysis->content !!});
                @endif
            @endforeach
        });

        // D3.js 차트 생성 함수
        function createBarChart(selector, data) {
            const margin = { top: 10, right: 10, bottom: 30, left: 40 },
                width = 400 - margin.left - margin.right,
                height = 300 - margin.top - margin.bottom;

            const svg = d3.select(selector)
                .append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", `translate(${margin.left},${margin.top})`);

            const x = d3.scaleBand()
                .domain(data.map((d, i) => i))
                .range([0, width])
                .padding(0.1);

            const y = d3.scaleLinear()
                .domain([0, d3.max(data)])
                .range([height, 0]);

            // X-axis
            svg.append("g")
                .attr("transform", `translate(0,${height})`)
                .call(d3.axisBottom(x).tickFormat(i => `Category ${i + 1}`));

            // Y-axis
            svg.append("g")
                .call(d3.axisLeft(y));

            // Bars
            svg.selectAll(".bar")
                .data(data)
                .enter()
                .append("rect")
                .attr("class", "bar")
                .attr("x", (d, i) => x(i))
                .attr("y", d => y(d))
                .attr("width", x.bandwidth())
                .attr("height", d => height - y(d))
                .attr("fill", "steelblue");
        }
    </script>

</body>
</html>
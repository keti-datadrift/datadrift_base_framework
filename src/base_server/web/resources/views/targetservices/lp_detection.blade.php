<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>3x2 Video Dashboard with D3.js</title>

    <!-- 간단한 스타일 적용 -->
    <style>
        body {
            font-family: Arial, sans-serif;
            width: 82%;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 2fr 2fr;
            grid-template-rows: 1fr 1fr;
            gap: 10px;
            width: 100%;
            height: 100%;
            padding: 5px;
            box-sizing: border-box;
        }

        .video-title, .video-container, .graph-container {
            display: flex;
            justify-content: center;
            align-items: center;
            border: 2px solid #2c3e50;
            border-radius: 5px;
            background-color: white;
            padding: 5px;
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        }

        .video-title h2 {
            font-size: 15px;
            color: #2c3e50;
        }

        video {
            width: 100%;
            height: auto;
            object-fit: cover;
        }

        .header {
            width: 100%;
            background-color: #2c3e50;
            color: white;
            padding: 2px;
            text-align: center;
        }
    </style>
</head>
<body>

    <!-- 대시보드 상단 -->
    <div class="header">
        <p>차량 검출기 기계학습 모델 비교</p>
    </div>

    <!-- 비디오 3x2 그리드 -->
    <div class="container">
        <!-- 1행 -->
        <div class="video-title">
            <h2>실험실 테스트</h2>
        </div>
        <div class="video-container">
            <video controls autoplay muted>
                <source src="{{ $videoUrl1 }}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
        <div class="graph-container">
            <svg id="graph1" width="400" height="300"></svg>
        </div>

        <!-- 2행 -->
        <div class="video-title">
            <h2>현장 적용 테스트</h2>
        </div>
        <div class="video-container">
            <video controls autoplay muted>
                <source src="{{ $videoUrl2 }}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
        <div class="graph-container">
            <svg id="graph2" width="400" height="300"></svg>
        </div>
    </div>

    <!-- D3.js를 사용하여 그래프 생성 -->
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        // CSV 데이터 파일을 불러와 그래프 그리기
        d3.csv("{{ asset('data/video_features.csv') }}").then(function(data) {
            // 첫 번째 그래프
            var svg1 = d3.select("#graph1");
            drawGraph(svg1, data, "video1");

            // 두 번째 그래프
            var svg2 = d3.select("#graph2");
            drawGraph(svg2, data, "video2");
        });

        // 그래프 그리기 함수
        function drawGraph(svg, data, videoId) {
            // 비디오 ID에 맞는 데이터 필터링
            var filteredData = data.filter(function(d) { return d.videoId === videoId; });

            var margin = {top: 20, right: 30, bottom: 30, left: 40},
                width = +svg.attr("width") - margin.left - margin.right,
                height = +svg.attr("height") - margin.top - margin.bottom,
                g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");

            var x = d3.scaleBand().rangeRound([0, width]).padding(0.1),
                y = d3.scaleLinear().rangeRound([height, 0]);

            x.domain(filteredData.map(function(d) { return d.feature; }));
            y.domain([0, d3.max(filteredData, function(d) { return +d.value; })]);

            g.append("g")
                .attr("class", "axis axis--x")
                .attr("transform", "translate(0," + height + ")")
                .call(d3.axisBottom(x));

            g.append("g")
                .attr("class", "axis axis--y")
                .call(d3.axisLeft(y).ticks(10))
              .append("text")
                .attr("fill", "#000")
                .attr("y", 6)
                .attr("dy", "0.71em")
                .attr("text-anchor", "end")
                .text("Value");

            g.selectAll(".bar")
              .data(filteredData)
              .enter().append("rect")
                .attr("class", "bar")
                .attr("x", function(d) { return x(d.feature); })
                .attr("y", function(d) { return y(d.value); })
                .attr("width", x.bandwidth())
                .attr("height", function(d) { return height - y(d.value); });
        }
    </script>
</body>
</html>
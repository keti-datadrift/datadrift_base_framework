<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Confusion Matrix Visualization</title>
  <script src="https://d3js.org/d3.v6.min.js"></script>
  <style>
    .background { fill: #eee; }
    .cell { fill: none; pointer-events: all; }
    text.active { font-weight: bold; }
    svg { font-family: sans-serif; }
    .axis-label {
      font-size: 12px;
      font-weight: bold;
    }
    .cell {
      stroke: #ddd;
    }
    .cell rect {
      stroke-width: 1px;
    }
  </style>
</head>
<body>

<svg></svg>

<script>
  var margin = { top: 80, right: 20, bottom: 80, left: 80 },
      width = 500,
      height = 500;

  var x = d3.scaleBand().range([0, width]).padding(0.05),
      y = d3.scaleBand().range([0, height]).padding(0.05),
      color = d3.scaleSequential(d3.interpolateBlues).domain([0, 100]);

  var svg = d3.select("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  // CSV 데이터 로드
  d3.csv("data/cm2.csv").then(function(data) {

    // 실제 클래스와 예측된 클래스의 고유 값 추출
    var actualClasses = Array.from(new Set(data.map(d => d.actual)));
    var predictedClasses = Array.from(new Set(data.map(d => d.predicted)));

    x.domain(predictedClasses);
    y.domain(actualClasses);

    // X축: 예측된 클래스
    svg.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + height + ")")
      .call(d3.axisBottom(x))
      .selectAll("text")
      .attr("class", "axis-label")
      .attr("y", 10)
      .attr("x", 0)
      .attr("dy", ".35em")
      .attr("text-anchor", "middle");

    // Y축: 실제 클래스
    svg.append("g")
      .attr("class", "y axis")
      .call(d3.axisLeft(y))
      .selectAll("text")
      .attr("class", "axis-label")
      .attr("x", -10)
      .attr("y", 0)
      .attr("dy", ".35em")
      .attr("text-anchor", "end");

    // 행렬 데이터 시각화 (각 셀)
    svg.selectAll(".cell")
      .data(data)
      .enter().append("rect")
      .attr("x", function(d) { return x(d.predicted); })
      .attr("y", function(d) { return y(d.actual); })
      .attr("width", x.bandwidth())
      .attr("height", y.bandwidth())
      .style("fill", function(d) { return color(d.count); })
      .attr("class", "cell");

    // 셀의 텍스트 표시 (카운트 값)
    svg.selectAll(".text")
      .data(data)
      .enter().append("text")
      .attr("x", function(d) { return x(d.predicted) + x.bandwidth() / 2; })
      .attr("y", function(d) { return y(d.actual) + y.bandwidth() / 2; })
      .attr("dy", ".35em")
      .attr("text-anchor", "middle")
      .text(function(d) { return d.count; })
      .style("fill", "black");

  }).catch(function(error) {
    console.log("Error loading the data: ", error);
  });

</script>

</body>
</html>

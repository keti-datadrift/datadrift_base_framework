# d3.js를 사용한 confusion matrix 시각화

Confusion Matrix를 기반으로 Accuracy, Recall, F1-Score 등의 성능 지표를 계산하고 이를 자동으로 표시하는 방식은 매우 유용합니다. D3.js로 Confusion Matrix를 시각화한 후, CSV 파일을 읽어와 이러한 성능 지표를 계산하고 페이지에 표시할 수 있도록 구현해 보겠습니다.

1. Confusion Matrix로부터 성능 지표 계산

기본적인 성능 지표를 Confusion Matrix로부터 계산하는 공식을 소개합니다.

	•	Accuracy: 전체 정확도는 올바르게 예측된 샘플의 비율입니다.
￼
	•	Recall (Sensitivity): 실제로 양성인 것 중에 올바르게 예측한 양성의 비율입니다.
￼
	•	F1-Score: Precision과 Recall의 조화 평균입니다.
￼

여기서:

	•	TP: True Positive (예측: Positive, 실제: Positive)
	•	TN: True Negative (예측: Negative, 실제: Negative)
	•	FP: False Positive (예측: Positive, 실제: Negative)
	•	FN: False Negative (예측: Negative, 실제: Positive)

2. D3.js 코드 수정

matrix.csv 파일로부터 데이터를 읽고, 이를 기반으로 성능 지표를 계산한 후 페이지에 자동으로 표시하는 예시 코드를 제공합니다.

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Confusion Matrix with Metrics</title>
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
    .matrix-container {
      display: flex;
      justify-content: center;
      align-items: flex-start;
      gap: 30px;
    }
    .matrix-title {
      text-align: center;
      margin-bottom: 10px;
      font-weight: bold;
    }
    .metrics {
      margin-top: 20px;
      font-family: Arial, sans-serif;
    }
    .metric-label {
      font-weight: bold;
    }
  </style>
</head>
<body>

<div class="matrix-container">
  <div>
    <div class="matrix-title">Confusion Matrix</div>
    <svg id="matrix"></svg>
  </div>
</div>

<div class="metrics">
  <div><span class="metric-label">Accuracy:</span> <span id="accuracy"></span></div>
  <div><span class="metric-label">Recall:</span> <span id="recall"></span></div>
  <div><span class="metric-label">F1-Score:</span> <span id="f1score"></span></div>
</div>

<script>
  var margin = { top: 80, right: 20, bottom: 80, left: 80 },
      width = 300,
      height = 300;

  var x = d3.scaleBand().range([0, width]).padding(0.05),
      y = d3.scaleBand().range([0, height]).padding(0.05),
      color = d3.scaleSequential(d3.interpolateBlues).domain([0, 100]);

  // 성능 지표를 계산하는 함수
  function calculateMetrics(data) {
    let TP = 0, TN = 0, FP = 0, FN = 0;

    data.forEach(d => {
      const actual = +d.actual;
      const predicted = +d.predicted;
      const count = +d.count;

      if (actual === 1 && predicted === 1) TP += count;
      if (actual === 0 && predicted === 0) TN += count;
      if (actual === 0 && predicted === 1) FP += count;
      if (actual === 1 && predicted === 0) FN += count;
    });

    const accuracy = (TP + TN) / (TP + TN + FP + FN);
    const recall = TP / (TP + FN);
    const precision = TP / (TP + FP);
    const f1Score = 2 * (precision * recall) / (precision + recall);

    return {
      accuracy: accuracy.toFixed(2),
      recall: recall.toFixed(2),
      f1Score: f1Score.toFixed(2)
    };
  }

  // Confusion Matrix 그리는 함수
  function drawConfusionMatrix(container, dataFile) {
    var svg = d3.select(container)
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
      .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    // CSV 데이터 로드
    d3.csv(dataFile).then(function(data) {

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

      // 성능 지표 계산 후 HTML에 표시
      const metrics = calculateMetrics(data);
      d3.select("#accuracy").text(metrics.accuracy);
      d3.select("#recall").text(metrics.recall);
      d3.select("#f1score").text(metrics.f1Score);

    }).catch(function(error) {
      console.log("Error loading the data: ", error);
    });
  }

  // Confusion Matrix 및 성능 지표 표시
  drawConfusionMatrix("#matrix", "matrix.csv");

</script>

</body>
</html>

3. CSV 데이터 형식

Confusion Matrix를 위해 필요한 데이터는 예측 클래스와 실제 클래스, 그리고 해당 데이터가 나타난 횟수를 포함합니다.

예시 CSV 데이터 (matrix.csv):

actual,predicted,count
0,0,50
0,1,10
1,0,5
1,1,35

4. 설명

	1.	CSV 데이터 로드: d3.csv()로 Confusion Matrix 데이터를 로드합니다.
	2.	Confusion Matrix 그리기: 기존과 동일하게 Confusion Matrix를 그립니다. rect와 text 요소를 사용하여 각 셀을 표현하고, 해당 셀에 있는 값을 텍스트로 표시합니다.
	3.	성능 지표 계산:
	•	Accuracy: 전체 데이터 중에서 올바르게 예측된 비율을 계산합니다.
	•	**Recall
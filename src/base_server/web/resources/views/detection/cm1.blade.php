<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Compare Confusion Matrices</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    /* Flexbox 설정 */
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
      color: white;
    }

    .matrix {
      width: 400px;
      height: 400px;
    }

    .metrics {
      text-align: center;
      margin-top: 10px;
      color: white;
    }
  </style>
</head>
<body style="background-color: #2d2d2d;">

<div class="matrix-container">
  <div>
    <div class="matrix-title">실험실 성능</div>
    <div id="matrix1" class="matrix"></div>
    <div id="metrics1" class="metrics"></div>
  </div>
  <div>
    <div class="matrix-title">현장 적용 성능</div>
    <div id="matrix2" class="matrix"></div>
    <div id="metrics2" class="metrics"></div>
  </div>
</div>

<script>
  function calculateMetrics(data) {
    let tp = 0, tn = 0, fp = 0, fn = 0;
    
    data.forEach(function(d) {
      if (d.actual === 'A' && d.predicted === 'A') tp = d.count;
      if (d.actual === 'B' && d.predicted === 'B') tn = d.count;
      if (d.actual === 'A' && d.predicted === 'B') fp = d.count;
      if (d.actual === 'B' && d.predicted === 'A') fn = d.count;
    });

    let accuracy = (tp + tn) / (tp + tn + fp + fn);
    let precision = tp / (tp + fp);
    let recall = tp / (tp + fn);
    let f1 = 2 * (precision * recall) / (precision + recall);

    return {
      accuracy: accuracy.toFixed(2),
      precision: precision.toFixed(2),
      recall: recall.toFixed(2),
      f1: f1.toFixed(2)
    };
  }

  function displayMetrics(metrics, container) {
    const metricsHtml = `
      <div>Accuracy: ${metrics.accuracy}</div>
      <div>Precision: ${metrics.precision}</div>
      <div>Recall: ${metrics.recall}</div>
      <div>F1-Score: ${metrics.f1}</div>
    `;
    document.getElementById(container).innerHTML = metricsHtml;
  }

  function drawConfusionMatrix(container, data, metricsContainer) {
    var actual = data.map(d => d.actual);
    var predicted = data.map(d => d.predicted);
    var counts = data.map(d => d.count);

    var uniqueClasses = Array.from(new Set(actual.concat(predicted))).sort();

    // 행렬 데이터를 채우기 위한 배열 초기화
    var matrixData = Array(uniqueClasses.length).fill(0).map(() => Array(uniqueClasses.length).fill(0));

    // Confusion matrix 데이터 채우기
    data.forEach(function(d) {
      var actualIndex = uniqueClasses.indexOf(d.actual);
      var predictedIndex = uniqueClasses.indexOf(d.predicted);
      matrixData[actualIndex][predictedIndex] = d.count;
    });

    var trace = {
      x: uniqueClasses,
      y: uniqueClasses,
      z: matrixData,
      type: 'heatmap',
      colorscale: 'Blues',
      showscale: true
    };

    var layout = {
      title: 'Confusion Matrix',
      xaxis: {
        title: 'Predicted',
        automargin: true
      },
      yaxis: {
        title: 'Actual',
        automargin: true
      },
      annotations: [],
      width: 400,
      height: 400
    };

    // 행렬 안에 값 텍스트 표시
    for (var i = 0; i < uniqueClasses.length; i++) {
      for (var j = 0; j < uniqueClasses.length; j++) {
        var value = matrixData[i][j];
        layout.annotations.push({
          x: uniqueClasses[j],
          y: uniqueClasses[i],
          text: value,
          showarrow: false,
          font: {
            color: 'black'
          }
        });
      }
    }

    Plotly.newPlot(container, [trace], layout);

    // Metrics 계산 및 표시
    var metrics = calculateMetrics(data);
    displayMetrics(metrics, metricsContainer);
  }

  // 샘플 데이터 (실제 CSV 파일을 사용하면 그 데이터를 여기에 넣을 수 있음)
  var data1 = [
    { actual: 'A', predicted: 'A', count: 90 },
    { actual: 'A', predicted: 'B', count: 10 },
    { actual: 'B', predicted: 'A', count: 3 },
    { actual: 'B', predicted: 'B', count: 97 }
  ];

  var data2 = [
    { actual: 'A', predicted: 'A', count: 65 },
    { actual: 'A', predicted: 'B', count: 35 },
    { actual: 'B', predicted: 'A', count: 25 },
    { actual: 'B', predicted: 'B', count: 75 }
  ];

  // 첫 번째 Confusion Matrix
  drawConfusionMatrix('matrix1', data1, 'metrics1');

  // 두 번째 Confusion Matrix
  drawConfusionMatrix('matrix2', data2, 'metrics2');

</script>

</body>
</html>

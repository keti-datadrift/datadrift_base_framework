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
      justify-content: left; /* 행렬을 왼쪽에 정렬 */
      align-items: flex-start; /* 수직 정렬 */
      gap: 30px; /* 두 행렬 사이의 간격 */
    }

    .matrix-title {
      text-align: center;
      margin-bottom: 10px;
      font-weight: bold;
    }

    /* SVG의 크기를 줄여 두 개가 더 가까워지도록 설정 */
    .matrix {
      width: 400px;
      height: 400px;
    }
  </style>
</head>
<body>

<div class="matrix-container">
  <div>
    <div class="matrix-title">참고 모델 성능</div>
    <div id="matrix1" class="matrix"></div>
  </div>
  <div>
    <div class="matrix-title">데이터 드리프트 처리 모델 성능</div>
    <div id="matrix2" class="matrix"></div>
  </div>
</div>

<script>
  function drawConfusionMatrix(container, data) {
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
  }

  // 샘플 데이터 (실제 CSV 파일을 사용하면 그 데이터를 여기에 넣을 수 있음)
  var data1 = [
    { actual: 'A', predicted: 'A', count: 30 },
    { actual: 'A', predicted: 'B', count: 5 },
    { actual: 'B', predicted: 'A', count: 3 },
    { actual: 'B', predicted: 'B', count: 40 }
  ];

  var data2 = [
    { actual: 'A', predicted: 'A', count: 25 },
    { actual: 'A', predicted: 'B', count: 10 },
    { actual: 'B', predicted: 'A', count: 2 },
    { actual: 'B', predicted: 'B', count: 43 }
  ];

  // 첫 번째 Confusion Matrix
  drawConfusionMatrix('matrix1', data1);

  // 두 번째 Confusion Matrix
  drawConfusionMatrix('matrix2', data2);

</script>

</body>
</html>
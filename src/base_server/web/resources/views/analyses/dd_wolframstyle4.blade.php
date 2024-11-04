<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dynamic Analysis</title>
    <meta name="csrf-token" content="{{ csrf_token() }}">
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

    <div id="input-section">
        <input type="text" id="user-input" placeholder="Enter a keyword to analyze...">
        <button onclick="analyzeInput()">Analyze</button>
    </div>

    <div class="result-container" id="result-container">
        <!-- Dynamic analysis results will be displayed here -->
    </div>

    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        function analyzeInput() {
            const input = document.getElementById('user-input').value;

            if (input.trim() === '') {
                alert('Please enter a valid input.');
                return;
            }

            // CSRF 토큰을 가져옵니다.
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

            // AJAX 요청을 사용하여 서버로 키워드 전송
            fetch('/analyses/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': csrfToken  // CSRF 토큰 추가
                },
                body: JSON.stringify({
                    keyword: input
                })
            })
            .then(response => response.json())
            .then(data => {
                // 결과 출력 함수 호출
                displayResults(data);
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }

        // 검색 결과를 화면에 표시
        function displayResults(analyses) {
            const resultContainer = document.getElementById('result-container');
            resultContainer.innerHTML = '';  // 기존 결과 제거

            // 분석 결과 반복 표시
            analyses.forEach(analysis => {
                const card = document.createElement('div');
                card.classList.add('result-card');

                const title = document.createElement('div');
                title.classList.add('result-title');
                title.textContent = analysis.title;
                card.appendChild(title);

                const content = document.createElement('div');
                content.classList.add('result-content');

                if (analysis.type === 'text') {
                    // 텍스트 결과 표시
                    content.textContent = analysis.content;
                } else if (analysis.type === 'chart') {
                    try {
                        console.log('Parsing chart data:', analysis.content);
                        const chartData = JSON.parse(analysis.content);  // JSON 데이터를 파싱

                        if (Array.isArray(chartData)) {
                            const chartContainer = document.createElement('div');
                            chartContainer.id = `chart-${analysis.id}`;
                            chartContainer.classList.add('chart-container');
                            card.appendChild(chartContainer);

                            // DOM에 추가된 후 차트를 렌더링
                            setTimeout(() => {
                                console.log('Chart data is valid:', chartData);
                                createBarChart(`#chart-${analysis.id}`, chartData);  // 차트 생성
                            }, 0);
                        } else {
                            console.error('Invalid chart data format:', chartData);
                            content.textContent = 'Invalid chart data format.';
                        }
                    } catch (e) {
                        console.error('Failed to parse chart data:', e);
                        content.textContent = 'Failed to parse chart data.';
                    }
                }

                card.appendChild(content);
                resultContainer.appendChild(card);
            });
        }

        // D3.js를 사용해 차트 생성
        function createBarChart(selector, data) {
            const margin = { top: 10, right: 10, bottom: 30, left: 40 },
                width = 400 - margin.left - margin.right,
                height = 300 - margin.top - margin.bottom;

            const container = d3.select(selector);

            if (!container.node()) {
                console.error(`No element found for selector: ${selector}`);
                return;
            }

            const svg = container
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

            console.log('Chart rendered successfully');
        }
    </script>
</body>
</html>
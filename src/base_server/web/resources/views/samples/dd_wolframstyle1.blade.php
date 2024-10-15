<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>D3.js Dynamic Analysis Interface</title>
    <style>
        body {
            font-family: Arial, sans-serif;
        }

        #input-section {
            margin-bottom: 20px;
        }

        input[type="text"] {
            padding: 10px;
            font-size: 16px;
            width: 70%;
            margin-right: 10px;
        }

        button {
            padding: 10px 20px;
            font-size: 16px;
        }

        #result-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }

        .result-cell {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
        }

        .result-title {
            font-weight: bold;
            margin-bottom: 10px;
        }

        .chart-container {
            width: 100%;
            height: 200px;
        }

        svg {
            width: 100%;
            height: 200px;
        }
    </style>
</head>
<body>

    <div id="input-section">
        <input type="text" id="user-input" placeholder="Enter something to analyze...">
        <button onclick="analyzeInput()">Analyze</button>
    </div>

    <div id="result-container">
        <!-- Dynamic analysis results will be displayed here -->
    </div>

    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        function analyzeInput() {
            const input = document.getElementById('user-input').value;
            const resultContainer = d3.select("#result-container");

            // Clear previous results
            resultContainer.html('');

            if (input.trim() === '') {
                alert('Please enter a valid input.');
                return;
            }

            // Example analysis results
            const results = [
                { title: 'Text Analysis', content: `You entered: "${input}"`, type: 'text' },
                { title: 'Character Count', content: input.length, type: 'text' },
                { title: 'Word Count', content: input.split(/\s+/).filter(Boolean).length, type: 'text' },
                { title: 'Sample Bar Chart', content: 'chart', type: 'chart' }
            ];

            // Create cells dynamically
            const cells = resultContainer.selectAll('.result-cell')
                .data(results)
                .enter()
                .append('div')
                .attr('class', 'result-cell');

            // Add title
            cells.append('div')
                .attr('class', 'result-title')
                .text(d => d.title);

            // Add content based on type
            cells.each(function(d, i) {
                const cell = d3.select(this);

                if (d.type === 'text') {
                    cell.append('div')
                        .text(d.content);
                } else if (d.type === 'chart') {
                    createBarChart(cell);
                }
            });
        }

        // D3.js Bar Chart Example
        function createBarChart(cell) {
            const data = [12, 19, 3, 5, 2, 3];

            const margin = { top: 10, right: 10, bottom: 30, left: 40 },
                width = 250 - margin.left - margin.right,
                height = 200 - margin.top - margin.bottom;

            const svg = cell.append('svg')
                .attr('width', width + margin.left + margin.right)
                .attr('height', height + margin.top + margin.bottom)
                .append('g')
                .attr('transform', `translate(${margin.left},${margin.top})`);

            const x = d3.scaleBand()
                .domain(data.map((d, i) => i))
                .range([0, width])
                .padding(0.1);

            const y = d3.scaleLinear()
                .domain([0, d3.max(data)])
                .nice()
                .range([height, 0]);

            // X-axis
            svg.append('g')
                .attr('transform', `translate(0,${height})`)
                .call(d3.axisBottom(x).tickFormat(i => ['A', 'B', 'C', 'D', 'E', 'F'][i]));

            // Y-axis
            svg.append('g')
                .call(d3.axisLeft(y));

            // Bars
            svg.selectAll('.bar')
                .data(data)
                .enter()
                .append('rect')
                .attr('class', 'bar')
                .attr('x', (d, i) => x(i))
                .attr('y', d => y(d))
                .attr('width', x.bandwidth())
                .attr('height', d => height - y(d))
                .attr('fill', 'steelblue');
        }
    </script>

</body>
</html>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Analysis Result</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
    <h1>File Analysis Result</h1>

    <table border="1">
        <thead>
            <tr>
                <th>File Name</th>
                <th>File Type</th>
                <th>File Size (bytes)</th>
            </tr>
        </thead>
        <tbody>
            @foreach ($fileDetails as $file)
                <tr>
                    <td>{{ $file['file_name'] }}</td>
                    <td>{{ $file['file_type'] }}</td>
                    <td>{{ $file['file_size'] }}</td>
                </tr>
            @endforeach
        </tbody>
    </table>

    <div id="chart"></div>

    <script>
        // D3.js를 사용해 파일 타입별 파일 수를 시각화
        const data = @json(array_count_values(array_column($fileDetails, 'file_type')));

        const width = 500;
        const height = 500;
        const margin = { top: 10, right: 10, bottom: 30, left: 40 };

        const svg = d3.select('#chart')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const x = d3.scaleBand()
            .domain(Object.keys(data))
            .range([margin.left, width - margin.right])
            .padding(0.1);

        const y = d3.scaleLinear()
            .domain([0, d3.max(Object.values(data))])
            .range([height - margin.bottom, margin.top]);

        svg.append('g')
            .attr('transform', `translate(0,${height - margin.bottom})`)
            .call(d3.axisBottom(x));

        svg.append('g')
            .attr('transform', `translate(${margin.left},0)`)
            .call(d3.axisLeft(y));

        svg.selectAll('.bar')
            .data(Object.entries(data))
            .enter()
            .append('rect')
            .attr('class', 'bar')
            .attr('x', d => x(d[0]))
            .attr('y', d => y(d[1]))
            .attr('width', x.bandwidth())
            .attr('height', d => height - margin.bottom - y(d[1]))
            .attr('fill', 'steelblue');
    </script>
</body>
</html>
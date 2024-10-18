<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload Compressed File</title>
</head>
<body>

<h1>Upload a Compressed File</h1>

<!--
<form id="upload-form" action="{{ route('upload') }}" method="POST" enctype="multipart/form-data">
    @csrf
    <input type="file" name="compressed_file" accept=".zip,.rar,.7z" required>
    <button type="submit">Upload</button>
</form>
-->

<form id="upload-form" enctype="multipart/form-data">
    @csrf
    <input type="file" id="compressed_file" name="compressed_file" accept=".zip,.rar,.7z" required>
    <button type="submit">Upload</button>
</form>
    
<!-- 업로드 결과를 표시할 영역 -->
<div id="upload-result"></div>

<!-- D3.js 라이브러리 -->
<script src="https://d3js.org/d3.v7.min.js"></script>

<script>
    document.getElementById('upload-form').addEventListener('submit', function (event) {
        event.preventDefault();  // 기본 폼 제출을 막음

        const formData = new FormData();
        const fileInput = document.getElementById('compressed_file');
        formData.append('compressed_file', fileInput.files[0]);

        fetch('{{ route("upload") }}', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRF-TOKEN': document.querySelector('input[name="_token"]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            // 업로드 결과를 표시
            if (data.message) {
                document.getElementById('upload-result').innerHTML = `
                    <h2>${data.message}</h2>
                    <p><strong>Uploaded File:</strong> ${data.uploaded_file}</p>
                    <p><strong>File Path:</strong> ${data.file_path}</p>
                    <p><strong>Total Files in Zip:</strong> ${data.file_info.total_files}</p>
                `;

                // 파일 정보 시각화 (히스토그램 그리기)
                drawHistogram(data.file_info.file_types);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('upload-result').innerHTML = '<p>File upload failed ...</p>';
        });
    });

    // D3.js로 히스토그램을 그리는 함수
    function drawHistogram(data) {
        const margin = {top: 20, right: 30, bottom: 40, left: 40},
              width = 800 - margin.left - margin.right,
              height = 400 - margin.top - margin.bottom;

        // SVG 초기화
        d3.select("#histogram").selectAll("*").remove();

        const svg = d3.select("#histogram")
                      .append("svg")
                      .attr("width", width + margin.left + margin.right)
                      .attr("height", height + margin.top + margin.bottom)
                      .append("g")
                      .attr("transform", `translate(${margin.left},${margin.top})`);

        // X축
        const x = d3.scaleBand()
                    .domain(data.map(d => d.type))
                    .range([0, width])
                    .padding(0.1);
        svg.append("g")
           .attr("transform", `translate(0, ${height})`)
           .call(d3.axisBottom(x));

        // Y축
        const y = d3.scaleLinear()
                    .domain([0, d3.max(data, d => d.size)])
                    .nice()
                    .range([height, 0]);
        svg.append("g")
           .call(d3.axisLeft(y));

        // 막대 생성
        svg.selectAll(".bar")
           .data(data)
           .enter()
           .append("rect")
           .attr("class", "bar")
           .attr("x", d => x(d.type))
           .attr("y", d => y(d.size))
           .attr("width", x.bandwidth())
           .attr("height", d => height - y(d.size))
           .attr("fill", "steelblue");
    }
</script>


<!-- JavaScript를 body 끝에 배치 -->
<script>
    document.addEventListener('DOMContentLoaded', function () {
        const form = document.getElementById('upload-form');
        form.addEventListener('submit', function (event) {
            event.preventDefault();  // 기본 폼 제출을 막음

            const fileInput = document.getElementById('compressed_file');
            if (fileInput && fileInput.files.length > 0) {
                const formData = new FormData();
                formData.append('compressed_file', fileInput.files[0]);

                // 파일 업로드 요청
                fetch('{{ route("upload") }}', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRF-TOKEN': document.querySelector('input[name="_token"]').value
                    }
                })
                .then(response => response.json())
                .then(data => {
                    console.log('File upload successful:', data);
                })
                .catch(error => {
                    console.error('Error:', error);
                });
            } else {
                console.error('No file selected.');
            }
        });
    });
</script>
    
</body>
</html>
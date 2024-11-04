<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DD 정량목표 진행율 (chart.js 사용)</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.3.0/papaparse.min.js"></script>
    <style>
        .progress-container {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        .progress-thumbnail {
            width: 50px;
            height: 50px;
            margin-right: 20px;
        }
        .progress-bar {
            width: 70%;
            height: 30px;
            background-color: #e0e0e0;
            border-radius: 5px;
            position: relative;
        }
        .progress {
            height: 100%;
            border-radius: 5px;
            position: absolute;
            top: 0;
            left: 0;
        }
        .progress-text {
            margin-left: 20px;
        }
    </style>
</head>
    
<body>

<center>
<h1>DD 정량목표 진행율 (chart.js 사용)</h1>
</center>
    
    <div id="progress-bars"></div>

    <script>
        // config.json에서 스프레드시트 ID를 읽어오는 함수
        function loadConfig() {
            return fetch('config/config.json')
                .then(response => response.json());
        }
    
        // config.json을 불러와서 Google Sheets 데이터 가져오기
        loadConfig().then(config => {
            const spreadsheetID = config.spreadsheetID; // config.json에서 스프레드시트 ID 가져오기
            //const apiUrl = `https://docs.google.com/spreadsheets/d/${spreadsheetID}/gviz/tq?tqx=out:json`;
            const spreadsheetUrl = `https://docs.google.com/spreadsheets/d/${spreadsheetID}/gviz/tq?tqx=out:csv`;

            // Papa Parse로 구글 스프레드시트 CSV 데이터 파싱
            Papa.parse(spreadsheetUrl, {
                download: true,
                header: true,
                complete: function(results) {
                    const data = results.data;
                    generateProgressBars(data);
                }
            });
        });

        // Progress Bar 생성 함수
        function generateProgressBars(data) {
            const container = document.getElementById('progress-bars');
            data.forEach(item => {
                const progressContainer = document.createElement('div');
                progressContainer.classList.add('progress-container');

                // 썸네일 이미지
                const thumbnail = document.createElement('img');
                thumbnail.src = item['img'];
                thumbnail.alt = item['title'];
                thumbnail.classList.add('progress-thumbnail');
                progressContainer.appendChild(thumbnail);

                // 제목 (URL 하이퍼링크)
                const titleLink = document.createElement('a');
                titleLink.href = item['url'];
                titleLink.textContent = item['title'];
                titleLink.target = "_blank";

                const progressBarWrapper = document.createElement('div');
                progressBarWrapper.classList.add('progress-bar');

                // Progress Bar
                const progressBar = document.createElement('div');
                progressBar.classList.add('progress');
                const progressPercentage = (parseFloat(item['current']) / parseFloat(item['goal'])) * 100;
                progressBar.style.width = `${progressPercentage}%`;
                progressBar.style.backgroundColor = progressPercentage >= 100 ? '#4caf50' : '#2196f3';

                // Progress Bar Wrapper에 Progress Bar 추가
                progressBarWrapper.appendChild(progressBar);

                // 제목과 Progress Bar를 Container에 추가
                progressContainer.appendChild(progressBarWrapper);
                progressContainer.appendChild(titleLink);

                // 텍스트로 달성률 표시
                const progressText = document.createElement('span');
                progressText.classList.add('progress-text');
                progressText.textContent = `${item['current']} / ${item['goal']}`;
                progressContainer.appendChild(progressText);

                // 전체 Container에 추가
                container.appendChild(progressContainer);
            });
        }
    </script>
</body>
</html>
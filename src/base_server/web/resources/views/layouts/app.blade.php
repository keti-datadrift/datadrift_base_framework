<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', 'Dashboard')</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
    <link rel="stylesheet" href="{{ asset('css/app.css') }}">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }

        .tabs {
            background-color: #2980b9;
            padding: 10px;
            display: flex;
        }

        .tabs .tab {
            margin-right: 20px;
            padding: 10px 20px;
            color: white;
            cursor: pointer;
            border-radius: 5px;
        }

        .tabs .tab.active {
            background-color: #3498db;
        }

        .sidebar {
            width: 200px;
            background-color: #2c3e50;
            color: white;
            height: 100vh;
            position: fixed;
            display: none;
        }

        .sidebar ul {
            list-style-type: none;
            padding: 0;
        }

        .sidebar ul li {
            padding: 15px;
            cursor: pointer;
        }

        .sidebar ul li:hover {
            background-color: #34495e;
        }

        .content {
            margin-left: 200px;
            width: calc(100% - 200px);
            padding: 20px;
        }

        .main-content {
            padding: 20px;
        }

        /* Dynamic layout adjustments based on tab/sidebars */
        .active-sidebar {
            display: block;
        }
    </style>
</head>
<body>

    <!-- Tabs -->
    <div class="tabs">
        <div class="tab active" data-tab="dashboard">LOGO (GO HOME)</div>
        <div class="tab active" data-tab="dashboard">Dashboard</div>
        <div class="tab" data-tab="reports">Reports</div>
        <div class="tab" data-tab="settings">Settings</div>
    </div>

    <!-- Sidebars -->
    <div class="sidebar" id="dashboard-sidebar">
        <ul>
            <li data-link="overview"> <i class="fas fa-home"></i> Overview</li>
            <li data-link="stats"> <i class="fas fa-chart-bar"></i> Statistics</li>
        </ul>
    </div>

    <div class="sidebar" id="reports-sidebar">
        <ul>
            <li data-link="sales">Sales Report</li>
            <li data-link="expenses">Expenses Report</li>
        </ul>
    </div>

    <div class="sidebar" id="settings-sidebar">
        <ul>
            <li data-link="profile">Profile Settings</li>
            <li data-link="security">Security Settings</li>
        </ul>
    </div>

    <!-- Content Area -->
    <div class="content">
        <div class="main-content" id="main-content">
            <!-- 본문 콘텐츠가 여기에서 동적으로 바뀝니다 -->
            @yield('content')
        </div>
    </div>

    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        // Tab 클릭 시, 각 탭에 맞는 사이드바 표시
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function () {
                // 탭 활성화 관리
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');

                // 사이드바 숨기기 및 해당 탭의 사이드바 표시
                const tabName = this.getAttribute('data-tab');
                document.querySelectorAll('.sidebar').forEach(sidebar => sidebar.classList.remove('active-sidebar'));
                document.getElementById(`${tabName}-sidebar`).classList.add('active-sidebar');

                // 기본 콘텐츠 초기화
                document.getElementById('main-content').innerHTML = `<h2>${tabName} Content</h2><p>Select a sidebar option to see more details.</p>`;
            });
        });

        // 사이드바 링크 클릭 시 본문 콘텐츠 변경
        document.querySelectorAll('.sidebar ul li').forEach(link => {
            link.addEventListener('click', function () {
                const contentKey = this.getAttribute('data-link');
                document.getElementById('main-content').innerHTML = `<h2>${contentKey} Content</h2><p>Content loaded for ${contentKey}.</p>`;
                
                // D3.js 차트가 필요한 경우 여기에 로드
                if (contentKey === 'stats') {
                    drawChart();
                }
            });
        });

        // D3.js 차트 그리기 예시
        function drawChart() {
            document.getElementById('main-content').innerHTML = '<div id="chart"></div>';

            const data = [10, 20, 30, 40, 50];
            const width = 400, height = 200;

            const svg = d3.select("#chart")
                .append("svg")
                .attr("width", width)
                .attr("height", height);

            svg.selectAll("rect")
                .data(data)
                .enter()
                .append("rect")
                .attr("x", (d, i) => i * 80)
                .attr("y", d => height - d)
                .attr("width", 60)
                .attr("height", d => d)
                .attr("fill", "steelblue");
        }

        // 초기 상태 설정: 대시보드 탭과 사이드바 활성화
        document.getElementById('dashboard-sidebar').classList.add('active-sidebar');
        document.getElementById('main-content').innerHTML = `<h2>Dashboard Content</h2><p>Select a sidebar option to see more details.</p>`;
    </script>
</body>
</html>
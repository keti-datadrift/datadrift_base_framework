<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', 'Data Drift Management System')</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
    <link rel="stylesheet" href="{{ asset('css/app.css') }}">
    
    <!-- Font Awesome CSS -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">

    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }

        /* iframe을 main-content 영역에 꽉 채우도록 설정 */
        #main-content {
            width: 100%;         /* 가로로 화면 전체를 차지 */
            height: 100vh;       /* 세로로 화면 전체를 차지 (뷰포트 높이 100%) */
            border: none;        /* 테두리 없애기 */
            display: block;      /* 기본적으로 iframe을 블록 요소로 처리 */
            position: fixed;
        }

        .tabs {
            background-color: #2980b9;
            padding: 10px;
            display: flex;
            justify-content: space-between; /* 좌우 간격을 최대한으로 벌림 */
            align-items: center; /* 수직 정렬 */
        }

        .tabs-left {
            display: flex;
        }
        
        .tabs-right {
            display: flex;
        }
        
        .tabs .tab {
            margin-right: 20px;
            padding: 10px 20px;
            color: white;
            cursor: pointer;
            border-radius: 5px;
            font-size: 15px; /* 탭의 글자 크기를 여기서 설정합니다 */
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

        .active-link {
            background-color: #1abc9c;
        }
    </style>
</head>

    
<body>
    <!-- Tabs -->
    <div class="tabs">
        <!----------------------------->
        @guest
        <div class="tabs-left">
            <div class="tab" data-tab="home"><i class="fas fa-home"></i> Data Drift Management System</div>
        </div>
        <div class="tabs-right">
            <div class="tab" data-tab="login"><a href="javascript:void(0)" style="color: white;">Login</i> </a></div>
            <div class="tab" data-tab="register"><a href="javascript:void(0)" style="color: white;">Register</a></div>
        </div>

        <!----------------------------->
        @else
        <div class="tabs-left">
            <div class="tab" data-tab="home"><i class="fas fa-home"></i> Data Drift Management</div>
            <div class="tab" data-tab="demos"><i class="fas fa-laptop"></i> 시연</div>
            <div class="tab" data-tab="reports"><i class="fas fa-laptop"></i> 검출</div>
            <div class="tab" data-tab="reports"><i class="fas fa-laptop"></i> 파이프라인</div>
            <div class="tab" data-tab="settings"><i class="fas fa-laptop"></i> 비전AI</div>
            <div class="tab" data-tab="settings"><i class="fas fa-laptop"></i> 추적관리</div>
        </div>
        
        <div class="tabs-right">
            <div class="tab"><i class="fa fa-user" aria-hidden="true"></i> {{ Auth::user()->name }}</div>
            <div class="tab">
                <a href="#" onclick="event.preventDefault(); document.getElementById('logout-form').submit();" style="color: white;">
                   <i class="fa fa-sign-out" aria-hidden="true"></i> Logout
                </a>
                <form id="logout-form" action="{{ route('logout') }}" method="POST" style="display: none;">
                    @csrf
                </form>
            </div>
        </div>
        @endguest
    </div>

    <!-- Sidebars -->
    <div class="sidebar" id="home-sidebar">
        <ul>
            <li data-link="overview">Overview</li>
        </ul>
    </div>

    <div class="sidebar" id="project-sidebar">
        <ul>
            <li data-link="pages_progress1">과제 정량 목표</li>
            <li data-link="expenses">todo</li>
        </ul>
    </div>

    <div class="sidebar" id="demos-sidebar">
        <ul>
            <li data-link="pages_demoui">demoui</li>
            <li data-link="pages_map1">map1</li>
            <li data-link="pages_map2">map2</li>
            <li data-link="pages_confusion1">human graph 1</li>
            <li data-link="pages_confusion2">human graph 2</li>
            <li data-link="pages_confusion3">human graph 3</li>
            <li data-link="pages_cm1">cm1</li>
            <li data-link="pages_cm2">cm2</li>
            <li data-link="pages_cm3">cm3</li>
            <li data-link="pages_cm4">cm4</li>
            <li data-link="pages_cm5">cm5</li>
            <li data-link="test">Reserved</li>
        </ul>
    </div>


    <div class="sidebar" id="settings-sidebar">
        <ul>
            <li data-link="profile">Profile Settings</li>
            <li data-link="security">Security Settings</li>
        </ul>
    </div>

    <div class="sidebar" id="login-sidebar">
        <ul>
            <li data-link="profile">todo</li>
            <li data-link="profile"><i class="fas fa-cog"></i> Settings</li>
        </ul>
    </div>

    <div class="sidebar" id="register-sidebar">
        <ul>
            <li data-link="profile">todo</li>
        </ul>
    </div>

    
    <!-- Content Area -->
    <div class="content">
        <!-- Iframe을 통해 페이지를 렌더링 -->
        <iframe id="main-content" src="/overview" width="100%" height="100%" />></iframe>

        <!-- 본문 콘텐츠가 여기에서 동적으로 바뀝니다 -->
        <!--
        <div class="main-content2" id="main-content2">
            <h2>Welcome to DD</h2>
            <p>Select a tab or sidebar option to see more details.</p>
        </div>
        -->
    </div>

    <script>

        // 페이지를 비동기로 로드하는 함수
        function loadPage_content(url) {
            fetch(url)
                .then(response => response.text())
                .then(html => {
                    document.getElementById('main-content').innerHTML = html;
                })
                .catch(error => console.log('Error:', error));
        }
        
        // 페이지를 비동기로 로드하는 함수
        function loadPage_iframe(url) {
            // iframe 요소를 찾아서 src 속성을 변경하여 해당 페이지 로드
            const iframe = document.getElementById('main-content');
            if (iframe) {
                iframe.src = url;
            } else {
                console.log('Error: iframe element not found');
            }
        }
        

        // Tab 클릭 시, 각 탭에 맞는 사이드바 표시
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function () {
                // 탭 활성화 관리
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');

                // 사이드바 숨기기 및 해당 탭의 사이드바 표시
                const tabName = this.getAttribute('data-tab');
                document.querySelectorAll('.sidebar').forEach(sidebar => sidebar.classList.remove('active-sidebar'));
                const sidebar = document.getElementById(`${tabName}-sidebar`);
                if (sidebar) {
                    sidebar.classList.add('active-sidebar');
                }

                // 페이지 로드 (로그인, 회원가입 등)
                if (tabName === 'login') {
                    loadPage_iframe('/login');
                } else if (tabName === 'logout') {
                    loadPage_iframe('/intro');
                } else if (tabName === 'register') {
                    loadPage_iframe('/register');
                }
            });
        });

        // 사이드바 링크 클릭 시 본문 콘텐츠 변경
        /*
        document.querySelectorAll('.sidebar ul li').forEach(link => {
            link.addEventListener('click', function () {
                const contentKey = this.getAttribute('data-link');
                let url = `/${contentKey}`;

                // 활성화된 링크 스타일 관리
                document.querySelectorAll('.sidebar ul li').forEach(li => li.classList.remove('active-link'));
                this.classList.add('active-link');

                loadPage(url);

            });
        });
        */

        // 사이드바에서 링크 클릭 시 iframe의 src를 변경하여 페이지를 동적으로 로드
        document.querySelectorAll('.sidebar ul li').forEach(link => {
            link.addEventListener('click', function () {
                const contentKey = this.getAttribute('data-link');
                const iframe = document.getElementById('main-content');
                let url = `/${contentKey}`;  // 원하는 페이지의 URL

                // iframe에 새 페이지 로드
                loadPage_iframe(url);

                // 활성화된 링크 스타일 관리
                document.querySelectorAll('.sidebar ul li').forEach(li => li.classList.remove('active-link'));
                this.classList.add('active-link');
            });
        });
        

        // 초기 상태 설정: 대시보드 탭과 사이드바 활성화
        document.getElementById('home-sidebar').classList.add('active-sidebar');
        //loadPage_content('/intro');
    </script>

</body>
</html>
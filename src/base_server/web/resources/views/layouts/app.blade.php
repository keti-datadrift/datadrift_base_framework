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
    
    <!-- Vite로 번들된 자바스크립트와 CSS 파일을 로드 -->
    @vite('js/app.js')

    <style>
        body {
            background-color: #212121;
            color: white;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }

        /* iframe을 main-content 영역에 꽉 채우도록 설정 */
        #main-content {
            width: 100%;         /* 가로로 화면 전체를 차지 */
            height: 80vh;       /* 세로로 화면 전체를 차지 (뷰포트 높이 80%) */
            border: none;        /* 테두리 없애기 */
            display: block;      /* 기본적으로 iframe을 블록 요소로 처리 */
            position: fixed;
            top: 10vh;
            color: white;
        }

        .tabs {
            background-color: #0d0d0d;
            padding: 20px;
            display: flex;
            justify-content: space-between; /* 좌우 간격을 최대한으로 벌림 */
            align-items: center; /* 수직 정렬 */
            min-width: 1200px;     /* 최소 너비 설정 */
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
            background-color: #0d0d0d;
            color: white;
            height: 80vh;
            position: fixed;
            display: none;
        }

        .sidebar-narrow {
            width: 10px;
            background-color: #0d0d0d;
            color: white;
            height: 80vh;
            position: fixed;
            display: none;
        }

        /* Footer 스타일 */
        .footer {
            background-color: #0d0d0d;
            color: white;
            height: 10vh;
            width: 100%;
            position: fixed;
            bottom: 0;
            display: flex;
            justify-content: space-between; /* 요소들 사이에 간격 */
            align-items: center;             /* 수직 가운데 정렬 */
            padding: 0 0px;                 /* 좌우 padding 추가 */
            font-size: 10px;
            min-width: 1200px;     /* 최소 너비 설정 */
        }

        .footer-item {
            margin: 0 10px; /* 각 개체 간 좌우 10px 간격 */
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
    <!-- 새로 추가된 헤더 영역 -->
    
    <!--
    <div class="header">
        <p> 데이터 드리프트 관리 기술 개발 </p>
        &nbsp;&nbsp;&nbsp;&nbsp;
        <a href="http://datadrift.kr">
            <img height=30px src='images/logo/keti-logo1.png'></img>
            <img height=20px src='images/logo/dq-logo1.png'></img>
            <img height=20px src='images/logo/iv-logo1.png'></img>
            <img height=20px src='images/logo/skku-logo1.jpg'></img>
            <img height=20px src='images/logo/knpu-logo1.png'></img>
            <img height=15px src='images/logo/bcave-logo1.png'></img>
            <img height=25px src='images/logo/osan-logo1.png'></img>
        </a>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
    </div>
    -->
    
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
            <div class="tab" data-tab="home" data-link="pages_demoui"><i class="fa fa-home"></i> 데이터 드리프트 관리기술 </div>
            <div class="tab" data-tab="dd_targetservices" data-link="pages_demoui"><i class="fa fa-user-md"></i> 분석대상</div>
            <div class="tab" data-tab="dd_detection"><i class="fa fa-search"></i> 드리프트 검출</div>
            <div class="tab" data-tab="dd_pipeline"><i class="fa fa-tasks"></i> 데이터 재구성</div>
            <div class="tab" data-tab="dd_deployment"><i class="fa fa-paper-plane"></i> 능동적 배포</div>
            <!--
            <div class="tab" data-tab="dd_visionai"><i class="fa fa-video-camera"></i> 비전AI</div>
            -->
            <div class="tab" data-tab="dd_management"><i class="fa fa-pie-chart"></i> 추적관리</div>
            
            <!--
            <div class="tab" data-tab="demos"><i class="fas fa-laptop"></i> 시연</div>
            -->
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
            <li data-link="overview">개념도</li>
            <li data-link="overview2">구조도</li>
            <li data-link="overview2">시연순서</li>
        </ul>
    </div>

    <div class="sidebar" id="project-sidebar">
        <ul>
            <li data-link="pages_progress1">과제 정량 목표</li>
            <li data-link="expenses">todo</li>
        </ul>
    </div>

    <!-- (실증) 타겟 서비스 : 교통,마케팅 -->
    <div class="sidebar" id="dd_targetservices-sidebar">
        <ul>
            <li data-link="dd_targetservices_lp_detection">차량 번호판 영역 검출</li>
            <li data-link="dd_targetservices_lp_ocr">차량 번호판 OCR</li>
            <li data-link="dd_targetservices_car_detection">차량 객체 분류</li>
            <li data-link="dd_targetservices_marketing">마케팅 전략 수립</li>
            <li data-link="dd_targetservices_video_4ch_player">[test] 4ch play</li>
        </ul>
    </div>

    <!-- 검출 -->
    <div class="sidebar" id="dd_detection-sidebar">
        <ul>
            <li data-link="detection1">d1</li>
            <li data-link="detection2">d2</li>
            <li data-link="detection3">d3</li>
            <li data-link="detection4">d4</li>
        </ul>
    </div>

    <!-- 파이프라인 -->
    <div class="sidebar-narrow" id="dd_pipeline-sidebar">
    </div>

    <!-- 비전 AI -->
    <div class="sidebar" id="dd_visionai-sidebar">
        <ul>
            <li data-link="pages_demoui">demoui</li>
        </ul>
    </div>

    <!-- 추적 관리 -->
    <div class="sidebar" id="dd_management-sidebar">
        <ul>
            <li data-link="pages_demoui">demoui</li>
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
        
<!-- Toggle Sidebar Buttons -->
    
        <!-- Iframe을 통해 페이지를 렌더링 -->
        <iframe id="main-content" src="/overview" width="100%" height="100%" /></iframe>

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
        // iframe이 로드된 후 발생하는 이벤트 핸들러 추가
        function loadPage_iframe(url) {
            const iframe = document.getElementById('main-content');
            if (iframe) {
                iframe.src = url;

                document.getElementById('iframe-id').onload = function() {
                
                    // 페이지가 로드된 후 jQuery 실행
                // 오류 방지
                try {
                        document.querySelector( ":has(*,:jqfake)" );
                    } catch (e) {
                        console.error("jQuery error: ", e);
                    }
                };

                // iframe이 로드된 후 처리할 동작
                iframe.onload = function() {
                    console.log("Iframe loaded successfully");
                    // 필요 시 추가 작업
                };
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
                    toggleSidebar(false); // 로그인 탭에서는 사이드바 숨기기
                } else if (tabName === 'logout') {
                    loadPage_iframe('/intro');
                    toggleSidebar(false); // 로그인 탭에서는 사이드바 숨기기
                } else if (tabName === 'register') {
                    loadPage_iframe('/register');
                    toggleSidebar(false); // 로그인 탭에서는 사이드바 숨기기
                } else if (tabName === 'dashboard') {
                    loadPage_iframe('/dashboard');
                    toggleSidebar(false); // 로그인 탭에서는 사이드바 숨기기
                } else if (tabName === 'dd_pipeline') {
                    loadPage_iframe('/dd_pipeline');
                    toggleSidebar(false); // 로그인 탭에서는 사이드바 숨기기
                } else {
                    toggleSidebar(true); // 로그인 탭에서는 사이드바 숨기기
                }


            });
        });

        // Sidebar 클릭 시, 메인 콘텐츠에 해당 페이지 로드
        document.querySelectorAll('.sidebar ul li').forEach(link => {
            link.addEventListener('click', function () {
                const contentKey = this.getAttribute('data-link');
                let url = `/${contentKey}`;
                loadPage_iframe(url);

                // 사이드바 링크 활성화 상태 관리
                document.querySelectorAll('.sidebar ul li').forEach(li => li.classList.remove('active-link'));
                this.classList.add('active-link');
            });
        });

        // 사이드바를 숨기고 메인 콘텐츠를 전체 화면으로 표시하는 함수
        function toggleSidebar(show) {
            const sidebar = document.querySelector('.active-sidebar');
            const content = document.getElementById('main-content');
            
            if (show) {
                // 사이드바를 보이게 하고 메인 콘텐츠 크기 조정
                if (sidebar) sidebar.style.display = 'block';
                content.style.width = 'calc(100% - 200px)';
                content.style.marginLeft = '200px';
            } else {
                // 사이드바를 숨기고 메인 콘텐츠를 전체 화면으로 확장
                if (sidebar) sidebar.style.display = 'none';
                content.style.width = '100%';
                content.style.marginLeft = '0';
            }
        }
        
        // 초기 상태 설정: 대시보드 탭과 사이드바 활성화
        document.getElementById('home-sidebar').classList.add('active-sidebar');
        //loadPage_content('/intro');
    </script>

    <!-- footer -->
    <div class="footer">
        <div class="footer-item" bgcolor=white>
            <img height=30px src='images/logo/keti-logo1.png'></img>
            <img height=20px src='images/logo/dq-logo1.png'></img>
            <img height=20px src='images/logo/iv-logo1.png'></img>
            <img height=20px src='images/logo/skku-logo1.jpg'></img>
            <img height=20px src='images/logo/knpu-logo1.png'></img>
            <img height=15px src='images/logo/bcave-logo1.png'></img>
            <img height=25px src='images/logo/osan-logo1.png'></img>
            &nbsp;&nbsp;&nbsp;&nbsp;
    </div>
</body>
</html>

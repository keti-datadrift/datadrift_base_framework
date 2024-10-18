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
            margin: 0;
            padding: 0;
            background-color: #262b3c;
            color: white;
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column; /* 행방향 배치 */
            height: 100vh;
        }

        .tabs {
            background-color: #262b3c;
            padding: 0px;
            display: flex;
            justify-content: space-around; 
            align-items: center; /* 수직 정렬 */
            min-width: 1250px; /* 최소 너비 설정 */
            height: 10vh;
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

        .dropdown {
            display: none; /* 드롭다운 메뉴 기본적으로 숨김 */
            position: absolute;
            top: 40px;
            left: 0;
            background-color: #ffffff;
            color: black;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            z-index: 100;
        }

        .dropdown ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .dropdown ul li {
            padding: 10px 20px;
            cursor: pointer;
        }

        .dropdown ul li:hover {
            background-color: #f0f0f0;
        }

        .header {
            background-color: #222736;
            height: 15px;
            padding: 10px;
            text-align: center;
            font-weight: bold;
        }




        .expanded-content {
            width: 100%;
            margin-left: 0;
        }

        /* Footer 스타일 */
        .footer1 {
            background-color: #212121;
            color: white;
            height: 40px;
            width: 100%;
            position: fixed;
            bottom: 0;
            display: flex;
            justify-content: center;
            align-items: center;             /* 수직 가운데 정렬 */
            padding: 0 0px;                 /* 좌우 padding 추가 */
            font-size: 10px;
            min-width: 1250px;     /* 최소 너비 설정 */
        }
        .footer2 {
            background-color: #ffffff;
            color: white;
            height: 30px;
            width: 100%;
            position: fixed;
            bottom: 0;
            display: flex;
            justify-content: center;
            align-items: center;             /* 수직 가운데 정렬 */
            padding: 0 0px;                 /* 좌우 padding 추가 */
            font-size: 10px;
            min-width: 1250px;     /* 최소 너비 설정 */
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

        .main-content {
            margin-left: 200px;
            width: calc(100% - 200px);
            padding: 20px;
            color: white;
        }

        .main {
            display: flex;
            flex: 1;
            transition: all 0.3s ease;
        }

        /* Dynamic layout adjustments based on tab/sidebars */
        .active-sidebar {
            display: block;
        }

        .active-link {
            background-color: #1abc9c;
        }

        /* iframe을 main-content 영역에 꽉 채우도록 설정 */
        #main-content-frame {
            width: 100%;         /* 가로로 화면 전체를 차지 */
            height: 90vh;       /* 세로로 화면 전체를 차지 (뷰포트 높이 80%) */
            border: none;        /* 테두리 없애기 */
            display: block;      /* 기본적으로 iframe을 블록 요소로 처리 */
            position: fixed;
            top: 20vh;
            color: white;
        }

    </style>
</head>

    
<body>
    <!-- Tabs -->
    <div class="tabs">
        <!----------------------------->
        @guest
        <div class="tabs-left">            
            <div class="tab" data-tab="home" data-link="pages_demoui"><i class="fa fa-home"></i> 데이터 드리프트 관리기술 </div>
            <div class="tab" data-tab="dd_targetservices" data-link="pages_demoui"><i class="fa fa-user-md"></i> 분석대상</div>
            <div class="tab" data-tab="dd_detection"><i class="fa fa-search"></i> 드리프트 검출</div>
            <div class="tab" data-tab="dd_pipeline"><i class="fa fa-tasks"></i> 데이터 재구성</div>
            <div class="tab" data-tab="dd_deployment"><i class="fa fa-paper-plane"></i> 능동적 배포</div>
            <div class="tab" data-tab="dd_management"><i class="fa fa-pie-chart"></i> 추적관리</div>
            
            <div class="tab" data-tab="login"><a href="javascript:void(0)" style="color: white;">Login</i> </a></div>
            <div class="tab" data-tab="register"><a href="javascript:void(0)" style="color: white;">Register</a></div>
        </div>

        <!----------------------------->
        @else
        <div class="tabs-left">
            <div class="tab" data-tab="home"><i class="fas fa-home"></i> 데이터 드리프트 관리기술 </div>
            <div class="tab" data-tab="dd_targetservices" data-link="pages_demoui"><i class="fa fa-user-md"></i> 분석대상</div>
            <div class="tab" data-tab="dd_detection"><i class="fa fa-search"></i> 드리프트 검출</div>
            <div class="tab" data-tab="dd_pipeline"><i class="fa fa-tasks"></i> 데이터 재구성</div>
            <div class="tab" data-tab="dd_deployment"><i class="fa fa-paper-plane"></i> 능동적 배포</div>
            <div class="tab" data-tab="dd_management"><i class="fa fa-pie-chart"></i> 추적관리</div>
            
            <!--
            <div class="tab" data-tab="dd_visionai"><i class="fa fa-video-camera"></i> 비전AI</div>
            -->
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

    <!-- 새로 추가된 헤더 영역 -->
    <div class="header" id="header-content">
        데이터 드리프트 관리 기술 개발
    </div>


    <div class="dropdown" id="home-dropdown">
        <ul>
            <li data-link="overview">개념도</li>
            <li data-link="overview2">구조도</li>
            <li data-link="overview2">시연순서</li>
        </ul>
    </div>





    
    <!-- Content Area -->
    <div class="main-content">
        <!-- Iframe을 통해 페이지를 렌더링 -->
        <iframe id="main-content-frame" src="/overview" width="100%" height="100%" /></iframe>
    </div>

    <script>
        // 페이지를 비동기로 로드하는 함수
        function loadPage_content(url) {
            fetch(url)
                .then(response => response.text())
                .then(html => {
                    document.getElementById('main-content-frame').innerHTML = html;
                })
                .catch(error => console.log('Error:', error));
        }
        
        // 페이지를 비동기로 로드하는 함수
        // iframe이 로드된 후 발생하는 이벤트 핸들러 추가
        function loadMainContent(url) {
            const iframe = document.getElementById('main-content-frame');
            if (iframe) {
                iframe.src = url;
                document.getElementById('main-content-frame').onload = function() {
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


        // Main Content 업데이트 함수
        function loadInitMainContent(tab) {
            const iframe = document.getElementById('main-content-frame');
            if (tab === 'home') {
                loadMainContent('/overview');
            } else if (tab === 'dd_targetservices') {
                loadMainContent('/dd_targetservices_overview');
            } else if (tab === 'dd_detection') {
                loadMainContent('/dd_detection_overview');
            } else if (tab === 'dd_pipeline') {
                loadMainContent('/dd_pipeline_overview');
            } else if (tab === 'dd_deployment') {
                loadMainContent('/dd_deployment_overview');
            } else if (tab === 'dd_management') {
                loadMainContent('/dd_management_overview');
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
                    toggleSidebar(true); // 로그인 탭에서는 사이드바 숨기기
                } else if (tabName === 'logout') {
                    loadPage_iframe('/intro');
                    toggleSidebar(true); // 로그인 탭에서는 사이드바 숨기기
                } else if (tabName === 'register') {
                    loadPage_iframe('/register');
                    toggleSidebar(true); // 로그인 탭에서는 사이드바 숨기기
                } else if (tabName === 'dd_pipeline') {
                    toggleSidebar(false); // 로그인 탭에서는 사이드바 숨기기
                } else {
                    toggleSidebar(false); // 로그인 탭에서는 사이드바 숨기기
                }


                updateHeader(tabName);
                loadInitMainContent(tabName);
            });
        });

        // Header 업데이트 함수
        function updateHeader(tab) {
            const header = document.getElementById('header-content');
            if (tab === 'home') {
                header.textContent = 'home';
                toggleSidebar(true);
            } else if (tab === 'dd_targetservices') {
                toggleSidebar(false);
                header.textContent = 'dd_targetservices';
            } else if (tab === 'dd_detection') {
                header.textContent = 'dd_detection';
            } else if (tab === 'dd_pipeline') {
                header.textContent = 'dd_pipeline';
            } else if (tab === 'dd_deployment') {
                header.textContent = 'dd_deployment';
            } else if (tab === 'dd_management') {
                header.textContent = 'dd_management';
            } else if (tab === 'dd_management') {
                header.textContent = 'dd_management';
            } else if (tab === 'dd_management') {
                header.textContent = 'dd_management';
            } else if (tab === 'login') {
                header.textContent = 'login';
            } else if (tab === 'logout') {
                header.textContent = 'logout';
            } else if (tab === 'register') {
                header.textContent = 'register';
            } 
        }

        // Sidebar 업데이트 함수
        function updateSidebar(tab) {
            const sidebar = document.getElementById('sidebar-content');
            let content = '';
            if (tab === 'home') {
                content = '<ul><li>Home Menu 1</li><li>Home Menu 2</li></ul>';
            } else if (tab === 'profile') {
                content = '<ul><li>Profile Menu 1</li><li>Profile Menu 2</li></ul>';
            } else if (tab === 'settings') {
                content = '<ul><li>Settings Menu 1</li><li>Settings Menu 2</li></ul>';
            }
            sidebar.innerHTML = content;
        }


        // Sidebar 클릭 시, 메인 콘텐츠에 해당 페이지 로드
        document.querySelectorAll('.sidebar ul li').forEach(link => {
            link.addEventListener('click', function () {
                const contentKey = this.getAttribute('data-link');
                let url = `/${contentKey}`;
                loadMainContent(url);

                // 사이드바 링크 활성화 상태 관리
                document.querySelectorAll('.sidebar ul li').forEach(li => li.classList.remove('active-link'));
                this.classList.add('active-link');
            });
        });

        // Sidebar를 숨기고 Main Content를 전체 화면으로 표시하거나 복원하는 함수
        function toggleSidebar(show) {
            const sidebar = document.querySelector('.sidebar');
            const content = document.querySelector('.main-content');
            
            if (content) {  // content가 null이 아닌지 확인
                if (show) {
                    // 사이드바를 보이게 하고 메인 콘텐츠 크기 조정
                    sidebar.classList.remove('hidden-sidebar');
                    content.classList.remove('expanded-content');
                } else {
                    // 사이드바를 숨기고 메인 콘텐츠를 전체 화면으로 확장
                    sidebar.classList.add('hidden-sidebar');
                    content.classList.add('expanded-content');
                }
            } else {
                console.error('Main content element not found!');
            }
        }

        
        // 초기 상태 설정: 대시보드 탭과 사이드바 활성화
        document.getElementById('home-sidebar').classList.add('active-sidebar');
        //loadPage_content('/intro');
    </script>

    <!-- footer -->
    <div class="footer1">
    </div>

    <div class="footer2">
        <div class="footer-item">
            <img height=25px src='images/logo/all-logo.png'></img>&nbsp;
        </div>
    </div>
</body>
</html>

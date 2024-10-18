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
            color: #ffffff;
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
            min-width: 1500px; /* 최소 너비 설정 */
            height: 70px;
        }

        .tabs-left {
            display: flex;
        }
        
        .tabs-right {
            display: flex;
        }
        
        .tabs .tab {
            font-weight: bold;
            position: relative; /* 드롭다운 메뉴가 이 탭을 기준으로 위치 */
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
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            background-color: #556ee6;
            color: #ffffff;
            font-weight: 450
            border-radius: 10px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
            z-index: 100;
            width: 300px;
            opacity: 1;
            transform: translateY(10px); /* 약간 아래에서 올라오듯이 */
            transition: opacity 0.3s ease, transform 0.3s ease; /* 애니메이션 */
        }
        
        .dropdown ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .dropdown ul li {
            list-style: none;
            padding: 10px 20px;
            cursor: pointer;
        }

        .dropdown ul li:hover {
            background-color: #777ee6;
            padding: 12px 20px;
            cursor: pointer;
            transition: background-color 0.3s ease;
            border-radius: 10px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
        }

        .header {
            background-color: #222736;
            color: #aaaaaa;
            height: 20px;
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
        }
        .footer2 {
            background-color: #ffffff;
            color: white;
            height: 50px;
            width: 100%;
            position: fixed;
            bottom: 0;
            display: flex;
            justify-content: center;
            align-items: center;             /* 수직 가운데 정렬 */
            padding: 0 0px;                 /* 좌우 padding 추가 */
            font-size: 10px;
        }

        .footer-item {
            margin: 0 10px; /* 각 개체 간 좌우 10px 간격 */
        }

        .main-content {
            margin-left: 5px;
            top: 0px;
            width: calc(100% - 5px);
            padding: 0px;
            color: white;
            justify-content: center;
        }

        .main {
            display: flex;
            flex: 1;
            transition: all 0.3s ease;
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
            top: 110px;
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
            <div class="tab" data-tab="login"><a href="javascript:void(0)" style="color: white;">Login</i> </a></div>

            <div class="tab" data-tab="register"><a href="javascript:void(0)" style="color: white;">Register</a></div>
        </div>

        <!----------------------------->
        @else
        <div class="tabs-left">
            <div class="tab" data-tab="home"><i class="fas fa-home"></i> 데이터 드리프트 관리기술 
                <div class="dropdown" id="dropdown-home">
                    <ul>
                        <li data-link="/ov1">기존의 문제점</li>
                        <li data-link="/ov2">기술의 지향점</li>
                    </ul>
                </div>
            </div>
            
            <div class="tab" data-tab="targetservices" data-link="pages_demoui"><i class="fa fa-user-md"></i> 분석 서비스 예시
                <div class="dropdown" id="dropdown-targetservices">
                    <ul>
                        <li data-link="/targetservices_lp_detection">교통 사고 분석</li>
                        <li data-link="/page2">지능형 영상 처리</li>
                        <li data-link="/page2">마케팅 전략 수립</li>
                    </ul>
                </div>
            </div>
            
            <div class="tab" data-tab="detection"><i class="fa fa-search"></i> 드리프트 검출
                <div class="dropdown" id="dropdown-targetservices">
                    <ul>
                        <li data-link="/detection1">검출 시각화 1</li>
                        <li data-link="/detection2">검출 시각화 2</li>
                        <li data-link="/detection3">검출 시각화 3</li>
                        <li data-link="/detection4">검출 시각화 4</li>
                    </ul>
                </div>
            </div>
            
            <div class="tab" data-tab="pipeline"><i class="fa fa-tasks"></i> 데이터 재구성 및 학습
                <div class="dropdown" id="dropdown-targetservices">
                    <ul>
                        <li data-link="/page1">Page 1d</li>
                        <li data-link="/page2">Page 2d</li>
                    </ul>
                </div>
            </div>
            
            <div class="tab" data-tab="deployment"><i class="fa fa-paper-plane"></i> 능동적 배포
                <div class="dropdown" id="dropdown-targetservices">
                    <ul>
                        <li data-link="/page1">Page 1e</li>
                    </ul>
                </div>
            </div>
            
            <div class="tab" data-tab="management"><i class="fa fa-pie-chart"></i> 추적 관리
                <div class="dropdown" id="dropdown-targetservices">
                    <ul>
                        <li data-link="/page1">Page 1</li>
                        <li data-link="/page2">Page 2</li>
                    </ul>
                </div>
            </div>
            
            <!--
            <div class="tab" data-tab="visionai"><i class="fa fa-video-camera"></i> 비전AI</div>
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





    
    <!-- Content Area -->
    <div class="main-content">
        <!-- Iframe을 통해 페이지를 렌더링 -->
        <iframe id="main-content-frame" src="/ov1" width="100%" height="100%" /></iframe>
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
            } else if (tab === 'targetservices') {
                loadMainContent('/targetservices_overview');
            } else if (tab === 'detection') {
                loadMainContent('/detection_overview');
            } else if (tab === 'pipeline') {
                loadMainContent('/pipeline_overview');
            } else if (tab === 'deployment') {
                loadMainContent('/deployment_overview');
            } else if (tab === 'management') {
                loadMainContent('/management_overview');
            }
        }

        // Header 업데이트 함수
        function updateHeader(tab) {
            const header = document.getElementById('header-content');
            if (tab === 'home') {
                header.textContent = '';
            } else if (tab === 'targetservices') {
                header.textContent = '교통 데이터 분석 및 성능 개선, 마케팅 분석 측면';
            } else if (tab === 'detection') {
                header.textContent = 'detection';
            } else if (tab === 'pipeline') {
                header.textContent = 'pipeline';
            } else if (tab === 'deployment') {
                header.textContent = 'deployment';
            } else if (tab === 'management') {
                header.textContent = 'management';
            } else if (tab === 'management') {
                header.textContent = 'management';
            } else if (tab === 'management') {
                header.textContent = 'management';
            } else if (tab === 'login') {
                header.textContent = 'login';
                loadMainContent('/login');
            } else if (tab === 'logout') {
                header.textContent = 'logout';
                loadMainContent('/logout');
            } else if (tab === 'register') {
                header.textContent = 'register';
                loadMainContent('/register');
            } 
        }

        // Tab 클릭 시 드롭다운 토글
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function () {
                // 모든 드롭다운 숨기기
                document.querySelectorAll('.dropdown').forEach(dd => dd.style.display = 'none');

                // 현재 탭의 드롭다운만 보이게 하기
                const dropdown = this.querySelector('.dropdown');
                if (dropdown) {
                    dropdown.style.display = (dropdown.style.display === 'block') ? 'none' : 'block';
                }

                // 탭 활성화 상태 관리
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');

                // Update
                const tabName = this.getAttribute('data-tab');
                updateHeader(tabName);
                //loadInitMainContent(tabName);
            });
        });

        // 드롭다운 메뉴 클릭 시 메인 콘텐츠 로드
        document.querySelectorAll('.dropdown ul li').forEach(item => {
            item.addEventListener('click', function (e) {
                e.stopPropagation();  // 드롭다운이 닫히지 않도록 이벤트 전파 막음
                const link = this.getAttribute('data-link');
                loadMainContent(link);

                // 드롭다운 메뉴 숨기기
                document.querySelectorAll('.dropdown').forEach(dd => dd.style.display = 'none');
            });
        });

        // 클릭 외부 시 드롭다운 닫기
        document.addEventListener('click', function (e) {
            if (!e.target.closest('.tab')) {
                document.querySelectorAll('.dropdown').forEach(dd => dd.style.display = 'none');
            }
        });




    </script>

    <!-- footer -->
    <div class="footer1">
    </div>

    <div class="footer2">
        <div class="footer-item">
            <img height=45px src='images/logo/all-logo.png'></img>&nbsp;
        </div>
    </div>
</body>
</html>

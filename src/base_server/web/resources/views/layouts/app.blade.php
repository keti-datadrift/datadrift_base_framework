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
            height: 110px;
            min-width: 1000px; /* 최소 너비 설정 */
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
            margin-right: 0px;
            padding: 10px 20px;
            color: white;
            cursor: pointer;
            border-radius: 5px;
            font-size: 17px; /* 탭의 글자 크기를 여기서 설정합니다 */
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

        .expanded-content {
            width: 100%;
            margin-left: 0;
        }

        /* Footer 스타일 */
        .talk {
            background-color: #222736;
            color: #aaeeff;
            height: 50px;
            width: 100%;
            position: fixed;
            bottom: 50px;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 0 0px;
            font-size: 19px;
            text-align: left;
            font-weight: normal;
        }

        .talk_tmp {
            background-color: #222736;
            color: #aaaaaa;
            height: 20px;
            padding: 10px;
            text-align: center;
            font-weight: bold;
        }

        .footer {
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
            text-align: center;
            font-weight: bold;
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
            height: 100vh;       /* 세로로 화면 전체를 차지 (뷰포트 높이 80%) */
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
            <div class="tab" data-tab="home">
                <i class="fas fa-home"></i> 데이터 드리프트 관리기술 
                <div class="dropdown" id="dropdown-home">
                    <ul>
                        <li data-link="/ov1">기존의 문제점</li>
                        <li data-link="/ov2">기술의 지향점</li>
                    </ul>
                </div>
            </div>
            
        
            <div class="tab" data-tab="targetservices" data-link="pages_demoui">
                <i class="fa fa-user-md"></i> 분석 대상 예시
                <div class="dropdown" id="dropdown-targetservices">
                    <ul>
                        <li data-link="/targetservices_lp_ocr">교통 및 차량 데이터 분석</li>
                    </ul>
                </div>
            </div>
    
            
            <div class="tab" data-tab="detection">
                <i class="fa fa-search"></i> 드리프트 검출
                <div class="dropdown" id="dropdown-targetservices">
                    <ul>
                        <li data-link="/detection_cm1">성능 저하 확인을 통한 검출 예시</li>
                        <li data-link="/detection_weather">시계열 데이터 패턴 분석 예시</li>
                        <li data-link="/detection_multimodal_embedding_vector">벡터공간 데이터 분석 (고차원 임베딩)</li>
                        <li data-link="/detection_number_embedding_vector1">번호판 숫자 데이터 (단순 차원 축소)</li>
                        <li data-link="/detection_number_embedding_vector2">번호판 숫자 데이터 (UMAP, PCA)</li>
                        <li data-link="/detection_hangul_embedding_vector">번호판 한글 데이터 (UMAP, PCA)</li>

                    </ul>
                </div>
            </div>
            
            <div class="tab" data-tab="pipeline">
                <i class="fa fa-tasks"></i> 데이터 재구성 및 학습
                <div class="dropdown" id="dropdown-targetservices">
                    <ul>
                        <li data-link="/pipeline_fiftyone5151">번호판 숫자 학습셋 분석</li>
                        <li data-link="/pipeline_fiftyone5152">번호판 한글 학습셋 분석</li>
                    </ul>
                </div>
            </div>
            
            <div class="tab" data-tab="deployment">
                <i class="fa fa-paper-plane"></i> 능동적 배포
                <div class="dropdown" id="dropdown-targetservices">
                    <ul>
                        <li data-link="https://59a01a94f8cc59fbab.gradio.live">모델 및 서비스 배포</li>
                        <!--
                        <li data-link="http://keticmr.iptime.org:22080/getip.php">test</li>
                        -->
                    </ul>
                </div>
            </div>
            
            <div class="tab" data-tab="demo">
                <i class="fa fa-pie-chart"></i> 배포 서비스 예시
                <div class="dropdown" id="dropdown-targetservices">
                    <ul>
                        <!--
                        <li data-link="http://datadrift.kr:5160">번호판 인식기</li>
                        -->
                        <li data-link="https://5bbe6633fcf083b9ae.gradio.live">모델 및 서비스 배포</li>

                        
                        <!--
                        <li data-link="http://keticmr.iptime.org:22080/getip.php">test</li>
                        -->
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="tabs-right">
            <div class="tab" data-tab="userinfo">
                <i class="fa fa-user"></i> {{ Auth::user()->name }}
                <div class="dropdown" id="dropdown-login">
                    <ul>
                        <li data-link="/userinfo"> 사용자 정보 </li>
                    </ul>
                </div>
            </div>

            <div class="tab" data-tab="logout">
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

        // talk 업데이트 함수
        function updateTalk(tab) {
            const talk = document.getElementById('talk-content');
            if (tab === 'home') {
                talk.textContent = '데이터 드리프트 관리 기술을 소개합니다.';
            } else if (tab === 'targetservices') {
                talk.textContent = '교통 데이터 분석 예시입니다.';
            } else if (tab === 'detection') {
                talk.textContent = '데이터 드리프트 현상을 검출하는 예시입니다.';
            } else if (tab === 'pipeline') {
                talk.textContent = '기존의 학습 데이터를 분석하여 문제점을 해결하고 데이터를 재구성합니다.';
            } else if (tab === 'deployment') {
                talk.textContent = '에지 기기와 연계하여 즉시 대응이 필요한 환경에 제작 모델과 서비스를 배포합니다.';
            } else if (tab === 'demos') {
                talk.textContent = '배포된 서비스 예시입니다.';
            } else if (tab === 'management') {
                talk.textContent = '기계학습 모델, 학습데이터, 서비스 도메인의 데이터를 지속적으로 관리하고 해결책을 제시합니다.';
            } else if (tab === 'userinfo') {
                talk.textContent = '사용자 정보';
                //loadMainContent('/login');
            } else if (tab === 'logout') {
                talk.textContent = '로그아웃';
                //loadMainContent('/logout');
            } else if (tab === 'register') {
                talk.textContent = '사용자 등록';
                //loadMainContent('/register');
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
                updateTalk(tabName);
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

    <!-- 새로 추가된 헤더 영역 -->
    <div class="talk" id="talk-content">
        데이터 드리프트 관리 기술 개발
    </div>

    <div class="footer">
        <div class="footer-item">
            <img height=45px src='images/logo/all-logo.png'></img>&nbsp;
        </div>
    </div>
    
</body>
</html>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Centered Title and Image</title>
    <script>
        
        function openNewPage() {
            // 새로운 탭 또는 창에서 특정 URL을 엽니다
            // window.open('http://datadrift.kr:5152/datasets/lpnum_dataset_merged', '_blank');
        }
        
    </script>

    <style>
        body, html {
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;  /* 수평 중앙 정렬 */
            align-items: center;      /* 수직 중앙 정렬 */
            font-family: Arial, sans-serif;
            color: white;
        }

        .container {
            text-align: center; /* 텍스트를 중앙 정렬 */
        }

        h1 {
            font-size: 25px;
            margin-bottom: 20px; /* 제목과 이미지 간격 */
        }
        
        h2 {
            font-size: 20px;
            margin-bottom: 20px; /* 제목과 이미지 간격 */
        }

        /* 이미지 액자 효과 */
        .frame {
            width: 90%;  /* 전체 너비의 90%를 차지 */
            height: 90%; /* 전체 높이의 90%를 차지 */
            padding: 20px; /* 이미지와 액자 간 여백 */
            background-color: #fff; /* 액자 내부 배경 */
            border: 15px solid #8b4513; /* 액자 테두리 */
            border-radius: 12px; /* 모서리를 둥글게 */
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2); /* 고급스러운 그림자 효과 */
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .frame_type1 {
            display: inline-block;
            padding: 10px; /* 이미지와 액자 사이 간격 */
            background-color: white; /* 액자의 배경색 */
            border: 10px solid #8b4513; /* 갈색 액자 테두리 */
            border-radius: 8px; /* 약간 둥근 모서리 */
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3); /* 그림자 효과 */
        }

        /* 이미지 스타일 */

        img {
            max-width: 70%;
            max-height: 70%;
            object-fit: contain; /* 이미지가 프레임 안에 가득 차되 비율 유지 */
            border-radius: 8px; /* 이미지 모서리도 살짝 둥글게 */
        }

        video {
            width: 100%;
            max-width: 900px; /* 비디오의 최대 너비 설정 */
            border-radius: 20px; /* 둥근 모서리 설정 */
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); /* 그림자 추가로 더욱 보기 좋게 */
        }
    </style>
</head>
<body onload="openNewPage()">

    <div class="container">
        <h1>차량번호판 분석도구 예시: 현장 상황에 따라 분석 성능 저하 발생</h1>

        <video controls autoplay muted loop>
            <source src="videos/clip_medialens.mp4" type="video/mp4">
            브라우저가 video 태그를 지원하지 않습니다.
        </video>
    </div>

</body>
</html>
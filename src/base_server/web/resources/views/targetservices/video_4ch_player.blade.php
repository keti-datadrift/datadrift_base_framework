<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Video Dashboard - 4 Channel CCTV</title>

    <!-- CCTV 스타일 그리드 적용 -->
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            width: 50%;
            height: 50%;
            background-color: #f4f4f4;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 10px;
            height: 100%;
            padding: 10px;
            box-sizing: border-box;
        }

        .video-container {
            background-color: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            border: 2px solid #2c3e50;
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.5);
            border-radius: 5px;
        }

        video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }


        .header {
            width: 100%;
            background-color: #2c3e50;
            color: white;
            height: 50px;
            padding: 1px;
            margin: 0;
            text-align: center;
        }
    </style>
</head>
    
<body>
    <!-- 대시보드 상단 -->
    <div class="header">
        <p>4 Channel CCTV Video Dashboard</p>
    </div>

    <!-- 비디오 4채널 그리드 -->
    <div class="container">
        <div class="video-container">
            <video controls autoplay muted>
                <source src="{{ $videoUrl1 }}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>

        <div class="video-container">
            <video controls autoplay muted>
                <source src="{{ $videoUrl2 }}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>

        <div class="video-container">
            <video controls autoplay muted>
                <source src="{{ $videoUrl3 }}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>

        <div class="video-container">
            <video controls autoplay muted>
                <source src="{{ $videoUrl4 }}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
    </div>

</body>
</html>
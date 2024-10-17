<?php

// app/Http/Controllers/VideoController.php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class VideoPlayController extends Controller
{
    public function showVideo()
    {
        // 원격 비디오 파일 URL을 배열로 전달
        $videoUrl1 = 'http://keticmr.iptime.org:22080/WorkDevCarAI/carai/api/web/static/20231002_follow02.mp4';
        $videoUrl2 = 'http://keticmr.iptime.org:22080/WorkDevCarAI/carai/api/web/static/20231002_follow02.mp4';
        $videoUrl3 = 'http://keticmr.iptime.org:22080/WorkDevCarAI/carai/api/web/static/20231002_follow02.mp4';
        $videoUrl4 = 'http://keticmr.iptime.org:22080/WorkDevCarAI/carai/api/web/static/20231002_follow02.mp4';

        return view('dd_targetservices/video_4ch_player', [
            'videoUrl1' => $videoUrl1,
            'videoUrl2' => $videoUrl2,
            'videoUrl3' => $videoUrl3,
            'videoUrl4' => $videoUrl4,
        ]);
    }

    public function showCCTVWithGraphs()
    {
        // 원격 비디오 파일 URL을 배열로 전달
        $videoUrl1 = 'http://keticmr.iptime.org:22080/WorkDevCarAI/carai/api/web/static/20231002_follow02.mp4';
        $videoUrl2 = 'http://keticmr.iptime.org:22080/WorkDevCarAI/carai/api/web/static/20231002_follow02.mp4';

        return view('dd_targetservices/lp_detection', [
            'videoUrl1' => $videoUrl1,
            'videoUrl2' => $videoUrl2
        ]);
    }
}
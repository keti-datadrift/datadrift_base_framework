<?php

use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| Web Routes
|--------------------------------------------------------------------------
|
| Here is where you can register web routes for your application. These
| routes are loaded by the RouteServiceProvider and all of them will
| be assigned to the "web" middleware group. Make something great!
|
*/
use Illuminate\Http\Request;
use App\Http\Controllers\IntroController;
use App\Http\Controllers\TimeSeriesController;
use App\Http\Controllers\BarChartRaceController;
use App\Http\Controllers\AnalysisController;

use App\Http\Controllers\Auth\AuthenticatedSessionController;
use App\Http\Controllers\Auth\RegisteredUserController;

//-------------------------------------------
// 로그인 로그아웃 
//-------------------------------------------

/*
// 로그인 폼 보여주기
Route::get('login', [LoginController::class, 'showLoginForm'])->name('login');

// 로그인 요청 처리
Route::post('login', [LoginController::class, 'login']);

// 로그아웃 요청 처리
Route::post('logout', [LoginController::class, 'logout'])->name('logout');

// 사용자 등록 요청 처리
Route::get('register', [RegisterController::class, 'showRegistrationForm'])->name('register');

// 사용자 등록 요청 처리
Route::post('register', [RegisterController::class, 'register']);
*/

Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'edit'])->name('profile.edit');
    Route::patch('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');
});

// 로그인 폼을 보여주는 라우트
Route::get('/login', [AuthenticatedSessionController::class, 'create'])
    ->middleware('guest')
    ->name('login');

// 로그인 처리 라우트
Route::post('/login', [AuthenticatedSessionController::class, 'store'])
    ->middleware('guest');

// 로그아웃 처리 라우트
Route::get('/logout', function () {     
    return view('intro');
});

Route::post('/logout', [AuthenticatedSessionController::class, 'destroy'])
    ->middleware('auth')
    ->name('logout');

// 사용자 등록 처리 라우트
Route::post('/register', [RegisteredUserController::class, 'store'])
    ->middleware('guest');

Route::get('/register', [RegisteredUserController::class, 'create'])
    ->middleware('guest')
    ->name('register');

// Breeze에서 제공하는 인증 라우트
require __DIR__.'/auth.php';

Route::get('/', function () {     
    return view('intro');
})->name('home');

Route::get('/intro', function () {
    return view('intro'); // 또는 대시보드 관련 Blade 템플릿
})->middleware(['auth'])->name('intro');

Route::get('/userinfo', function () {
    return view('userinfo.info1'); // 또는 대시보드 관련 Blade 템플릿
})->middleware(['auth'])->name('userinfo');

Route::get('/test', function () {
    return view('pages.test');
})->middleware(['auth'])->name('test');

Route::get('/ov1', function () {
    return view('overview.ov1');
})->middleware(['auth'])->name('ov1');

Route::get('/ov2', function () {
    return view('overview.ov2');
})->middleware(['auth'])->name('ov2');

Route::get('/ov3', function () {
    return view('overview.ov3');
})->middleware(['auth'])->name('ov3');

Route::get('/ov4', function () {
    return view('overview.ov4');
})->middleware(['auth'])->name('ov4');

Route::get('/ov5', function () {
    return view('overview.ov5');
})->middleware(['auth'])->name('ov5');

//------------------------------------
// target services
//------------------------------------

use App\Http\Controllers\VideoPlayController;
Route::get('/targetservices_overview', function () {
    return view('targetservices.overview');
})->middleware(['auth'])->name('targetservices_overview');

Route::get('/targetservices_car_detection', function () {
    return view('targetservices.car_detection');
})->middleware(['auth'])->name('targetservices_car_detection');

Route::get('/targetservices_lp_detection', [VideoPlayController::class, 'showCCTVWithGraphs'
])->middleware(['auth'])->name('targetservices_lp_detection');

Route::get('/targetservices_lp_ocr', function () {
    return view('targetservices.lp_ocr');
})->middleware(['auth'])->name('targetservices_lp_ocr');

Route::get('/targetservices_marketing', function () {
    return view('targetservices.marketing');
})->middleware(['auth'])->name('targetservices_marketing');

Route::get('/targetservices_video_4ch_player', [VideoPlayController::class, 'showVideo'
])->middleware(['auth'])->name('targetservices_video_4ch_player');

//------------------------------------
// detection
//------------------------------------

Route::get('/detection_overview', function () {
    return view('detection.overview');
})->middleware(['auth'])->name('detection_overview');

Route::get('/detection_multimodal_embedding_vector', function () {
    return view('detection.multimodal_embedding_vector');
})->middleware(['auth'])->name('detection_multimodal_embedding_vector');

Route::get('/detection_number_embedding_vector1', function () {
    return view('detection.number_embedding_vector1');
})->middleware(['auth'])->name('detection_number_embedding_vector1');

Route::get('/detection_number_embedding_vector2', function () {
    return view('detection.number_embedding_vector2');
})->middleware(['auth'])->name('detection_number_embedding_vector2');

Route::get('/detection_hangul_embedding_vector', function () {
    return view('detection.hangul_embedding_vector');
})->middleware(['auth'])->name('detection_hangul_embedding_vector');

Route::get('/detection_cm1', function () {
    return view('detection.cm1');
})->middleware(['auth'])->name('detection_cm1');

Route::get('/detection_weather', function () {
    return view('detection.weather');
})->middleware(['auth'])->name('detection_weather');

Route::get('/detection1', function () {
    return redirect('http://datadrift.kr/plotly/3d1.html');
});

Route::get('/detection2', function () {
    return redirect('http://datadrift.kr/plotly/3d2.html');
});

Route::get('/detection3', function () {
    return redirect('http://datadrift.kr/plotly/3d3.html');
});

Route::get('/detection4', function () {
    return redirect('http://datadrift.kr/plotly/3d4.html');
});

Route::get('/detection33', function () {
    return view('detection.detection3');
})->middleware(['auth'])->name('detection3');

//------------------------------------
// pipeline
//------------------------------------

Route::get('/pipeline_overview', function () {
    return redirect('http://datadrift.kr:5151/datasets/quickstart');
});

Route::get('/pipeline_fiftyone5151', function () {
    return view('pipeline.fiftyone5151');
})->middleware(['auth'])->name('pipeline_fiftyone5151');

Route::get('/pipeline_fiftyone5152', function () {
    return view('pipeline.fiftyone5152');
})->middleware(['auth'])->name('pipeline_fiftyone5152');

//------------------------------------
// deployment
//------------------------------------

Route::get('/deployment_overview', function () {
    return view('deployment.overview');
})->middleware(['auth'])->name('deployment_overview');

//------------------------------------
// deployment
//------------------------------------

Route::get('/management_overview', function () {
    return view('management.overview');
})->middleware(['auth'])->name('management_overview');

//------------------------------------
// todo
//------------------------------------

Route::get('/stats', function () {
    return view('pages.stats');
})->middleware(['auth'])->name('stats');

Route::get('/reports', function () {
    return view('pages.reports');
})->middleware(['auth'])->name('reports');

Route::get('/sales', function () {
    return view('pages.sales');
})->middleware(['auth'])->name('sales');
 
Route::get('/expenses', function () {
    return view('pages.expenses');
})->middleware(['auth'])->name('expenses');

Route::get('/settings_profile', function () {
    return view('pages.settings_profile');
})->middleware(['auth'])->name('settings_profile');

Route::get('/settings_security', function () {
    return view('pages.settings_security');
})->middleware(['auth'])->name('settings_security');

Route::get('/pages_demoui', function () {
    return view('pages.demoui');
})->middleware(['auth'])->name('pages_demoui');

Route::get('/pages_confusion1', function () {
    return view('pages.confusion1');
})->middleware(['auth'])->name('pages_confusion1');

Route::get('/pages_confusion2', function () {
    return view('pages.confusion2');
})->middleware(['auth'])->name('pages_confusion2');

Route::get('/pages_confusion3', function () {
    return view('pages.confusion3');
})->middleware(['auth'])->name('pages_confusion3');

Route::get('/pages_cm1', function () {
    return view('pages.cm1');
})->middleware(['auth'])->name('pages_cm1');

Route::get('/pages_cm2', function () {
    return view('pages.cm2');
})->middleware(['auth'])->name('pages_cm2');

Route::get('/pages_cm3', function () {
    return view('pages.cm3');
})->middleware(['auth'])->name('pages_cm3');

Route::get('/pages_cm3a', function () {
    return view('pages.cm3a');
})->middleware(['auth'])->name('pages_cm3a');

Route::get('/pages_cm4', function () {
    return view('pages.cm4');
})->middleware(['auth'])->name('pages_cm4');

Route::get('/pages_cm5', function () {
    return view('pages.cm5');
})->middleware(['auth'])->name('pages_cm5');

Route::get('/pages_map1', function () {
    return view('pages.map1');
})->middleware(['auth'])->name('pages_map1');

Route::get('/pages_map2', function () {
    return view('pages.map2');
})->name('pages_map2');

Route::get('/pages_progress1', function () {
    return view('pages.progress1');
})->name('pages_progress1');



//-------------------------------------------
// 암호로 보호할 페이지
//-------------------------------------------

use App\Http\Controllers\ProtectedController;
use App\Http\Middleware\PasswordProtected;
Route::get('/protected', [ProtectedController::class, 'index'])->middleware(PasswordProtected::class);

Route::get('/password', function () {
    return view('password');  // 암호 입력 폼을 표시
})->name('password.form');

Route::post('/password', function (Request $request) {
    $password = 'dev'; // 여기에 실제 사용할 암호를 설정

    print( $request->input('password') );
    print( $password );
    
    if ($request->input('password') === $password) {
        // 암호가 일치하면 세션에 상태 저장
        $request->session()->put('password_passed', true);
        return redirect()->intended('/intro');  // 보호된 페이지로 리다이렉트
    }

    return back()->withErrors(['password' => 'Invalid password']);
})->name('password.check');


Route::get('/docs', function () {
    return view('docs');
})->middleware(PasswordProtected::class);

Route::get('/progress1', function () {
    return view('/samples/progress1');
})->middleware(PasswordProtected::class);

Route::get('/progress2', function () {
    return view('/samples/progress2');
})->middleware(PasswordProtected::class);

Route::get('/timeseries1', function () {
    return view('/samples/timeseries1');
})->middleware(PasswordProtected::class);

Route::get('/timeseries2', function () {
    return view('/samples/timeseries2');
})->middleware(PasswordProtected::class);

Route::get('/timeseries3', function () {
    return view('/samples/timeseries3');
})->middleware(PasswordProtected::class);

Route::get('/embeddingvis', function () {
    return view('/samples/embeddingvis');
})->middleware(PasswordProtected::class);

Route::get('/double_histogram', function () {
    return view('/samples/double_histogram');
})->middleware(PasswordProtected::class);

Route::get('/ridgeline', function () {
    return view('/samples/ridgeline');
})->middleware(PasswordProtected::class);

Route::get('/histogram1', function () {
    return view('/samples/histogram1');
})->middleware(PasswordProtected::class);

Route::get('/histogram2', function () {
    return view('/samples/histogram2');
})->middleware(PasswordProtected::class);

Route::get('/confusion1', function () {
    return view('/samples/confusion1');
})->middleware(PasswordProtected::class);

Route::get('/sankey', function () {
    return view('/samples/sankey');
})->middleware(PasswordProtected::class);

Route::get('/sankey_jpark1', function () {
    return view('/samples/sankey_jpark1');
})->middleware(PasswordProtected::class);

Route::get('/flare', function () {
    return view('/samples/flare');
})->middleware(PasswordProtected::class);

Route::get('/map1', function () {
    return view('/samples/map1');
})->middleware(PasswordProtected::class);

Route::get('/map2', function () {
    return view('/samples/map2');
})->middleware(PasswordProtected::class);

Route::get('/map3', function () {
    return view('/samples/map3');
})->middleware(PasswordProtected::class);

Route::get('/map4', function () {
    return view('/samples/map4');
})->middleware(PasswordProtected::class);

Route::get('/map5', function () {
    return view('/samples/map5');
})->middleware(PasswordProtected::class);

Route::get('/weather1', function () {
    return view('/samples/weather1');
})->middleware(PasswordProtected::class);

Route::get('/wolframstyle1', function () {
    return view('/samples/wolframstyle1');
})->middleware(PasswordProtected::class);

Route::post('/analyses/search', [AnalysisController::class, 'search']);  // 검색을 위한 라우트 추가
Route::get('/wolframstyle2', [AnalysisController::class, 'wolframstyle2']);
Route::get('/wolframstyle3', [AnalysisController::class, 'wolframstyle3']);
Route::get('/wolframstyle4', [AnalysisController::class, 'wolframstyle4']); 

Route::post('/analyses/search_wolframstyle5', [AnalysisController::class, 'search_wolframstyle5']);
Route::get('/wolframstyle5', [AnalysisController::class, 'wolframstyle5']);


Route::get('/intro_controller', [IntroController::class, 'showIntro']);
Route::get('/api/time-series', [TimeSeriesController::class, 'index']);
Route::get('/bar-chart-race', [BarChartRaceController::class, 'index']);
Route::get('/api/bar-chart-race-data', [BarChartRaceController::class, 'getData']);



//-------------------------------------------
// 업로드 테스트
//-------------------------------------------


// upload
//use App\Http\Controllers\UploadController;
//Route::post('/upload', [UploadController::class, 'upload'])->name('upload');
//Route::post('/upload', [UploadController::class, 'upload'])->name('upload');
//Route::get('/upload', function () {
//    return view('upload');
//});

use App\Http\Controllers\ZipController;
Route::get('/zipupload', [ZipController::class, 'index']);
Route::post('/upload', [ZipController::class, 'upload']);


//-------------------------------------------
// 그라파나 연동 페이지, 암호로 보호할 페이지
//-------------------------------------------

Route::get('/g/metrics', function () {
    return view('/grafana/metrics');
})->middleware(PasswordProtected::class);
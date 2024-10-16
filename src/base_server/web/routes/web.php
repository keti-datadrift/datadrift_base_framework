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


Route::get('/intro_controller', [IntroController::class, 'showIntro']);
Route::get('/api/time-series', [TimeSeriesController::class, 'index']);
Route::get('/bar-chart-race', [BarChartRaceController::class, 'index']);
Route::get('/api/bar-chart-race-data', [BarChartRaceController::class, 'getData']);

//-------------------------------------------
// 암호 입력
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


//-------------------------------------------
// 업로드 테스트
//-------------------------------------------


// upload
//use App\Http\Controllers\UploadController;
//Route::post('/upload', [UploadController::class, 'upload'])->name('upload');
//Route::post('/upload', [UploadController::class, 'upload'])->name('upload');
//Route::get('/dd_upload', function () {
//    return view('dd_upload');
//});

use App\Http\Controllers\ZipController;
Route::get('/zipupload', [ZipController::class, 'index']);
Route::post('/upload', [ZipController::class, 'upload']);

//-------------------------------------------
// 암호로 보호할 페이지
//-------------------------------------------

Route::get('/', function () {
    return view('intro');
})->middleware(PasswordProtected::class);

Route::get('/chart', function () {
    return view('chart');
})->middleware(PasswordProtected::class);

Route::get('/introview', function () {
    return view('intro');
})->middleware(PasswordProtected::class);

Route::get('/intro', function () {     
    return 'Data Drift 시연 페이지'; 
})->middleware(PasswordProtected::class);

Route::get('/dashboard', function () {
    return view('dashboard');
})->middleware(PasswordProtected::class);

Route::get('/reports', function () {
    return view('reports');
})->middleware(PasswordProtected::class);

Route::get('/settings', function () {
    return view('settings');
})->middleware(PasswordProtected::class);

Route::get('/docs', function () {
    return view('docs');
})->middleware(PasswordProtected::class);


Route::get('/dd_progress1', function () {
    return view('/samples/dd_progress1');
})->middleware(PasswordProtected::class);

Route::get('/dd_progress2', function () {
    return view('/samples/dd_progress2');
})->middleware(PasswordProtected::class);

Route::get('/dd_timeseries1', function () {
    return view('/samples/dd_timeseries1');
})->middleware(PasswordProtected::class);

Route::get('/dd_timeseries2', function () {
    return view('/samples/dd_timeseries2');
})->middleware(PasswordProtected::class);

Route::get('/dd_timeseries3', function () {
    return view('/samples/dd_timeseries3');
})->middleware(PasswordProtected::class);

Route::get('/dd_embeddingvis', function () {
    return view('/samples/dd_embeddingvis');
})->middleware(PasswordProtected::class);

Route::get('/dd_double_histogram', function () {
    return view('/samples/dd_double_histogram');
})->middleware(PasswordProtected::class);

Route::get('/dd_ridgeline', function () {
    return view('/samples/dd_ridgeline');
})->middleware(PasswordProtected::class);

Route::get('/dd_histogram1', function () {
    return view('/samples/dd_histogram1');
})->middleware(PasswordProtected::class);

Route::get('/dd_histogram2', function () {
    return view('/samples/dd_histogram2');
})->middleware(PasswordProtected::class);

Route::get('/dd_confusion1', function () {
    return view('/samples/dd_confusion1');
})->middleware(PasswordProtected::class);

Route::get('/dd_sankey', function () {
    return view('/samples/dd_sankey');
})->middleware(PasswordProtected::class);

Route::get('/dd_sankey_jpark1', function () {
    return view('/samples/dd_sankey_jpark1');
})->middleware(PasswordProtected::class);

Route::get('/dd_flare', function () {
    return view('/samples/dd_flare');
})->middleware(PasswordProtected::class);

Route::get('/dd_map1', function () {
    return view('/samples/dd_map1');
})->middleware(PasswordProtected::class);

Route::get('/dd_map2', function () {
    return view('/samples/dd_map2');
})->middleware(PasswordProtected::class);

Route::get('/dd_map3', function () {
    return view('/samples/dd_map3');
})->middleware(PasswordProtected::class);

Route::get('/dd_map4', function () {
    return view('/samples/dd_map4');
})->middleware(PasswordProtected::class);

Route::get('/dd_map5', function () {
    return view('/samples/dd_map5');
})->middleware(PasswordProtected::class);

Route::get('/dd_weather1', function () {
    return view('/samples/dd_weather1');
})->middleware(PasswordProtected::class);

Route::get('/dd_wolframstyle1', function () {
    return view('/samples/dd_wolframstyle1');
})->middleware(PasswordProtected::class);

Route::post('/analyses/search', [AnalysisController::class, 'search']);  // 검색을 위한 라우트 추가
Route::get('/dd_wolframstyle2', [AnalysisController::class, 'dd_wolframstyle2']);
Route::get('/dd_wolframstyle3', [AnalysisController::class, 'dd_wolframstyle3']);
Route::get('/dd_wolframstyle4', [AnalysisController::class, 'dd_wolframstyle4']); 

Route::post('/analyses/search_wolframstyle5', [AnalysisController::class, 'search_wolframstyle5']);
Route::get('/dd_wolframstyle5', [AnalysisController::class, 'dd_wolframstyle5']);

//-------------------------------------------
// 그라파나 연동 페이지, 암호로 보호할 페이지
//-------------------------------------------

Route::get('/g/metrics', function () {
    return view('/grafana/metrics');
})->middleware(PasswordProtected::class);
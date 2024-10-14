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

Route::get('/', function () {
    return view('hello');
});

Route::get('/welcome', function () {
    return view('welcome');
});

Route::get('/helloview', function () {
    return view('hello');
});

Route::get('/hello', function () {     return 'Hello World (JPark)'; });

use App\Http\Controllers\HelloWorldController;
Route::get('/hellocontrol', [HelloWorldController::class, 'showHello']);

use App\Http\Controllers\TimeSeriesController;
Route::get('/api/time-series', [TimeSeriesController::class, 'index']);

Route::get('/chart', function () {
    return view('chart');
});

use App\Http\Controllers\BarChartRaceController;

Route::get('/bar-chart-race', [BarChartRaceController::class, 'index']);
Route::get('/api/bar-chart-race-data', [BarChartRaceController::class, 'getData']);

//-------------------------------------------
// 암호 입력
//-------------------------------------------
use Illuminate\Http\Request;

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
        return redirect()->intended('/chart');  // 보호된 페이지로 리다이렉트
    }

    return back()->withErrors(['password' => 'Invalid password']);
})->name('password.check');



//-------------------------------------------
// 암호로 보호할 페이지
//-------------------------------------------

use App\Http\Controllers\ProtectedController;
use App\Http\Middleware\PasswordProtected;

Route::get('/protected', [ProtectedController::class, 'index'])->middleware(PasswordProtected::class);

Route::get('/chart', function () {
    return view('chart');
})->middleware(PasswordProtected::class);

Route::get('/d3chart', function () {
    return view('d3chart');
})->middleware(PasswordProtected::class);

Route::get('/dd_progress', function () {
    return view('dd_progress');
})->middleware(PasswordProtected::class);

Route::get('/dd_embeddingvis', function () {
    return view('dd_embeddingvis');
})->middleware(PasswordProtected::class);


// upload
use App\Http\Controllers\UploadController;
//Route::post('/upload', [UploadController::class, 'upload'])->name('upload');
Route::post('/upload', [UploadController::class, 'upload'])->name('upload')->middleware('auth');

Route::get('/upload', function () {
    return view('upload');
});






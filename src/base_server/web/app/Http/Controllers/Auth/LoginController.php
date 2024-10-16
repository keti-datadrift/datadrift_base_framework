<?php

namespace App\Http\Controllers\Auth;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class LoginController extends Controller
{
    // 로그인 폼 보여주기
    public function showLoginForm()
    {
        return view('auth.login');
    }

    // 로그인 처리
    public function login(Request $request)
    {
        $credentials = $request->only('email', 'password');

        if (Auth::attempt($credentials)) {
            // 인증 성공, 대시보드로 리디렉션
            return redirect()->intended('dashboard');
        }

        // 인증 실패, 로그인 페이지로 다시 리디렉션
        return back()->withErrors([
            'email' => 'The provided credentials do not match our records.',
        ]);
    }

    // 로그아웃 처리
    public function logout(Request $request)
    {
        Auth::logout();

        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return redirect('/');
    }
}
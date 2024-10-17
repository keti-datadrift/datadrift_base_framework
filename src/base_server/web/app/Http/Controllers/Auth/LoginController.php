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
            // 인증 성공, 리디렉션
            return redirect()->intended('intro');
        }

        // 로그인 실패, 다시 로그인 페이지로 리디렉션하면서 오류 메시지 전달
        return redirect()->back()
            ->withInput($request->only('email'))  // 이메일 필드만 유지
            ->withErrors([
                'email' => 'The provided credentials do not match our records.',
        ]);
    }

    // 로그아웃 처리
    public function logout(Request $request)
    {
        Auth::logout();

        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return redirect('/intro');
    }
}
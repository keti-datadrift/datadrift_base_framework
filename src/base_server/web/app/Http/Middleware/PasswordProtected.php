<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class PasswordProtected
{
    /**
     * Handle an incoming request.
     *
     * @param  \Closure(\Illuminate\Http\Request): (\Symfony\Component\HttpFoundation\Response)  $next
     */
    public function handle(Request $request, Closure $next)
    {
        // 세션에 password_passed가 없는 경우 또는 false인 경우 암호 페이지로 리다이렉트
        if (!$request->session()->has('password_passed') || !$request->session()->get('password_passed')) {
            return redirect()->route('password.form');
        }

        return $next($request);
    }
}

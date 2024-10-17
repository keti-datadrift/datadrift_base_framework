<?php

namespace App\Http\Controllers\Auth;

use App\Http\Controllers\Controller;
use App\Models\User;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Validator;
use Illuminate\Foundation\Auth\RegistersUsers;

class RegisterController extends Controller
{
    use RegistersUsers;

    // 사용자가 회원가입 후 리디렉션될 경로
    protected $redirectTo = '/intro';

    public function __construct()
    {
        $this->middleware('guest');
    }

    // 유효성 검사
    protected function validator(array $data)
    {
        return Validator::make($data, [
            'name' => ['required', 'string', 'max:255'],
            'email' => ['required', 'string', 'email', 'max:255', 'unique:users'],
            'password' => ['required', 'string', 'min:8', 'confirmed'],
        ]);
    }

    // 사용자 등록 폼을 보여주는 메서드
    public function showRegistrationForm()
    {
        return view('auth.register'); // 이 메서드가 회원가입 폼을 반환합니다.
    }
    
    // 사용자 생성
    protected function create(array $data)
    {
        return User::create([
            'name' => $data['name'],
            'email' => $data['email'],
            'password' => Hash::make($data['password']),
        ]);
    }
}
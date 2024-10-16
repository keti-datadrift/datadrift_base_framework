# 라라벨에서 로그인/로그아웃 기능 구현

- npm 설치 하지 않고 진행

## 절차 및 내용

Breeze의 간단한 인증 시스템을 구성하려면 Vue.js나 React.js와 같은 프론트엔드 자바스크립트 프레임워크를 사용하지 않고 Blade 템플릿 기반으로 설치하는 방법을 사용할 수 있습니다. 이 방법은 npm을 사용하지 않으며, 간단한 방식으로 인증을 설정합니다.

다음은 Laravel Breeze를 올바르게 설치하고, 간단하게 로그인/로그아웃 기능을 구현하는 단계입니다.

1. Breeze 설치

먼저 Laravel Breeze 패키지를 설치합니다.

composer require laravel/breeze --dev

2. Breeze 설치 명령어 실행 (Blade 기반)

Vue.js나 React.js를 사용하지 않고, Blade 템플릿 기반의 간단한 인증 시스템을 설치하려면 다음 명령어를 사용합니다.

php artisan breeze:install

이 명령어는 기본적으로 Blade 템플릿을 사용하는 인증 시스템을 설정해줍니다.

3. 마이그레이션 실행

Breeze가 설치된 후, 데이터베이스 테이블을 설정하기 위해 마이그레이션을 실행합니다.

php artisan migrate

4. CSS 및 자바스크립트 빌드 (선택사항)

기본적으로 Breeze는 Tailwind CSS와 함께 동작하므로, 스타일링이 필요하지 않다면 이 단계는 생략해도 됩니다. 하지만 스타일링을 적용하려면 npm을 사용하여 필요한 자산을 빌드해야 합니다.

npm install && npm run dev

이 명령어를 통해 Tailwind CSS가 빌드되고, Breeze의 기본적인 스타일링이 적용됩니다. npm을 사용하지 않으려면 이 단계는 생략할 수 있지만, 스타일링은 직접 추가해야 합니다.

5. 라우팅 설정 (routes/web.php)

Breeze는 인증 관련 라우트를 자동으로 설정합니다. routes/web.php 파일에 기본적인 라우팅과 Breeze의 인증 라우트를 추가합니다.

use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('welcome');
});

// Breeze에서 제공하는 인증 라우트
require __DIR__.'/auth.php';

6. 로그인, 회원가입 페이지 설정

Breeze가 설치되면 resources/views/auth/ 디렉토리에 로그인 및 회원가입 페이지가 자동으로 생성됩니다. 이 페이지들은 Laravel의 기본 레이아웃을 사용해 자동으로 Blade 템플릿을 렌더링합니다.

로그인 페이지 (resources/views/auth/login.blade.php)

@extends('layouts.app')

@section('title', 'Login')

@section('content')
    <h2>Login</h2>

    @if($errors->any())
        <div>
            <p>{{ $errors->first() }}</p>
        </div>
    @endif

    <form method="POST" action="{{ route('login') }}">
        @csrf
        <div>
            <label for="email">Email:</label>
            <input id="email" type="email" name="email" value="{{ old('email') }}" required autofocus>
        </div>
        <div>
            <label for="password">Password:</label>
            <input id="password" type="password" name="password" required>
        </div>
        <div>
            <button type="submit">Login</button>
        </div>
    </form>
@endsection

회원가입 페이지 (resources/views/auth/register.blade.php)

@extends('layouts.app')

@section('title', 'Register')

@section('content')
    <h2>Register</h2>

    @if($errors->any())
        <div>
            <p>{{ $errors->first() }}</p>
        </div>
    @endif

    <form method="POST" action="{{ route('register') }}">
        @csrf
        <div>
            <label for="name">Name:</label>
            <input id="name" type="text" name="name" value="{{ old('name') }}" required autofocus>
        </div>
        <div>
            <label for="email">Email:</label>
            <input id="email" type="email" name="email" value="{{ old('email') }}" required>
        </div>
        <div>
            <label for="password">Password:</label>
            <input id="password" type="password" name="password" required>
        </div>
        <div>
            <label for="password_confirmation">Confirm Password:</label>
            <input id="password_confirmation" type="password" name="password_confirmation" required>
        </div>
        <div>
            <button type="submit">Register</button>
        </div>
    </form>
@endsection

결론

Laravel Breeze를 사용하여 Blade 기반의 간단한 로그인/로그아웃 기능을 구현할 때는, --simple 옵션을 사용하는 대신, 기본 설치 명령어인 php artisan breeze:install을 사용하면 됩니다. 이 방식으로 로그인, 회원가입, 로그아웃, 비밀번호 재설정 등 모든 인증 기능을 간편하게 설정할 수 있습니다.

npm을 사용하지 않더라도 Breeze는 Blade 템플릿만으로 작동하며, 간단한 인증 시스템을 빠르게 구현할 수 있습니다.
# laravel hello world

- 참고 문헌 : https://medium.com/novai-php-laravel-101/building-a-hello-world-web-application-with-laravel-72c650599a3f
- 수정 : JPark @ KETI, 2024

## Quick Start

- 서버 실행

```bash
composer create-project --prefer-dist laravel/laravel web
cd web
php -S 0.0.0.0:8000 -t public # or php artisan serve
# open http://localhost:8000
```

- http://localhost:8000/hello 추가

```bash
vi routes/web.php
vi resources/views/hello.blade.php
```

- http://localhost:8000/hello 컨트롤러로 추가

```bash
php artisan make:controller HelloWorldController
```

- controller 내용

vi app/Http/Controllers/HelloWorldController.php

```bash
<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;

class HelloWorldController extends Controller
{
    public function showHello()
    {
        return view('hello');
    }
}
```



```
# 문제 해결

## /storage/logs 접근 오류

- run_clear_cache.sh 실행하여 캐시 정리

```bash
docker compose run app rm -rf bootstrap/cache/*.php
docker compose run app php artisan config:clear

echo "recreate cache"
docker compose run app php artisan config:cache
```


## {{ Auth::user()->name }} 오류


Laravel에서 발생하는 “Attempt to read property ‘name’ on null” 오류는 주로 null 값을 가진 객체에서 속성을 읽으려 할 때 발생합니다. 이 오류는 대개 인증되지 않은 사용자가 로그인된 사용자 정보에 접근하려 할 때 발생합니다. 예를 들어, Auth::user()가 null을 반환하는데, 그 객체의 name 속성에 접근하려 할 때 이 오류가 발생합니다.

1. 문제의 원인

대개 두 가지 상황에서 이 문제가 발생합니다:

	•	사용자가 로그인되지 않은 상태에서 Auth::user()->name과 같은 코드를 실행하려고 했을 때.
	•	데이터베이스에서 찾으려는 값이 없어서 반환된 결과가 null인 경우.

예시:

{{ Auth::user()->name }}

이 코드는 사용자가 로그인된 경우에만 정상적으로 작동합니다. 하지만 로그인되지 않은 경우 Auth::user()는 null을 반환하므로, null 객체에서 name 속성을 읽으려 할 때 오류가 발생합니다.

2. 해결 방법

1) 사용자가 인증되었는지 확인하기 (Auth::check())

사용자가 로그인된 상태에서만 Auth::user()에 접근하도록 조건을 추가해야 합니다.

@if (Auth::check())
    <span>{{ Auth::user()->name }}</span>
@else
    <span>Guest</span>
@endif

	•	Auth::check()는 사용자가 인증된 상태인지를 확인합니다. 인증된 경우에만 Auth::user()에 접근하도록 조건을 설정해 줍니다.

2) Blade 디렉티브 사용하기

Blade 템플릿에서는 @auth 및 @guest 지시어를 사용하여 인증된 사용자와 비인증 사용자를 구분할 수 있습니다.

@auth
    <!-- 사용자가 로그인한 경우에만 표시 -->
    <span>{{ Auth::user()->name }}</span>
@endauth

@guest
    <!-- 로그인하지 않은 사용자에게 표시 -->
    <span>Guest</span>
@endguest

	•	@auth: 사용자가 로그인된 경우에만 실행됩니다.
	•	@guest: 사용자가 로그인되지 않은 경우에만 실행됩니다.

3) null 값을 체크하기

Auth::user()가 null인지 확인하고, null이 아닌 경우에만 name 속성에 접근하는 방법입니다.

{{ optional(Auth::user())->name ?? 'Guest' }}

	•	optional(Auth::user()): Auth::user()가 null일 경우 오류를 방지하고, null이 아니면 name 속성에 안전하게 접근할 수 있습니다.
	•	?? 'Guest': name이 없을 경우 “Guest”라는 기본값을 출력합니다.

3. 데이터베이스 조회 시 발생하는 경우

데이터베이스에서 조회한 값이 null일 때 이 오류가 발생할 수도 있습니다. 예를 들어, find() 메서드로 모델을 조회했을 때 값이 없는 경우에도 이 오류가 발생할 수 있습니다.

$user = User::find($id);

if ($user) {
    echo $user->name;
} else {
    echo "User not found";
}

여기서, $user가 null인지 확인한 후에 name 속성에 접근해야 합니다.

결론

	•	로그인 상태 확인: Auth::check() 또는 Blade 템플릿의 @auth, @guest 지시어를 사용해 로그인 여부를 확인합니다.
	•	null 값 처리: optional()을 사용하여 안전하게 null 값을 처리하거나 조건문을 사용하여 null 여부를 확인합니다.
	•	데이터베이스 조회 시 체크: 데이터베이스에서 조회한 객체가 null일 가능성을 고려하여 이를 처리합니다.

이 과정을 통해 “Attempt to read property ‘name’ on null” 오류를 해결할 수 있을 것입니다.

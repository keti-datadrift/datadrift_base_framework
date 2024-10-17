<x-guest-layout>
    <!-- 로그아웃 버튼 -->
    <form id="logout-form" action="{{ route('logout') }}" method="POST">
        @csrf
        <button type="submit">Logout</button>
    </form>

    <script>
        document.querySelector('#logout-form').addEventListener('submit', function(event) {
            event.preventDefault();  // 기본 폼 제출 동작을 방지
            var form = this;

            var formData = new FormData(form);

            fetch(form.action, {
                method: 'POST',
                body: formData
            }).then(response => {
                if (response.ok) {
                    // 로그아웃 성공 후 부모 페이지(상위 프레임)를 새로고침
                    window.top.location.reload();  // 상위 페이지 새로고침
                } else {
                    // 실패한 경우 로그아웃 실패 처리
                    console.log('Logout failed');
                }
            }).catch(error => {
                console.error('Error:', error);
            });
        });
    </script>
</x-guest-layout>
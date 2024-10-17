# Fiftyone Reverse Proxy

proxy_set_header Access-Control-Allow-Origin *;와 관련된 CORS 설정은, 클라이언트가 서버로 요청을 보낼 때 발생할 수 있는 교차 출처 리소스 공유(CORS) 문제를 해결하는 데 사용됩니다. 이 헤더들은 클라이언트가 서버에서 자원을 가져올 수 있도록 허용하는 역할을 하며, CORS 오류를 방지합니다.

이 코드는 클라이언트의 요청이 프록시를 통해서 서버로 전달될 때 해당 헤더가 설정되어야 하므로, NGINX의 리버스 프록시 설정에서 각 요청 경로에 대해 적용되어야 합니다.

위치:

이 CORS 관련 헤더는 리버스 프록시가 적용되는 모든 요청 경로에 설정되어야 합니다. 보통 기본 경로(/), 정적 파일 경로(/assets/), API 경로(/api/), WebSocket 경로(/events) 등에 적용합니다.

수정된 nginx/default.conf 예시

아래는 CORS 설정을 포함한 NGINX 설정 파일의 예시입니다:

server {
    listen 80;

    # 기본 요청 처리 (fiftyone 프록시)
    location / {
        proxy_pass http://fiftyone_server:5151;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
        proxy_cache_bypass $http_upgrade;

        # CORS 설정
        proxy_set_header Access-Control-Allow-Origin *;
        proxy_set_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        proxy_set_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept";
    }

    # WebSocket을 위한 /events 경로
    location /events {
        proxy_pass http://fiftyone_server:5151/events;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_buffering off;

        # CORS 설정
        proxy_set_header Access-Control-Allow-Origin *;
        proxy_set_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        proxy_set_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept";
    }

    # 정적 파일 (assets) 처리
    location /assets/ {
        proxy_pass http://fiftyone_server:5151/assets/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;

        # CORS 설정
        proxy_set_header Access-Control-Allow-Origin *;
        proxy_set_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        proxy_set_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept";
    }

    # API 요청 처리
    location /api/ {
        proxy_pass http://fiftyone_server:5151/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;

        # CORS 설정
        proxy_set_header Access-Control-Allow-Origin *;
        proxy_set_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        proxy_set_header Access-Control-Allow-Headers "Origin, X-Requested-With, Content-Type, Accept";
    }
}

설명:

	1.	CORS 설정 추가 위치:
	•	location / {}, location /events {}, location /assets/ {}, location /api/ {}: 각 경로에 대해 CORS 헤더를 설정하여, 해당 경로로 들어오는 모든 요청에서 교차 출처 자원 공유(CORS) 문제가 발생하지 않도록 처리합니다.
	2.	proxy_set_header Access-Control-Allow-Origin *;:
	•	모든 도메인에서 요청을 허용하도록 설정합니다. 특정 도메인에서만 요청을 허용하려면, * 대신 해당 도메인을 입력할 수 있습니다. 예를 들어, Access-Control-Allow-Origin https://example.com;와 같이 설정합니다.
	3.	Access-Control-Allow-Methods:
	•	서버가 허용하는 HTTP 메서드를 정의합니다. 예시에서는 GET, POST, OPTIONS 메서드가 허용됩니다. 필요한 메서드가 더 있다면 추가할 수 있습니다.
	4.	Access-Control-Allow-Headers:
	•	클라이언트가 서버로 요청할 때 사용할 수 있는 HTTP 헤더를 정의합니다.

1. CORS 설정이 필요한 이유

브라우저는 기본적으로 교차 출처 요청을 허용하지 않습니다. 즉, 클라이언트가 다른 도메인 또는 포트로 요청을 보낼 때, 서버가 해당 요청을 명시적으로 허용해야만 브라우저에서 정상적으로 요청이 처리됩니다. NGINX에서 프록시를 통해 서버로 요청이 전달될 때도 동일한 CORS 문제가 발생할 수 있으므로, 이를 해결하기 위해 각 요청 경로에 대해 Access-Control-Allow-Origin 헤더 등을 설정해야 합니다.

2. 실행

NGINX 설정 파일을 수정한 후, Docker Compose로 NGINX를 다시 빌드 및 실행합니다.

docker-compose up --build

3. NGINX 로그 확인

CORS 문제나 다른 문제가 여전히 발생하는지 확인하려면, NGINX의 로그를 확인할 수 있습니다.

docker logs nginx_proxy

이렇게 설정하면 CORS 문제가 해결되고, 외부에서 클라이언트가 서버로 정상적으로 요청을 보낼 수 있습니다.
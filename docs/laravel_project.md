# laravel 기반 프로젝트를 컨테이너로 만들기

- JPark and ChatGPT, 2024-10-11

## composer로 생성한 Laravel 프로젝터를 docker로 패키징 하기

Composer를 사용해서 생성된 Laravel 프로젝트는 Docker로 패키징할 수 있습니다.
Laravel 프로젝트는 다양한 폴더와 파일을 포함하고 있지만, 이를 적절히 Docker로 패키징하고 Docker Compose를 사용하여 실행할 수 있습니다. 
패키징 과정은 프로젝트의 구조를 고려하여 Dockerfile과 Docker Compose 파일을 작성하는 방식으로 이루어집니다.

1. Laravel 프로젝트 구조

Laravel을 Composer로 설치하면 다음과 같은 폴더와 파일이 생성됩니다:

	•	app/: 애플리케이션 로직이 포함된 폴더
	•	bootstrap/: 애플리케이션 부트스트랩 파일이 포함된 폴더
	•	config/: 애플리케이션 설정 파일
	•	database/: 데이터베이스 마이그레이션 및 시드 파일
	•	public/: 웹 서버에 의해 제공되는 웹 문서의 루트 디렉토리
	•	resources/: 뷰 템플릿, 언어 파일, 자산 파일 등을 포함
	•	routes/: 라우팅 정의 파일
	•	storage/: 로그 파일, 캐시 파일, 세션 등이 저장
	•	vendor/: Composer 패키지들이 설치되는 디렉터리
	•	.env: 환경 설정 파일

2. Docker로 패키징하는 방법

Laravel 프로젝트를 Docker로 패키징하려면 다음 단계가 필요합니다:

2.1. Dockerfile 작성

Dockerfile을 프로젝트 루트에 작성하여 Laravel 애플리케이션을 PHP-FPM 기반으로 패키징합니다.

# Dockerfile

# PHP-FPM 기반 이미지 사용
FROM php:8.1-fpm

# 필요한 PHP 확장 설치
RUN apt-get update && apt-get install -y \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    zip \
    unzip \
    git \
    curl \
    && docker-php-ext-install pdo_mysql mbstring gd

# Composer 설치
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# 작업 디렉토리 설정
WORKDIR /var/www

# Laravel 프로젝트 복사
COPY . /var/www

# 권한 설정
RUN chown -R www-data:www-data /var/www

# 의존성 설치
RUN composer install --no-dev --optimize-autoloader

# Laravel 설정 캐싱 (선택 사항)
RUN php artisan config:cache && php artisan route:cache

# 권한 수정
RUN chmod -R 777 storage bootstrap/cache

# PHP-FPM 실행
CMD ["php-fpm"]

2.2. Docker Compose 설정

Laravel 애플리케이션과 데이터베이스(MariaDB)를 함께 실행할 수 있도록 docker-compose.yml 파일을 작성합니다.

version: '3.8'

services:
  # Laravel 애플리케이션
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: laravel-app
    volumes:
      - .:/var/www
    networks:
      - laravel

  # Nginx 웹 서버
  web:
    image: nginx:latest
    container_name: laravel-nginx
    volumes:
      - .:/var/www
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
    ports:
      - "8000:80"
    depends_on:
      - app
    networks:
      - laravel

  # MariaDB 데이터베이스
  db:
    image: mariadb:latest
    container_name: laravel-mariadb
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: laravel_db
      MYSQL_USER: laravel_user
      MYSQL_PASSWORD: laravel_password
    volumes:
      - dbdata:/var/lib/mysql
    networks:
      - laravel

networks:
  laravel:
    driver: bridge

volumes:
  dbdata:
    driver: local

2.3. Nginx 설정 파일 작성

nginx/default.conf 파일을 만들어 Nginx의 설정을 정의합니다.

server {
    listen 80;
    server_name localhost;
    root /var/www/public;

    index index.php index.html;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass app:9000;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    location ~ /\.ht {
        deny all;
    }
}

2.4. 환경설정 파일 수정

Laravel의 .env 파일에서 데이터베이스 설정을 Docker Compose 파일과 일치하도록 수정합니다.

DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE=laravel_db
DB_USERNAME=laravel_user
DB_PASSWORD=laravel_password

3. Docker Compose 실행

아래 명령어를 실행하여 Docker Compose로 Laravel 애플리케이션과 MariaDB 컨테이너를 실행할 수 있습니다.

docker-compose up -d

이제 http://localhost:8000에서 애플리케이션을 확인할 수 있으며, 애플리케이션의 데이터베이스는 MariaDB에 연결되어 있습니다.

4. 마이그레이션 및 권한 설정

Laravel 애플리케이션 컨테이너에 접속하여 데이터베이스 마이그레이션을 수행하고 권한을 설정합니다.

docker-compose exec app bash
php artisan migrate
chmod -R 777 storage bootstrap/cache

결론

Laravel 프로젝트의 많은 폴더와 파일을 Docker로 패키징하는 것은 가능합니다. 
Dockerfile과 Docker Compose를 적절히 구성하면 Laravel 애플리케이션과 데이터베이스를 손쉽게 컨테이너 환경에서 실행할 수 있습니다. 
이를 통해 개발, 테스트, 배포 과정을 간소화할 수 있습니다.

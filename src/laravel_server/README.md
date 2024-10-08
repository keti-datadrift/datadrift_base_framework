# laravel 기반 서버

이 프로젝트는 PHP-FPM, Nginx, MariaDB를 포함한 Laravel 애플리케이션을 컨테이너에서 실행합니다.

1. 프로젝트 구조

우선 프로젝트 폴더 구조는 다음과 같습니다.

simple-board/
├── app/                # Laravel Application Code
├── docker-compose.yml   # Docker Compose Configuration
├── Dockerfile           # Laravel Dockerfile
├── nginx/
│   └── default.conf     # Nginx Configuration
└── .env                 # Laravel Environment Configuration

2. Dockerfile 작성

Dockerfile을 프로젝트 루트 디렉터리에 생성하고, Laravel 애플리케이션을 위한 PHP 환경을 설정합니다.

# Dockerfile

FROM php:8.2-fpm

# 작업 디렉토리 설정
WORKDIR /var/www

# 필요한 PHP 확장 설치
RUN apt-get update && apt-get install -y \
    libpng-dev \
    libonig-dev \
    libxml2-dev \
    zip \
    unzip \
    git \
    curl \
    && docker-php-ext-install pdo pdo_mysql mbstring exif pcntl bcmath gd

# Composer 설치
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# 권한 수정
RUN chown -R www-data:www-data /var/www

# Laravel 프로젝트 복사
COPY . /var/www

# Composer로 의존성 설치
RUN composer install --no-scripts --no-autoloader && \
    composer dump-autoload

EXPOSE 9000
CMD ["php-fpm"]

3. Nginx 설정 파일 작성

nginx/default.conf 파일을 생성해 Nginx 설정을 작성합니다.

server {
    listen 80;
    index index.php index.html;
    server_name localhost;
    root /var/www/public;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass app:9000;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}

4. Docker Compose 설정 작성

docker-compose.yml 파일을 생성하여 서비스들을 정의합니다.

version: '3.8'

services:
  # Laravel 애플리케이션 (PHP-FPM)
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

5. .env 파일 설정

.env 파일에서 데이터베이스 설정을 MariaDB에 맞게 수정합니다.

DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE=laravel_db
DB_USERNAME=laravel_user
DB_PASSWORD=laravel_password

6. Docker Compose 실행

프로젝트 폴더 내에서 docker-compose up 명령어를 실행하여 컨테이너를 실행합니다.

docker-compose up -d

7. 마이그레이션 및 권한 설정

컨테이너가 실행되면, 애플리케이션 컨테이너 안에 들어가서 Laravel의 마이그레이션을 실행해야 합니다.

docker-compose exec app bash
php artisan migrate

또한, storage와 bootstrap/cache 디렉토리에 대한 권한을 설정합니다.

chmod -R 777 storage
chmod -R 777 bootstrap/cache

8. 웹사이트 접속

웹 브라우저에서 http://localhost:8000에 접속하면 Laravel 애플리케이션이 실행된 것을 확인할 수 있습니다.

요약

	•	PHP-FPM 컨테이너(app): Laravel 애플리케이션을 실행
	•	Nginx 컨테이너(web): 프론트엔드 서버 역할
	•	MariaDB 컨테이너(db): 데이터베이스 서버

이 설정을 통해 Laravel과 MariaDB 기반의 게시판 애플리케이션을 Docker Compose로 관리하고, 효율적인 개발 환경을 구축할 수 있습니다.
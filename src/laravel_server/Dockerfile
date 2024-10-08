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
# Dockerfile
FROM php:8.2-fpm

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    zip \
    unzip \
    git \
    curl \
    && docker-php-ext-install pdo_mysql

# Composer 설치
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

# 작업 디렉토리 설정
WORKDIR /var/www

# Lumen 애플리케이션 파일 복사
COPY . /var/www

# 권한 설정
RUN chown -R www-data:www-data /var/www

# 의존성 설치
RUN composer install --no-dev --optimize-autoloader

EXPOSE 9000
CMD ["php-fpm"]
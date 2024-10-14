FROM php:8.2-fpm

# Install dependencies
RUN apt-get update && apt-get install -y \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    && docker-php-ext-install pdo pdo_mysql

# PHP 설정 파일 수정 (업로드 크기 제한 설정)
RUN echo "upload_max_filesize = 100M\npost_max_size = 100M" > /usr/local/etc/php/conf.d/uploads.ini


# Set working directory
WORKDIR /var/www/html

# 필요한 디렉토리 생성
RUN mkdir -p /var/www/html/storage /var/www/html/bootstrap/cache

# Copy the application code
COPY . /var/www/html

# 권한 설정
RUN chown -R www-data:www-data /var/www/html/storage /var/www/html/bootstrap/cache
RUN chmod -R 775 /var/www/html/storage /var/www/html/bootstrap/cache

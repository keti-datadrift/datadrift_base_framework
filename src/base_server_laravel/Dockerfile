FROM deltasquare4/docker-php-base:latest

MAINTAINER Rakshit Menpara <rakshit@improwised.com>

# Copy Composer
COPY ./app/composer.* /var/www/

RUN composer install \
  --no-scripts \
  --no-autoloader \
  --no-dev

# Copy app
COPY ./app /var/www

# Add build dependencies to compile drafter
RUN set -ex \
  && composer dump-autoload --optimize \
  && chown -R nginx:nginx /var/www

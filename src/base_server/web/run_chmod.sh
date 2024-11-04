docker compose exec app chown -R www-data:www-data /var/www/html/public
docker compose exec app chmod -R 775 /var/www/html/public 
docker compose exec app chmod -R 775 /var/www/html/storage
docker compose exec app chmod -R 775 /var/www/html/bootstrap/cache


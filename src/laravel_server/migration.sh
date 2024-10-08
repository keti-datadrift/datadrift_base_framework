docker compose exec app bash
php artisan migrate

chmod -R 777 storage
chmod -R 777 bootstrap/cache

docker compose exec app php artisan config:clear
docker compose exec app php artisan cache:clear
docker compose exec app php artisan config:cache

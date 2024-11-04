echo "Remove caches"
docker compose run app rm -rf bootstrap/cache/*.php
docker compose run app php artisan config:clear

echo "Recreate caches"
docker compose run app php artisan config:cache

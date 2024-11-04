mkdir ~/.datadrift
mkdir ~/.datadrift/grafana
mkdir ~/.datadrift/mariadb
mkdir ~/.datadrift/redis
mkdir ~/.datadrift/redisearch

docker compose up --build -d

mkdir ~/.datadrift
mkdir ~/.datadrift/grafana
mkdir ~/.datadrift/mariadb
mkdir ~/.datadrift/redis
mkdir ~/.datadrift/redisearch

clear
# docker-compose up # OLD
# docker compose up -d # Run backgroud process
docker compose up --build # Run foreground process

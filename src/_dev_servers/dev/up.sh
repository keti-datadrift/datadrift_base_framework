mkdir ~/.evc
mkdir ~/.evc/grafana
mkdir ~/.evc/mariadb
mkdir ~/.evc/redis
mkdir ~/.evc/redisearch

clear
# docker-compose up # OLD
# docker compose up -d # Run backgroud process
docker compose up # Run foreground process

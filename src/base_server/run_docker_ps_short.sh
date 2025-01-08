#docker ps --format '{{.Names}}'
#docker ps --format "table {{.Image}}\t{{.Ports}}\t{{.Names}}"
docker ps --format "table {{.Image}}\t{{.Names}}"

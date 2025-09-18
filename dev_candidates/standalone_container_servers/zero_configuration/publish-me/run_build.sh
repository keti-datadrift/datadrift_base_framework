# docker compose build

docker buildx create --use
docker buildx ls
docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile -t evcrepo/publish-me:latest --push .
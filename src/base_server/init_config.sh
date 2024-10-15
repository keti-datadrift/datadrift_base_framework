sudo chown -R $(whoami):$(whoami) ~/.datadrift/grafana
sudo chmod -R 755 ~/.datadrift/grafana

echo "UID=$(id -u)" >> .env
echo "GID=$(id -g)" >> .env

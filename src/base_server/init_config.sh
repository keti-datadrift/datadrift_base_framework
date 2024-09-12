sudo chown -R $(whoami):$(whoami) ~/.evc/grafana
sudo chmod -R 755 ~/.evc/grafana

echo "UID=$(id -u)" >> .env
echo "GID=$(id -g)" >> .env
# evc_server

## docker-compose install and access

- 참고 https://osg.kr/archives/2108#ubuntu-docker-compose-%EC%84%A4%EC%B9%98-%EB%B0%A9%EB%B2%95-%EA%B0%9C%EC%9A%94

- 설치

```bash

sudo apt-get update

sudo apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

sudo mkdir -p /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  
sudo apt-get update

sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

```

- 권한설정

```bash
sudo groupadd docker
groups
sudo usermod -aG docker $USER
newgrp docker
```


- 실행

```bash
docker compose up
```


- 종료

```bash
docker compose down
```

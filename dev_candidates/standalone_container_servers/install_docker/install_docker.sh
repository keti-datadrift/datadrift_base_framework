#!/bin/bash

# 시스템 정보 확인
OS_NAME=$(uname -s)
ARCHITECTURE=$(uname -m)
IS_DOCKER_INSTALLED=$(which docker)

# 함수: Docker 설치 확인 및 설치
install_docker() {
    echo "Docker가 설치되어 있지 않습니다. 설치를 진행합니다."

    if [[ "$OS_NAME" == "Linux" ]]; then
        if [[ "$ARCHITECTURE" == "x86_64" || "$ARCHITECTURE" == "amd64" ]]; then
            # Ubuntu/Debian에서 Docker 설치
            echo "Ubuntu/Debian 시스템에서 Docker를 설치합니다."
            sudo apt-get update
            sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt-get update
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io
        elif [[ "$ARCHITECTURE" == "armv7l" || "$ARCHITECTURE" == "aarch64" ]]; then
            # Raspberry Pi에서 Docker 설치
            echo "Raspberry Pi 시스템에서 Docker를 설치합니다."
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            rm get-docker.sh
        else
            echo "[-] 지원하지 않는 아키텍처: $ARCHITECTURE"
            exit 1
        fi

        # Docker 설치 후 사용자 그룹 설정
        echo "[+] Docker 설치가 완료되었습니다. 사용자 그룹을 설정합니다."
        sudo usermod -aG docker $USER
        newgrp docker
        echo "[+] Docker 사용자 그룹을 설정을 완료했습니다."
    else
        echo "[-] 이 스크립트는 Linux 시스템에서만 작동합니다."
        exit 1
    fi
}

# Docker 설치 여부 확인
if [[ -z "$IS_DOCKER_INSTALLED" ]]; then
    install_docker
else
    echo "Docker가 이미 설치되어 있습니다. 버전을 확인합니다:"
    docker --version
fi
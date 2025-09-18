# 네트워크 내에서 Edge 자동 감지

라즈베리 파이 장치만 감지하여 호스트 인벤토리에 추가하려면, 라즈베리 파이 장치의 특성을 사용하여 필터링하는 방법을 사용할 수 있습니다. 라즈베리 파이 장치는 주로 특정 호스트 이름 패턴이나 MAC 주소 벤더 코드 등을 통해 구별할 수 있습니다.

여기서는 라즈베리 파이의 호스트 이름이 주로 "raspberrypi" 또는 이와 유사한 패턴을 따르는 것을 이용해 필터링하는 예제를 보여드리겠습니다.

### Avahi를 사용하여 라즈베리 파이 감지 및 Ansible 인벤토리에 추가

1. **Avahi 설치 및 설정**
2. **필터링 스크립트 작성**
3. **Ansible 인벤토리 파일 작성**
4. **Ansible 플레이북 작성**

### 1. Avahi 설치 및 설정

라즈베리 파이 및 감지할 호스트 컴퓨터에 Avahi를 설치합니다.

#### 라즈베리 파이 및 호스트 컴퓨터

```sh
sudo apt-get update
sudo apt-get install avahi-daemon avahi-utils
```

Avahi 서비스 시작:

```sh
sudo systemctl start avahi-daemon
sudo systemctl enable avahi-daemon
```

[참고] Avahi 서비스 확인 및 종료

```sh
sudo systemctl status avahi-daemon
sudo systemctl stop avahi-daemon
sudo systemctl disable avahi-daemon
```

### 2. 필터링 스크립트 작성

라즈베리 파이 장치만 감지하여 Ansible 인벤토리에 추가하는 스크립트를 작성합니다.

```sh
#!/bin/bash

INVENTORY_FILE="./hosts"
PLAYBOOK_FILE="./setup_edge.yml"

# 감지된 에지 장치가 인벤토리에 이미 존재하는지 확인
function edge_exists() {
    local edge_ip=$1
    grep -q "$edge_ip" "$INVENTORY_FILE"
}

# 새로운 에지 장치를 인벤토리에 추가
function add_edge_to_inventory() {
    local edge_ip=$1
    echo "Adding $edge_ip to inventory"
    echo "$edge_ip ansible_user=your_user ansible_password=your_password" >> "$INVENTORY_FILE"
}

# 인벤토리에 추가된 에지 장치에 대해 플레이북 실행
function run_playbook() {
    local edge_ip=$1
    ansible-playbook -i "$INVENTORY_FILE" -l "$edge_ip" "$PLAYBOOK_FILE"
}

# 라즈베리 파이 장치를 감지하고 처리
function discover_raspberry_pi() {
    avahi-browse -r _workstation._tcp --resolve --terminate | grep "raspberrypi" | awk '{print $4}' | while read -r edge_ip; do
        if ! edge_exists "$edge_ip"; then
            add_edge_to_inventory "$edge_ip"
            run_playbook "$edge_ip"
        fi
    done
}

while true; do
    discover_raspberry_pi
    sleep 60 # 주기적으로 네트워크를 스캔합니다.
done
```

### 3. Ansible 인벤토리 파일 작성

Ansible 인벤토리 파일 `hosts`를 생성합니다.

```ini
[edges]
```

### 4. Ansible 플레이북 작성

라즈베리 파이 장치에 적용할 Ansible 플레이북 `setup_edge.yml`을 작성합니다.

```yaml
---
- name: Setup Raspberry Pi Edge Device
  hosts: all
  tasks:
    - name: Update and upgrade apt packages
      apt:
        update_cache: yes
        upgrade: dist

    - name: Install required packages
      apt:
        name:
          - python3
          - python3-pip
        state: present

    - name: Ensure the edge service is running
      systemd:
        name: edge-service
        state: started
        enabled: yes
```

### 실행 스크립트

위의 스크립트를 실행하여 새로운 라즈베리 파이 장치를 감지하고 처리합니다.

```sh
chmod +x run_discovery.sh
./run_discovery.sh
```

### 요약

- **Avahi 설치 및 설정**: 라즈베리 파이 및 호스트 컴퓨터에 Avahi를 설치하고 설정합니다.
- **필터링 스크립트 작성**: 라즈베리 파이 장치만 감지하여 Ansible 인벤토리에 추가하고 플레이북을 실행하는 스크립트를 작성합니다.
- **Ansible 인벤토리 및 플레이북 작성**: 인벤토리 파일과 플레이북을 작성하여 라즈베리 파이 장치에 대한 설정을 정의합니다.

이 방법을 사용하면 네트워크에 연결된 라즈베리 파이 장치를 자동으로 감지하고 Ansible을 통해 관리할 수 있습니다.
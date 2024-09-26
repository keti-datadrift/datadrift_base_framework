# Install Ansible

- Ansible을 사용하여 "Hello World" 예제를 실행하는 방법입니다.

### 1. Ansible 설치

먼저 Ansible을 설치해야 합니다. Ansible은 Python 기반의 도구이므로 `pip`를 사용하여 설치할 수 있습니다.

#### Ubuntu/Debian

```sh
sudo apt update
sudo apt install ansible -y
```

#### CentOS/RHEL

```sh
sudo yum install epel-release -y
sudo yum install ansible -y
```

#### macOS

```sh
brew install ansible
```

### 2. 인벤토리 파일 생성

Ansible은 인벤토리 파일을 사용하여 관리할 호스트를 정의합니다. 기본적으로 `/etc/ansible/hosts` 파일을 사용하지만, 프로젝트 디렉토리에 인벤토리 파일을 생성할 수도 있습니다.

프로젝트 디렉토리를 만들고 인벤토리 파일을 생성합니다.

```sh
mkdir ansible-hello-world
cd ansible-hello-world
echo "[local]
localhost ansible_connection=local" > hosts
```

### 3. 플레이북 작성

Ansible 플레이북은 YAML 형식으로 작성됩니다. "Hello World" 메시지를 출력하는 간단한 플레이북을 작성합니다.

`hello-world.yml` 파일을 생성합니다.

```yaml
---
- name: Hello World Playbook
  hosts: local
  tasks:
    - name: Print Hello World
      debug:
        msg: "Hello, World!"
```

### 4. 플레이북 실행

작성한 플레이북을 실행합니다.

```sh
ansible-playbook -i hosts hello-world.yml
```

이 명령어는 `hosts` 인벤토리 파일을 사용하여 `hello-world.yml` 플레이북을 실행합니다. 실행 결과는 다음과 비슷할 것입니다.

```
PLAY [Hello World Playbook] *******************************************************************

TASK [Gathering Facts] ***********************************************************************
ok: [localhost]

TASK [Print Hello World] *********************************************************************
ok: [localhost] => {
    "msg": "Hello, World!"
}

PLAY RECAP ***********************************************************************************
localhost                  : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

### 5. 요약

- **Ansible 설치**: Ansible을 설치합니다.
- **인벤토리 파일 생성**: 관리할 호스트를 정의하는 인벤토리 파일을 생성합니다.
- **플레이북 작성**: "Hello World" 메시지를 출력하는 간단한 플레이북을 작성합니다.
- **플레이북 실행**: 작성한 플레이북을 실행하여 결과를 확인합니다.

이 간단한 예제를 통해 Ansible의 기본 개념을 이해할 수 있습니다. Ansible은 매우 강력한 도구로, 복잡한 작업도 자동화할 수 있습니다. 이 예제를 시작으로 더 복잡한 작업을 수행하는 방법을 학습할 수 있습니다.
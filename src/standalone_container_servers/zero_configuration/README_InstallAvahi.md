# avahi 설치

1. Avahi를 설치합니다.

```sh
sudo apt-get update
sudo apt-get install avahi-daemon avahi-utils -y
```

2. Avahi 데몬을 시작하고 활성화합니다.

```sh
sudo systemctl status avahi-daemon
```

3. Avahi 데몬을 시작하고 활성화합니다.

```sh
sudo systemctl start avahi-daemon
sudo systemctl enable avahi-daemon
```

4. avahi-daemon.conf 설정

- 편집

```sh
sudo vi /etc/avahi/avahi-daemon.conf
```

- 편집 내용

```sh
[server]
use-ipv4=yes
use-ipv6=no
allow-interfaces=eth0,wlan0

[wide-area]
enable-wide-area=no

[publish]
publish-hinfo=yes
publish-workstation=yes

[reflector]
enable-reflector=no

[rlimits]
```

- 서비스 재시작

```sh
sudo systemctl restart avahi-daemon
```
 
6. Edge에서 퍼블리쉬

```sh
avahi-publish -s 'evc_edge' _workstation._tcp 9
```

#!/bin/bash

echo '-----------------------------'
echo ' publish-me started'
echo '-----------------------------'
# 호스트 이름과 IP 주소 가져오기
#HOSTNAME=$(hostname)
#IP_ADDRESS=$(hostname -I | awk '{print $1}')
#IP_ADDRESS=$(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)

# 전달받은 환경 변수 사용
HOSTNAME=${HOSTNAME}
IP_ADDRESS=${IP_ADDRESS}

echo $HOSTNAME
echo $IP_ADDRESS

# DBus 서비스 시작
dbus-daemon --system

# Avahi 데몬 시작
avahi-daemon -D

# Avahi 서비스 등록
avahi-publish -s "evc_edge" _workstation._tcp 9 "hostname=$HOSTNAME" "address=$IP_ADDRESS"

# 대몬이 종료되지 않도록 대기
tail -f /dev/null
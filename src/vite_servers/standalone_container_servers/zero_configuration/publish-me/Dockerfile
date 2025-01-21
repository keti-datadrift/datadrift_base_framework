# Dockerfile
FROM alpine:latest

# Avahi 및 필요한 패키지 설치
RUN apk update && apk add --no-cache \
    avahi avahi-tools dbus bash

# DBus 소켓 디렉토리 생성
RUN mkdir -p /var/run/dbus

# avahi-daemon 설정 파일 복사
COPY avahi-daemon.conf /etc/avahi/avahi-daemon.conf

# 서비스 시작 스크립트 복사
COPY start.sh /start.sh
RUN chmod +x /start.sh

# avahi-daemon 과 dbus 서비스 시작
CMD ["/start.sh"]
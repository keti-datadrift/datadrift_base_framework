# Python 3.10 이미지를 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 라이브러리 설치
RUN apt-get update && apt-get install -y \
    curl \
    libcurl4 \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 애플리케이션 코드 복사
COPY ./ /app

# 필수 패키지 설치
RUN pip install fiftyone

# 포트 노출
EXPOSE 5151

# 첫 번째 애플리케이션 실행
CMD ["python", "app.py"]
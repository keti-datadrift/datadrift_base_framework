# Python 3.10 기반 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 첫 번째 애플리케이션 코드 복사
COPY ./ /app

# 필요한 패키지를 미리 설치하기 위해 requirements.txt 파일을 복사
COPY requirements.txt .

# 필요한 패키지 설치 (예: Flask)
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 포트 노출 (예: Flask는 기본적으로 5000번 포트 사용)
EXPOSE 8011

# 첫 번째 애플리케이션 실행
CMD ["python", "app.py"]

# Python 3.10 기반 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 애플리케이션 코드 복사
COPY ./ /app

# Gradio 및 의존성 설치
RUN pip install --upgrade pip
RUN pip install gradio

# 포트 노출 (Gradio 기본 포트: 7860)
EXPOSE 8011

# Gradio 애플리케이션 실행
CMD ["python", "app.py"]
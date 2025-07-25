# data-ingestion-preprocessing/app.py
import os
import time
import json
from kafka import KafkaProducer

KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:9092') # docker-compose 네트워크 내 Kafka
PRODUCER_TOPIC = "raw_patient_data" # 생성할 토픽 이름

# Kafka Producer 설정
# bootstrap_servers: Kafka 브로커 주소 목록
# value_serializer: 메시지를 JSON 형식으로 직렬화 (인코딩 포함)
try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        api_version=(0, 10, 1) # Kafka 버전 호환성 설정
    )
    print(f"Kafka Producer 초기화 성공: {KAFKA_BROKER}")
except Exception as e:
    print(f"Kafka Producer 초기화 실패: {e}")
    exit(1) # 초기화 실패 시 종료

def generate_and_send_data():
    """
    임의의 환자 데이터를 생성하여 Kafka 토픽으로 전송합니다.
    """
    patient_id_counter = 0
    while True:
        patient_id_counter += 1
        sample_data = {
            "patient_id": f"P{patient_id_counter:04d}",
            "timestamp": int(time.time()),
            "heart_rate": 60 + (patient_id_counter % 30),
            "blood_pressure": f"{110 + (patient_id_counter % 20)}/{70 + (patient_id_counter % 10)}",
            "temperature": 36.5 + (patient_id_counter % 10) / 10,
            "event_type": "vital_sign_update"
        }
        try:
            # 데이터를 Kafka 토픽으로 비동기 전송
            future = producer.send(PRODUCER_TOPIC, sample_data)
            record_metadata = future.get(timeout=10) # 전송 확인 (블로킹)
            print(f"Sent: {sample_data['patient_id']} - Topic: {record_metadata.topic}, Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")
        except Exception as e:
            print(f"데이터 전송 실패: {e}")
        time.sleep(5) # 5초마다 데이터 전송

if __name__ == "__main__":
    print("데이터 수집 및 전처리 모듈 시작 중...")
    generate_and_send_data()
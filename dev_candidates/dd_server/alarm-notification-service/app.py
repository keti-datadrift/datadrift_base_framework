# alarm-notification-service/app.py
import os
import json
from kafka import KafkaConsumer

KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:9092')
CONSUMER_TOPIC = "diagnosis_results" # 진단 결과가 올 것으로 예상되는 토픽

# Kafka Consumer 설정
try:
    consumer = KafkaConsumer(
        CONSUMER_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='alarm-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        api_version=(0, 10, 1)
    )
    print(f"Kafka Consumer 초기화 성공: {KAFKA_BROKER}, Topic: {CONSUMER_TOPIC}")
except Exception as e:
    print(f"Kafka Consumer 초기화 실패: {e}")
    consumer = None

def send_notification(patient_id, message):
    """
    실제 알림 (SMS, 이메일, 푸시 알림)을 보내는 가상 함수.
    """
    print(f"[ALARM] 환자 {patient_id}에게 알림 전송: {message}")
    # 실제 구현: Twilio, SendGrid, FCM 등 연동

def process_diagnosis_results():
    """
    Kafka에서 진단 결과를 소비하고 알람 조건을 확인합니다.
    """
    if consumer is None:
        print("Kafka Consumer가 초기화되지 않아 메시지 소비를 시작할 수 없습니다.")
        return

    print(f"진단 결과 메시지 소비 시작: {CONSUMER_TOPIC}")
    for message in consumer:
        diagnosis_data = message.value
        patient_id = diagnosis_data.get("patient_id")
        diagnosis = diagnosis_data.get("diagnosis")
        recommendation = diagnosis_data.get("recommendation")

        print(f"Consumed Diagnosis: Patient: {patient_id}, Diagnosis: {diagnosis}, Recommendation: {recommendation}")

        # 알람 조건: '위험' 또는 '의심' 진단 시 알림
        if "위험" in diagnosis or "의심" in diagnosis:
            alert_message = f"긴급 알림: 환자 {patient_id}의 진단 결과: '{diagnosis}'. 권고: {recommendation}"
            send_notification(patient_id, alert_message)
        else:
            print(f"환자 {patient_id} 정상 범위: 알림 불필요.")

if __name__ == "__main__":
    print("알람 및 알림 서비스 시작 중...")
    process_diagnosis_results()
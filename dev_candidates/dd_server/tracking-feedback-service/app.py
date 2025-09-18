# tracking-feedback-service/app.py
import os
import json
import logging
import logstash # Logstash 핸들러
from kafka import KafkaConsumer, KafkaProducer

KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:9092')
LOGSTASH_HOST = os.getenv('LOGSTASH_HOST', 'logstash')
LOGSTASH_PORT = int(os.getenv('LOGSTASH_PORT', '5044'))

CONSUMER_TOPICS = ["raw_patient_data", "diagnosis_results"] # 소비할 토픽 목록
FEEDBACK_TOPIC = "feedback_events" # 피드백을 보낼 토픽

# 로거 설정 (Logstash로 전송)
logger = logging.getLogger('data_hospital_tracker')
logger.setLevel(logging.INFO)
logger.addHandler(logstash.LogstashHandler(LOGSTASH_HOST, LOGSTASH_PORT, version=1)) # TCP 방식
# console_handler = logging.StreamHandler()
# logger.addHandler(console_handler) # 콘솔 출력도 추가

# Kafka Consumer 설정
try:
    consumer = KafkaConsumer(
        *CONSUMER_TOPICS, # 여러 토픽을 구독
        bootstrap_servers=[KAFKA_BROKER],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='tracking-feedback-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        api_version=(0, 10, 1)
    )
    print(f"Kafka Consumer 초기화 성공: {KAFKA_BROKER}, Topics: {CONSUMER_TOPICS}")
except Exception as e:
    print(f"Kafka Consumer 초기화 실패: {e}")
    consumer = None

# Kafka Producer 설정 (피드백 전송용)
try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        api_version=(0, 10, 1)
    )
    print(f"Kafka Producer (Feedback) 초기화 성공: {KAFKA_BROKER}")
except Exception as e:
    print(f"Kafka Producer (Feedback) 초기화 실패: {e}")
    producer = None

def process_events():
    """
    Kafka에서 다양한 이벤트를 소비하고 로깅하며, 피드백을 시뮬레이션합니다.
    """
    if consumer is None:
        print("Kafka Consumer가 초기화되지 않아 메시지 소비를 시작할 수 없습니다.")
        return

    print(f"이벤트 메시지 소비 시작: {CONSUMER_TOPICS}")
    for message in consumer:
        event_data = message.value
        event_topic = message.topic
        patient_id = event_data.get("patient_id", "N/A")

        # 모든 이벤트를 Logstash로 로깅
        logger.info(f"Event Received: {event_topic}", extra={'patient_id': patient_id, 'event_data': event_data, 'source_topic': event_topic})
        print(f"Logged event from {event_topic} for {patient_id}: {event_data}")

        # 예시: 진단 결과에 대한 가상 피드백 생성
        if event_topic == "diagnosis_results":
            diagnosis = event_data.get("diagnosis")
            feedback_type = "positive" if "정상" in diagnosis else "needs_attention"
            feedback_message = f"진단 결과에 대한 시스템 피드백: {feedback_type}"

            feedback_event = {
                "patient_id": patient_id,
                "event_type": "system_feedback",
                "feedback_details": feedback_message,
                "original_diagnosis": diagnosis,
                "timestamp": int(time.time())
            }
            if producer:
                try:
                    producer.send(FEEDBACK_TOPIC, feedback_event).get(timeout=10)
                    print(f"Sent feedback for {patient_id}: {feedback_event}")
                except Exception as e:
                    print(f"피드백 전송 실패: {e}")

if __name__ == "__main__":
    print("추적 관리 및 피드백 서비스 시작 중...")
    # Kafka 및 Logstash 연결이 준비될 때까지 기다릴 수 있는 로직 추가 고려
    time.sleep(30) # 인프라 서비스 시작 대기
    process_events()
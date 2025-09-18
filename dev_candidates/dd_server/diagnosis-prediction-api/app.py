# diagnosis-prediction-api/app.py
import os
import json
from flask import Flask, request, jsonify
from kafka import KafkaConsumer
import threading
import time

app = Flask(__name__)

KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafka:9092')
CONSUMER_TOPIC = "raw_patient_data" # 데이터를 받아올 토픽

# Kafka Consumer 설정
try:
    consumer = KafkaConsumer(
        CONSUMER_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        auto_offset_reset='earliest', # 가장 오래된 오프셋부터 시작
        enable_auto_commit=True,
        group_id='diagnosis-group', # 컨슈머 그룹 ID
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        api_version=(0, 10, 1)
    )
    print(f"Kafka Consumer 초기화 성공: {KAFKA_BROKER}, Topic: {CONSUMER_TOPIC}")
except Exception as e:
    print(f"Kafka Consumer 초기화 실패: {e}")
    consumer = None # Consumer 초기화 실패 시 None으로 설정하여 앱이 계속 실행되도록 함

# 메모리에 최신 데이터를 저장하는 간단한 캐시 (실제는 DB 또는 캐시 서버 사용)
latest_patient_data = {}

def consume_kafka_messages():
    """
    백그라운드에서 Kafka 메시지를 지속적으로 소비합니다.
    """
    if consumer is None:
        print("Kafka Consumer가 초기화되지 않아 메시지 소비를 시작할 수 없습니다.")
        return

    print(f"Kafka 메시지 소비 시작: {CONSUMER_TOPIC}")
    for message in consumer:
        data = message.value
        patient_id = data.get("patient_id")
        if patient_id:
            latest_patient_data[patient_id] = data
            print(f"Consumed data for {patient_id}: {data}")
        # 여기서 데이터를 기반으로 진단 로직을 실행하거나,
        # 모델을 로드하여 예측을 수행할 수 있습니다.
        # (예: MLflow에서 모델 로드)
        # if "mlflow" in sys.modules:
        #     loaded_model = mlflow.pyfunc.load_model(model_uri)
        #     prediction = loaded_model.predict(input_data)

# Kafka 메시지 소비를 별도의 스레드에서 시작
if consumer:
    kafka_thread = threading.Thread(target=consume_kafka_messages)
    kafka_thread.daemon = True # 메인 스레드 종료 시 함께 종료
    kafka_thread.start()

@app.route('/diagnose', methods=['POST'])
def diagnose():
    """
    환자 데이터를 받아 가상의 진단 결과를 반환하는 API 엔드포인트.
    """
    data = request.get_json()
    patient_id = data.get('patient_id')
    current_data = latest_patient_data.get(patient_id)

    if not patient_id or not current_data:
        return jsonify({"error": "Patient data not found or invalid request"}), 400

    # 여기서 실제 기계학습 모델을 사용하여 진단 로직 구현
    # 지금은 가상의 진단 로직
    heart_rate = current_data.get('heart_rate', 0)
    diagnosis_result = "정상"
    recommendation = "일상적인 건강 관리 유지"

    if heart_rate > 90:
        diagnosis_result = "부정맥 의심"
        recommendation = "심박수 모니터링 및 전문의 상담 필요"
    elif heart_rate < 50:
        diagnosis_result = "서맥 의심"
        recommendation = "휴식 취하고 증상 지속 시 병원 방문"

    return jsonify({
        "patient_id": patient_id,
        "diagnosis": diagnosis_result,
        "recommendation": recommendation,
        "data_used": current_data
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "diagnosis-prediction-api"})

if __name__ == '__main__':
    print("Diagnosis Prediction API 서버 시작 중...")
    # Flask는 기본적으로 디버그 모드에서 자동 재시작되므로, main 함수에서 직접 run하지 않음
    # CMD ["flask", "run", "--host=0.0.0.0", "--port=8001"] 명령으로 실행됨
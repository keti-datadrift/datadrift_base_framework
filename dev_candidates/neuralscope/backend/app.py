from flask import Flask, request, jsonify
import redis
import evidently
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset, RegressionDriftPreset, ClassificationDriftPreset
import numpy as np
import pandas as pd
import fiftyone as fo
import os
import json

app = Flask(__name__)
redis_client = redis.Redis(host=os.environ.get('VECTOR_DB_HOST'), port=int(os.environ.get('VECTOR_DB_PORT')), decode_responses=True)
fiftyone_url = os.environ.get('FIFTYONE_URL')
if fiftyone_url:
    os.environ["FIFTYONE_DATABASE_URI"] = f"mongodb://fiftyone:27017/fiftyone" # FiftyOne 컨테이너 내부 MongoDB

# 가상의 데이터 로딩 함수 (실제 환경에서는 데이터 파이프라인 연동)
def load_reference_data():
    # ... 학습 데이터 로딩 로직
    return pd.DataFrame({'feature1': np.random.rand(100), 'feature2': np.random.rand(100), 'target': np.random.randint(0, 2, 100)})

def load_current_data():
    # ... 현재 운영 데이터 로딩 로직
    return pd.DataFrame({'feature1': np.random.rand(100) + 0.1, 'feature2': np.random.rand(100) - 0.1, 'target': np.random.randint(0, 2, 100)})

# 벡터 DB에 드리프트 정보 저장 (간단한 예시: JSON 형태 저장)
def store_drift_report_embedding(report_json, model_name, timestamp):
    embedding = json.dumps(report_json).encode('utf-8') # 실제 임베딩 방식은 필요에 따라 변경
    key = f"drift:{model_name}:{timestamp}"
    redis_client.set(key, embedding)

# FiftyOne 데이터셋 생성 및 업데이트 (드리프트 발생 데이터 시각화)
def visualize_drifted_samples(reference_data, current_data, drifted_indices, model_name, timestamp):
    try:
        session = fo.login(uri=fiftyone_url, auto=False)
        dataset_name = f"drifted_samples_{model_name}_{timestamp}"
        if dataset_name in fo.list_datasets():
            dataset = fo.load_dataset(dataset_name)
        else:
            dataset = fo.Dataset(dataset_name)

        # ... reference_data 및 current_data 샘플을 FiftyOne 데이터셋에 추가하고
        # drifted_indices에 해당하는 샘플에 드리프트 태그 등을 추가하는 로직
        # (FiftyOne API 활용)

        session.launch(dataset)
        session.logout()
    except Exception as e:
        print(f"FiftyOne 연동 오류: {e}")

@app.route('/api/detect_drift', methods=['POST'])
def detect_drift():
    data = request.get_json()
    model_name = data.get('model_name', 'default_model')
    reference_data = load_reference_data()
    current_data = load_current_data()
    timestamp = pd.Timestamp.now().isoformat()

    # Evidently AI를 사용하여 데이터 드리프트 감지
    data_drift_report = Report(metrics=[DataDriftPreset()])
    data_drift_report.run(reference_data=reference_data, current_data=current_data)
    report_json = data_drift_report.as_json()

    # 벡터 DB에 드리프트 보고서 (JSON) 저장
    store_drift_report_embedding(report_json, model_name, timestamp)

    # 드리프트 발생 가능성이 높은 데이터 샘플을 FiftyOne으로 시각화 (예시)
    if data_drift_report.metric_by_id('Data Drift').result['share_of_drifted_columns'] > 0.5:
        # ... 드리프트된 Feature 분석 후, 해당 Feature의 값 분포가 크게 달라진 샘플 추출 로직
        drifted_indices = np.random.choice(len(current_data), size=10, replace=False)
        visualize_drifted_samples(reference_data, current_data, drifted_indices, model_name, timestamp)

    return jsonify({"message": "Drift detection completed", "report": report_json, "timestamp": timestamp})

# 그라파나 연동을 위한 드리프트 지표 제공 API (예시)
@app.route('/api/drift_metrics/<model_name>', methods=['GET'])
def get_drift_metrics(model_name):
    # 벡터 DB에서 최신 드리프트 보고서를 조회하고 필요한 지표 추출
    latest_key = redis_client.keys(f"drift:{model_name}:*")
    if latest_key:
        latest_report_json = redis_client.get(sorted(latest_key)[-1])
        report = json.loads(latest_report_json)
        drift_share = report['metrics'][0]['result']['share_of_drifted_columns']
        # ... 다른 필요한 지표 추출
        return jsonify({"model_name": model_name, "drift_share": drift_share, "timestamp": sorted(latest_key)[-1]})
    return jsonify({"message": "No drift report found for this model"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
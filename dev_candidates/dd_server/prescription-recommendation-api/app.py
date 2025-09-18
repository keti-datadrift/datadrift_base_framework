# prescription-recommendation-api/app.py
import os
from flask import Flask, request, jsonify
import requests # 다른 서비스(진단 API) 호출용

app = Flask(__name__)

DIAGNOSIS_API_URL = os.getenv('DIAGNOSIS_API_URL', 'http://diagnosis-prediction-api:8001') # 진단 API 주소

@app.route('/recommend_prescription', methods=['POST'])
def recommend_prescription():
    """
    환자 ID를 받아 진단 API를 호출하고, 그 결과에 기반하여 처방/추천을 제공.
    """
    data = request.get_json()
    patient_id = data.get('patient_id')

    if not patient_id:
        return jsonify({"error": "Patient ID is required"}), 400

    try:
        # 진단 API 호출
        diagnosis_response = requests.post(f"{DIAGNOSIS_API_URL}/diagnose", json={"patient_id": patient_id})
        diagnosis_response.raise_for_status() # HTTP 오류 발생 시 예외 처리
        diagnosis_data = diagnosis_response.json()
        diagnosis_result = diagnosis_data.get('diagnosis')
        diagnosis_recommendation = diagnosis_data.get('recommendation')
        data_used = diagnosis_data.get('data_used')

        # 진단 결과에 따른 가상 처방/추천 로직
        prescription_recommendation = ""
        if "부정맥 의심" in diagnosis_result:
            prescription_recommendation = "심장 전문의와 상담 후 정밀 검사 및 필요시 약물 치료 고려."
        elif "서맥 의심" in diagnosis_result:
            prescription_recommendation = "휴식 후 증상 호전 여부 확인. 필요 시 심장 박동기 삽입 검토."
        elif "정상" in diagnosis_result:
            prescription_recommendation = "정기적인 건강 검진 및 생활 습관 유지 권고."
        else:
            prescription_recommendation = "진단 결과에 따른 추가 분석 필요."

        return jsonify({
            "patient_id": patient_id,
            "diagnosis_from_api": diagnosis_result,
            "overall_recommendation": f"{diagnosis_recommendation}. {prescription_recommendation}",
            "prescription_details": prescription_recommendation,
            "data_context": data_used
        })

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"진단 API 호출 실패: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"처방 추천 중 오류 발생: {e}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "prescription-recommendation-api"})

if __name__ == '__main__':
    print("처방 및 추천 API 서버 시작 중...")
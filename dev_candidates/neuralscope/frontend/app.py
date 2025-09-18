import streamlit as st
import requests
import pandas as pd
import json

BACKEND_URL = st.session_state.get('BACKEND_URL', 'http://localhost:5000') # Docker 환경에서는 nginx 주소로 변경 가능

st.title("뉴로매치 for Data Drift")

model_name = st.text_input("분석할 모델 이름:", "my_model")

if st.button("데이터 드리프트 감지"):
    try:
        response = requests.post(f"{BACKEND_URL}/api/detect_drift", json={"model_name": model_name})
        response.raise_for_status()
        result = response.json()
        st.success("데이터 드리프트 감지 완료!")
        st.json(result['report'])
        st.write(f"보고서 생성 시간: {result['timestamp']}")
    except requests.exceptions.RequestException as e:
        st.error(f"백엔드 API 오류: {e}")
    except Exception as e:
        st.error(f"오류 발생: {e}")

st.subheader("최근 드리프트 지표")
try:
    metrics_response = requests.get(f"{BACKEND_URL}/api/drift_metrics/{model_name}")
    metrics_response.raise_for_status()
    metrics = metrics_response.json()
    st.write(f"모델: {metrics['model_name']}")
    st.write(f"최근 드리프트 비율 (Data Drift): {metrics.get('drift_share', 'N/A')}")
    st.write(f"측정 시간: {metrics['timestamp']}")
except requests.exceptions.RequestException as e:
    st.warning(f"최근 드리프트 지표를 불러올 수 없습니다: {e}")
except Exception as e:
    st.error(f"오류 발생: {e}")

st.subheader("FiftyOne 시각화")
st.info(f"FiftyOne UI는 다음 주소에서 확인할 수 있습니다: http://localhost:5171") # 실제 환경에 맞게 변경
st.write("드리프트가 감지된 데이터 샘플은 FiftyOne에서 확인하실 수 있습니다.")
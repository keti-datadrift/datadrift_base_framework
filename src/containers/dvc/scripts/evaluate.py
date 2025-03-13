#------------------------------------------------------------------------------
# title : evaluate.py
# by : JPark @ KETI, since March 2025
# function : Evaluation
#------------------------------------------------------------------------------

import pandas as pd
import pickle
import json
from sklearn.metrics import accuracy_score

# 데이터 로드
test = pd.read_csv("data/processed/test.csv")

# 입력(X)과 출력(y) 분리
X_test = test.drop(columns=["label"])
y_test = test["label"]

# 모델 로드
with open("models/model.pkl", "rb") as f:
    model = pickle.load(f)

# 예측 및 평가
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

# 평가 결과 저장
metrics = {"accuracy": accuracy}
with open("outputs/metrics.json", "w") as f:
    json.dump(metrics, f)

print(f"✅ Model evaluation complete! Accuracy: {accuracy:.4f}")

#------------------------------------------------------------------------------
# End of this file
#------------------------------------------------------------------------------

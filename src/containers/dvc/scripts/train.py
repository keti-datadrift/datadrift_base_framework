#------------------------------------------------------------------------------
# title : train.py
# by : JPark @ KETI, since March 2025
# function : Training (Logistic Regression)
#------------------------------------------------------------------------------

import pandas as pd
import pickle
from sklearn.linear_model import LogisticRegression

# 데이터 로드
train = pd.read_csv("data/processed/train.csv")

# 입력(X)과 출력(y) 분리
X_train = train.drop(columns=["label"])
y_train = train["label"]

# 모델 학습
model = LogisticRegression()
model.fit(X_train, y_train)

# 모델 저장
with open("models/model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model training complete! Model saved as models/model.pkl")

#------------------------------------------------------------------------------
# End of this file
#------------------------------------------------------------------------------

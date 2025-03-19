import os
import json
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

DD_DIR = ".dd"
MODEL_LOG_FILE = os.path.join(DD_DIR, "model_log.json")

def load_model_log():
    """ model_log.json을 로드하거나 새로 생성 """
    if not os.path.exists(MODEL_LOG_FILE):
        return {}
    with open(MODEL_LOG_FILE, "r") as f:
        return json.load(f)

def save_model_log(model_log):
    """ model_log.json 저장 """
    with open(MODEL_LOG_FILE, "w") as f:
        json.dump(model_log, f, indent=4)

def run(filepath, output):
    df = pd.read_csv(filepath)
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    accuracy = round(accuracy_score(y_test, y_pred), 4)
    f1 = round(f1_score(y_test, y_pred, average="macro"), 4)

    with open(output, "wb") as f:
        pickle.dump(model, f)

    model_log = load_model_log()
    model_log[output] = {
        "accuracy": accuracy,
        "f1_score": f1,
        "trained_on": filepath
    }
    save_model_log(model_log)

    print(f"✅ 모델 학습 완료: {output}")
    print(f"📊 모델 성능: Accuracy={accuracy}, F1 Score={f1}")
    print(f"✅ 모델 학습 로그 업데이트 완료: {MODEL_LOG_FILE}")
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def run(filepath, output):
    df = pd.read_csv(filepath)
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]

    model = RandomForestClassifier()
    model.fit(X, y)

    with open(output, "wb") as f:
        pickle.dump(model, f)

    print(f"✅ 모델 학습 완료: {output}")
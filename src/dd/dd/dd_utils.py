import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
import numpy as np

# 데이터 품질 진단
def diagnose_data(filepath):
    df = pd.read_csv(filepath)
    report = {
        "missing_values": df.isnull().sum().sum(),
        "duplicates": df.duplicated().sum(),
        "outliers": (np.abs(df - df.mean()) > (2 * df.std())).sum().sum()
    }
    return report

# 데이터 품질 개선
def treat_data(filepath):
    df = pd.read_csv(filepath)
    df.fillna(df.mean(), inplace=True)
    df = df[~df.duplicated()]
    df = df[(np.abs(df - df.mean()) <= (2 * df.std()))]
    
    new_filepath = filepath.replace(".csv", "_cleaned.csv")
    df.to_csv(new_filepath, index=False)
    return new_filepath

# 모델 학습
def train_model(filepath, output):
    df = pd.read_csv(filepath)
    X = df.iloc[:, :-1]  # 특징 데이터
    y = df.iloc[:, -1]   # 타겟 데이터
    
    model = RandomForestClassifier()
    model.fit(X, y)
    
    with open(output, "wb") as f:
        pickle.dump(model, f)
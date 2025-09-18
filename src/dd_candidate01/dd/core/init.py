#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

import os
import json
import pandas as pd
import numpy as np
import subprocess

# 프로젝트 디렉토리 구조 정의
ROOT_NAME = "./"
DIR_STRUCTURE = [
    "data/raw",
    "data/processed",
    "models",
    "scripts",
    "notebooks",
    "outputs",
    "docs",
]

# 샘플 데이터 생성 함수
def generate_sample_data():
    np.random.seed(42)
    num_samples = 300
    feature1 = np.random.uniform(4.5, 7.5, num_samples)
    feature2 = np.random.uniform(2.5, 4.5, num_samples)
    feature3 = np.random.uniform(1.0, 6.0, num_samples)
    labels = (feature1 >= 6).astype(int)

    df = pd.DataFrame({"feature1": feature1, "feature2": feature2, "feature3": feature3, "label": labels})
    df.to_csv(f"{ROOT_NAME}/data/raw/data.csv", index=False)
    print("✅ Sample data generated: data/raw/data.csv")

# 기본 스크립트 생성
SCRIPTS = {
    "scripts/preprocess.py": """import pandas as pd
from sklearn.model_selection import train_test_split

data = pd.read_csv("data/raw/data.csv")
train, test = train_test_split(data, test_size=0.2, random_state=42)

train.to_csv("data/processed/train.csv", index=False)
test.to_csv("data/processed/test.csv", index=False)

print("✅ Data preprocessing complete!")
""",
    
    "scripts/train.py": """import pandas as pd
import pickle
from sklearn.linear_model import LogisticRegression

train = pd.read_csv("data/processed/train.csv")
X_train = train.drop(columns=["label"])
y_train = train["label"]

model = LogisticRegression()
model.fit(X_train, y_train)

with open("models/model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model training complete!")
""",
    
    "scripts/evaluate.py": """import pandas as pd
import pickle
import json
from sklearn.metrics import accuracy_score

test = pd.read_csv("data/processed/test.csv")
X_test = test.drop(columns=["label"])
y_test = test["label"]

with open("models/model.pkl", "rb") as f:
    model = pickle.load(f)

y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

metrics = {"accuracy": accuracy}
with open("outputs/metrics.json", "w") as f:
    json.dump(metrics, f)

print(f"✅ Model evaluation complete! Accuracy: {accuracy:.4f}")
""",
    
    "dvc.yaml": """stages:
  preprocess:
    cmd: python scripts/preprocess.py
    deps:
      - data/raw/data.csv
      - scripts/preprocess.py
    outs:
      - data/processed/train.csv
      - data/processed/test.csv

  train:
    cmd: python scripts/train.py
    deps:
      - data/processed/train.csv
      - scripts/train.py
    outs:
      - models/model.pkl

  evaluate:
    cmd: python scripts/evaluate.py
    deps:
      - data/processed/test.csv
      - models/model.pkl
      - scripts/evaluate.py
    metrics:
      - outputs/metrics.json
""",
    
    "run_pipeline.sh": """
    # 1️⃣ git and DVC initialization
    git init
    dvc init
        
    # 2️⃣ 데이터 생성
    python scripts/generate_data.py
        
    # 3️⃣ Data management (with Git)
    dvc add data/raw/data.csv
    git add data/.gitignore data/raw/data.csv.dvc
    git commit -m "Add raw dataset"
        
    # 4️⃣ Run pipeline (preprocess → training → evaluation)
    dvc repro
        
    # 5️⃣ Check result
    cat outputs/metrics.json  # { "accuracy": 0.XX }
""",
}

# .gitignore 파일 생성
GITIGNORE_CONTENT = """__pycache__/
*.pyc
.DS_Store
data/raw/*.dvc
models/
**/metrics.json
outputs/
**/.ipynb_checkpoints
"""

# 프로젝트 생성 함수
def create_project():
    print(f"🚀 Creating dd project: {ROOT_NAME}")

    # 디렉토리 생성
    for folder in DIR_STRUCTURE:
        os.makedirs(f"{ROOT_NAME}/{folder}", exist_ok=True)

    # 스크립트 파일 생성
    for filename, content in SCRIPTS.items():
        filepath = os.path.join(ROOT_NAME, filename)
        with open(filepath, "w") as f:
            f.write(content)

    # .gitignore 생성
    with open(f"{ROOT_NAME}/.gitignore", "w") as f:
        f.write(GITIGNORE_CONTENT)

    # 샘플 데이터 생성
    generate_sample_data()

    print("✅ Project scaffolding complete!")

# Git & DVC 초기화
def init_git_dvc():
    os.chdir(ROOT_NAME)
    subprocess.run(["git", "init"])
    subprocess.run(["dvc", "init"])
    subprocess.run(["dvc", "add", "data/raw/data.csv"])
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", "Initial commit with DVC setup"])
    print("✅ Git and DVC initialized successfully!")

def init_dd():
    os.makedirs(".dd", exist_ok=True)

    metadata = {
        "project": {
            "name": "AI_Project",
            "description": "AI 모델을 위한 데이터 및 학습 관리"
        },
        "domains": {}
    }

    config = {
        "dd": {
            "version": "0.1.0",
            "track_data": True,
            "track_models": True,
            "sync_with_hub": False
        },
        "monitoring": {
            "enabled": True,
            "interval": "7d"
        }
    }

    with open(".dd/metadata.yaml", "w") as f:
        json.dump(metadata, f, indent=4)

    with open(".dd/config.yaml", "w") as f:
        json.dump(config, f, indent=4)

def run():
    init_git_dvc()
    init_dd()
    create_project()
    print(f"🎉 DD Project is ready! Run 'dvc repro' to start the pipeline.")


#------------------------------------------------------------------------------
# End of this file
#------------------------------------------------------------------------------
import os
import json

def run():
    os.makedirs(".dd", exist_ok=True)
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("models", exist_ok=True)

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

    print("✅ `dd` 프로젝트가 초기화되었습니다!")
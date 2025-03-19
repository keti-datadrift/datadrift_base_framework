import os
import json
import yaml
import argparse
import requests
from dd.dd_utils import diagnose_data, treat_data, train_model

DD_HUB_URL = "http://127.0.0.1:8001"
# 🔹 `version.json`을 패키지 내에서 찾기
VERSION_FILE = os.path.join(os.path.dirname(__file__), "..", "version.json")

try:
    with open(VERSION_FILE, "r") as f:
        version_info = json.load(f)
except FileNotFoundError:
    version_info = {"version": "Unknown", "release_date": "N/A"}

def main():
    parser = argparse.ArgumentParser(
        description="🚀 dd: AI 데이터 및 모델 관리 CLI",
        usage="""
    dd init                          # 프로젝트 초기화
    dd push <파일>                    # 데이터/모델 dd Hub에 업로드
    dd pull <파일명>                   # dd Hub에서 데이터/모델 다운로드
    dd diagnose <데이터 파일>          # 데이터 품질 진단
    dd treat <데이터 파일>             # 데이터 품질 개선
    dd train <데이터 파일> [--output 모델 파일]  # 모델 학습
    dd --help                         # 명령어 도움말
    dd --version                      # 버전 정보 확인
    """
    , add_help=True)
    
    subparsers = parser.add_subparsers(dest="command")

    # 데이터 업로드
    upload_parser = subparsers.add_parser("push")
    upload_parser.add_argument("filepath", help="File to upload (data or model)")

    # 데이터 다운로드
    download_parser = subparsers.add_parser("pull")
    download_parser.add_argument("filename", help="File to download")

    # 데이터 진단
    diagnose_parser = subparsers.add_parser("diagnose")
    diagnose_parser.add_argument("filepath", help="Data file to diagnose")

    # 데이터 품질 개선
    treat_parser = subparsers.add_parser("treat")
    treat_parser.add_argument("filepath", help="Data file to treat")

    # 모델 학습
    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("filepath", help="Data file for training")
    train_parser.add_argument("--output", help="Output model file")

    # Version
    parser.add_argument("--version", "-v", action="store_true", help="현재 dd 버전 정보 출력")
    
    # 인자 파싱 및 실행
    args = parser.parse_args()

    if args.version:
        print(f"📌 dd Version: {version_info['version']} (Released: {version_info['release_date']})")
        return
        
    if args.command is None:
        parser.print_help()
        return

    if args.command == "init":
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
                "version": "1.0",
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

    elif args.command == "push":
        filepath = args.filepath
        if not os.path.exists(filepath):
            print("❌ 파일이 존재하지 않습니다.")
            exit()

        files = {"file": open(filepath, "rb")}
        if filepath.startswith("data/"):
            response = requests.post(f"{DD_HUB_URL}/upload/data/", files=files)
        else:
            response = requests.post(f"{DD_HUB_URL}/upload/model/", files=files)

        print(response.json())

    elif args.command == "pull":
        filename = args.filename
        response = requests.get(f"{DD_HUB_URL}/download/data/{filename}")
        if response.status_code == 200:
            print(f"✅ 다운로드 링크: {response.json()['download_url']}")
        else:
            print("❌ 파일을 찾을 수 없습니다.")

    elif args.command == "diagnose":
        filepath = args.filepath
        report = diagnose_data(filepath)
        print(json.dumps(report, indent=4))

    elif args.command == "treat":
        filepath = args.filepath
        new_filepath = treat_data(filepath)
        print(f"✅ 데이터 품질 개선 완료: {new_filepath}")

    elif args.command == "train":
        filepath = args.filepath
        output = args.output or "models/new_model.pkl"
        train_model(filepath, output)
        print(f"✅ 모델 학습 완료: {output}")
#------------------------------------------------------------------------------
# data drift (dd) management module
# jpark @ KETI
#------------------------------------------------------------------------------

import argparse
import os
import json
from dd.core import init, push, pull, diagnose, treat, train, monitor, lineage, compare, fuse, visualize, embed, compare_folders

# 🔹 `config.json`을 패키지 내부에서 찾기
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "config.json")
try:
    with open(CONFIG_FILE, "r") as f:
        version_info = json.load(f)
except FileNotFoundError:
    version_info = {"version": "Unknown", "release_date": "N/A"}

def main():
    parser = argparse.ArgumentParser(description="🚀 dd: AI 데이터 및 모델 관리 CLI")
    subparsers = parser.add_subparsers(dest="command")

    # ✅ 프로젝트 초기화
    subparsers.add_parser("init", help="프로젝트 초기화 및 .dd 설정 파일 생성")

    # ✅ 데이터/모델 업로드
    push_parser = subparsers.add_parser("push", help="데이터/모델을 dd Hub에 업로드")
    push_parser.add_argument("filepath", help="업로드할 파일")

    # ✅ 데이터/모델 다운로드
    pull_parser = subparsers.add_parser("pull", help="dd Hub에서 데이터/모델 다운로드")
    pull_parser.add_argument("filename", help="다운로드할 파일 이름")

    # ✅ 데이터 품질 진단
    diagnose_parser = subparsers.add_parser("diagnose", help="데이터 품질 진단")
    diagnose_parser.add_argument("filepath", help="진단할 데이터 파일")

    # ✅ 데이터 품질 개선
    treat_parser = subparsers.add_parser("treat", help="데이터 품질 개선")
    treat_parser.add_argument("filepath", help="정제할 데이터 파일")

    # ✅ 모델 학습
    train_parser = subparsers.add_parser("train", help="모델 학습")
    train_parser.add_argument("filepath", help="학습할 데이터 파일")
    train_parser.add_argument("--output", help="출력할 모델 파일", default="models/new_model.pkl")

    # ✅ 데이터 및 모델 lineage 추적
    lineage_parser = subparsers.add_parser("lineage", help="데이터 및 모델 lineage 추적")
    lineage_parser.add_argument("filepath", help="추적할 데이터 또는 모델")

    # ✅ 모델 성능 비교
    compare_models_parser = subparsers.add_parser("compare_models", help="두 개의 모델 성능 비교")
    compare_models_parser.add_argument("model1", help="첫 번째 모델 파일")
    compare_models_parser.add_argument("model2", help="두 번째 모델 파일")

    # ✅ 모델 융합
    fuse_parser = subparsers.add_parser("fuse", help="두 개의 모델을 융합")
    fuse_parser.add_argument("model1", help="첫 번째 모델 파일")
    fuse_parser.add_argument("model2", help="두 번째 모델 파일")
    fuse_parser.add_argument("--output", help="융합된 모델 파일", required=True)

    # ✅ 모니터링
    monitor_parser = subparsers.add_parser("monitor", help="데이터 및 모델 모니터링")
    monitor_parser.add_argument("filepath", help="모니터링할 파일")
    monitor_parser.add_argument("--interval", type=int, default=7, help="모니터링 주기 (일)")

    # ✅ version 확인
    parser.add_argument("--version", "-v", action="store_true", help="현재 dd 버전 정보 출력")

    # ✅ 상태 시각화
    visualize_parser = subparsers.add_parser("visualize", help=".dd 상태 시각화")
    visualize_parser.add_argument("--output", help="출력 파일명 (예: output.pdf, output.html)")

    # ✅ embed
    embed_parser = subparsers.add_parser("embed", help=".dd embedding")
    embed_parser.add_argument("--folders", help="입력 폴더 (예: \"folder1 folder2 folder3\" )")

    # ✅ embed
    compare_folders_parser = subparsers.add_parser("compare_folders", help=".dd compare")
    compare_folders_parser.add_argument("--folders", help="입력 폴더 (예: \"folder1 folder2 folder3\" )")
    compare_folders_parser.add_argument("--dim_reduction_method", type=str, default="PCA", help="Reduction method: PCA, UMAP, KernelPCA, etc.")
    compare_folders_parser.add_argument("--output_dir", type=str, default="outputs", help="Directory to save outputs.")

    
    # 인자 파싱 및 실행
    args = parser.parse_args()

    if args.version:
        print(f"📌 dd Version: {version_info['version']} (Released: {version_info['release_date']})")
        return
        
    elif args.command == "init":
        init.run()
        
    elif args.command == "visualize":
        visualize.run(args.output if args.output else "output.pdf")
  
    elif args.command == "push":
        push.run(args.filepath)

    elif args.command == "pull":
        pull.run(args.filename)

    elif args.command == "diagnose":
        diagnose.run(args.filepath)

    elif args.command == "treat":
        treat.run(args.filepath)

    elif args.command == "train":
        train.run(args.filepath, args.output)

    elif args.command == "lineage":
        lineage.run(args.filepath)

    elif args.command == "compare_models":
        compare_models.run(args.model1, args.model2)

    elif args.command == "fuse":
        fuse.run(args.model1, args.model2, args.output)

    elif args.command == "monitor":
        monitor.run(args.filepath, args.interval)
        
    elif args.command == "embed":
        embed.run(args.folders)

    elif args.command == "compare_folders":
        compare_folders.run(args.folders, 
                            args.dim_reduction_method, 
                            args.output_dir )

        
#------------------------------------------------------------------------------
# End of this file
#------------------------------------------------------------------------------
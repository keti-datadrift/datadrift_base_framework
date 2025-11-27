#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# dvc 초기화
if [ ! -d ".dvc" ]; then
  dvc init
fi

mkdir -p data
mkdir -p dvcstore

# data 디렉터리를 DVC에 등록
if [ ! -f "data.dvc" ]; then
  dvc add data
fi

# 로컬 remote를 기본으로 설정
dvc remote add -d localstore ./dvc_storage || true

echo "DVC initialized."
# 문제 해결

자주 발생하는 문제 및 해결 방법입니다.

## 일반적인 문제

### Q: "data.dvc not found" 오류

**원인:** 데이터를 먼저 추가해야 합니다.

**해결책:**
```bash
ddoc add --data /path/to/data
```

### Q: "No git commits found" 오류

**원인:** Git commit이 필요합니다.

**해결책:**
```bash
git add .
git commit -m "Initial commit"
```

### Q: 스냅샷 복원 시 충돌

**원인:** 현재 변경사항이 있습니다.

**해결책:**
```bash
# 변경사항 커밋
git add .
git commit -m "Save changes"
ddoc snapshot --restore v01

# 또는 강제 복원
ddoc snapshot --restore v01 --force
```

### Q: DVC 데이터가 복원되지 않음

**원인:** DVC checkout이 필요합니다.

**해결책:**
```bash
dvc checkout
```

## Trainer 관련 문제

### Q: Trainer를 찾을 수 없음

**에러 메시지:**
```
❌ Trainer 'yolo' not found in code/trainers
```

**해결책:**
- `code/trainers/yolo/` 디렉토리가 존재하는지 확인
- `train.py` 또는 `eval.py` 파일이 있는지 확인
- `ddoc add --code ... --trainer yolo` 명령으로 추가

### Q: 모델을 찾을 수 없음

**에러 메시지:**
```
❌ Model not found: yolov8n.pt
```

**해결책:**
- `models/` 디렉토리가 생성되었는지 확인
- 모델 이름이 올바른지 확인 (예: `yolov8n.pt`, `yolov8s.pt`)
- 인터넷 연결 확인 (자동 다운로드 필요)

### Q: data.yaml 경로 오류

**에러 메시지:**
```
Dataset 'data/dataset_name/data.yaml' images not found
```

**해결책:**
- `data.yaml`의 `path` 필드가 워크스페이스 루트 기준 상대 경로인지 확인
- `path: data/dataset_name` 형식 사용 권장

## 분석 관련 문제

### Q: 분석이 너무 느림

**해결책:**
- 캐시 시스템 활용 (자동으로 활성화됨)
- 증분 분석 사용 (변경된 파일만 재분석)
- 데이터 해시 기반 캐시 공유

### Q: 캐시가 업데이트되지 않음

**해결책:**
```bash
# 캐시 강제 갱신 (필요 시)
# 캐시는 자동으로 동기화되므로 일반적으로 필요 없음
```

## 스냅샷 관련 문제

### Q: 스냅샷 생성 실패

**원인:** Git 또는 DVC 상태 문제

**해결책:**
```bash
# Git 상태 확인
git status

# DVC 상태 확인
dvc status

# 문제 해결 후 재시도
ddoc snapshot create -m "message"
```

### Q: 스냅샷 복원 후 데이터가 없음

**해결책:**
```bash
# DVC checkout 수동 실행
dvc checkout

# 또는 스냅샷 재복원
ddoc snapshot --restore <version> --force
```

## 실험 관련 문제

### Q: MLflow UI가 표시되지 않음

**해결책:**
```bash
# MLflow UI 실행
mlflow ui

# 포트 변경 (기본: 5000)
mlflow ui --port 5001

# 원격 접속 허용
mlflow ui --host 0.0.0.0
```

### Q: 실험 결과가 저장되지 않음

**해결책:**
- `experiments/` 디렉토리 확인
- MLflow 로그 확인
- Trainer 함수의 반환값 확인

## 추가 도움말

문제가 해결되지 않으면:
- [GitHub Issues](https://github.com/your-org/ddoc/issues)에 이슈 리포트
- [명령어 레퍼런스](../reference/commands.md) 확인
- [사용자 가이드](../guides/) 참조


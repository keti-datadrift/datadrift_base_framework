# Documentation snippets for `ddoc exp` (Round-5 conversion).
# These are NOT meant to be executed as-is — the original file used
# leading `$` prompts which bash evaluated as variable expansions and
# silently truncated the lines. Kept as commented examples.

# 1. 실험 큐에 추가 — exp01 정의 + 학습률(lr) 오버라이드
# ddoc exp run exp01 --params '{"train": {"lr": 0.0001}}'

# 2. Dry Run — 변경 사항만 확인
# ddoc exp run exp06 --params '{"train": {"epochs": 1}}'

# 3. HEAD 커밋 상태와 특정 실험 비교
# ddoc exp show --name HEAD --baseline exp-12345

# 4. master 브랜치 베이스라인과 비교
# ddoc exp show --name my-first-exp --baseline master

# Note: `ddoc exp` 명령은 [exp] extras 를 요구합니다.
#   pip install -e ".[exp]"   # mlflow 설치

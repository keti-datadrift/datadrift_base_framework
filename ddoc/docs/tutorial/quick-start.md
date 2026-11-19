# 빠른 시작

5분 안에 ddoc 로 첫 drift 판정을 내려 봅니다.

## 1. 설치

저장소 루트에서:

```bash
pip install -e ddoc
pip install -e plugins/ddoc-plugin-categorical
```

자세한 내용은 [설치 가이드](installation.md) 참고.

## 2. toy 데이터 만들기

```bash
ddoc examples generate categorical --out /tmp/d --scenario shifted
```

`/tmp/d/ref` (기준) 와 `/tmp/d/cur` (현재) 두 디렉토리가 생깁니다.
`--scenario identical` 로 만들면 두 쪽이 같아서 drift 가 없어야 정상입니다.

## 3. 한 줄 판정 — `ddoc diff`

```bash
ddoc diff /tmp/d/ref /tmp/d/cur
echo $?      # 0 = OK, 1 = DRIFT, 2 = BLIND
```

생 CSV 는 플러그인 없이도 비교됩니다:

```bash
ddoc diff jan.csv aug.csv
```

## 4. 근거 남기기

```bash
ddoc diff /tmp/d/ref /tmp/d/cur --json               # 판정 JSON 한 객체
ddoc diff /tmp/d/ref /tmp/d/cur --report note.html   # 판정 + 근거 + 처방 HTML 소견서
```

## 5. 저수준 분석과 리포트

검출기를 고르거나 여러 modality 결과를 합치려면 `ddoc analyze drift` 를 씁니다:

```bash
ddoc analyze drift --data-path-ref /tmp/d/ref --data-path-cur /tmp/d/cur \
                   --json --quiet > drift.json
ddoc report render -i drift.json -o drift.md --format md
```

## 6. CI 데이터 게이트로 쓰기

exit code 가 판정이므로 CI 단계에 그대로 넣으면 됩니다.
저장소 루트의 `action.yml` 이 GitHub Action 으로 이 동작을 제공합니다.

## 다음 단계

- [핵심 개념](concepts.md) — 판정, modality, 플러그인, envelope
- [toy 데이터](toy-data.md) — modality 별 예제와 dataset layout
- [detector cookbook](detectors.md) — `--detector` 선택과 severity 임계값
- [레시피](recipe.md) — 여러 단계를 YAML 하나로

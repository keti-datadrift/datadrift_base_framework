# Drift Zoo 🦓

유명한 드리프트 패턴들을 **한 명령으로 재현**하는 갤러리.
각 케이스는 튜토리얼이자 ddoc의 회귀 테스트입니다(`tests/test_zoo.py`).

```bash
cd zoo/<case>
python make.py            # data/ref.csv, data/cur.csv 생성 (고정 seed)
ddoc diff data/ref.csv data/cur.csv --report note.html
```

| case | 패턴 | 기대 판정 | 이야기 |
|---|---|---|---|
| [`regime_shift/`](regime_shift/) | 영구 레짐 전환 | **DRIFT** (high) | 어느 날부터 세상이 바뀌었고 되돌아오지 않는다 — 가격대·채널 구성이 통째로 이동 |
| [`creeping_degradation/`](creeping_degradation/) | 점진 열화 | **DRIFT** | 하루하루는 멀쩡해 보이는데 한 달 전과 비교하면 센서가 죽어가고 있다 |
| [`rhythm_not_drift/`](rhythm_not_drift/) | 주기 리듬 (함정) | **OK** | 월요일과 화요일은 다르게 *보이지만* 드리프트가 아니다 — 탐지기는 아니라고 말할 줄도 알아야 한다 |

세 번째 케이스가 핵심입니다: 모든 것을 DRIFT라 우기는 탐지기는 알람 피로만
만듭니다. ddoc의 판정은 3값(OK / DRIFT / BLIND)이고, Zoo는 세 답이 모두
나오는 것까지 검증합니다.

"""Rhythm, not drift — 월요일과 화요일은 다르게 *보이지만*
드리프트가 아니다.

같은 매장의 이틀치 방문자 로그(방문자 단위 행). 두 날 모두 동일한
일간 리듬(아침 피크 / 점심 피크 / 저녁 피크)을 따르고 표본 노이즈만
다르다. 개별 시각을 순간 비교하면 요란해 보여도, 하루 전체 분포로
보면 같은 세상이다. 탐지기는 "아니오"라고 말할 줄도 알아야 한다 —
모든 것을 DRIFT라 우기는 탐지기는 알람 피로만 만든다.

기대 판정: OK
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def make(out_dir: Path, *, seed: int = 23) -> tuple[Path, Path]:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    def day() -> list[str]:
        rows = []
        for h in range(24):
            base = (
                60 * np.exp(-((h - 8) ** 2) / 4)      # 출근 피크
                + 80 * np.exp(-((h - 12.5) ** 2) / 3)  # 점심 피크
                + 70 * np.exp(-((h - 18.5) ** 2) / 5)  # 저녁 피크
                + 5
            )
            visits = max(0, int(rng.normal(base, base * 0.07)))
            for _ in range(visits):   # 방문자 1명 = 1행
                dwell = max(1.0, rng.normal(12, 2.5))
                basket = max(0.0, rng.normal(28, 9))
                rows.append(f"{h},{dwell:.1f},{basket:.2f}")
        return rows

    header = "hour,dwell_min,basket_krw_k"
    ref = out_dir / "ref.csv"
    cur = out_dir / "cur.csv"
    ref.write_text("\n".join([header] + day()) + "\n")
    cur.write_text("\n".join([header] + day()) + "\n")
    return ref, cur


if __name__ == "__main__":
    r, c = make(Path(__file__).parent / "data")
    print(f"wrote {r} / {c}")
    print("next: ddoc diff data/ref.csv data/cur.csv   # → ✅ OK 여야 한다")

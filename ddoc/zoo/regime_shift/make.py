"""Regime shift — 어느 날부터 세상이 바뀌었고, 되돌아오지 않는다.

소매 일별 판매 로그. ref = 안정기 60일, cur = 레짐 전환 후 60일:
단가가 한 단계 위로 이동했고(원자재/환율), 판매 채널 구성이
오프라인 중심 → 온라인 중심으로 재편됐다. 일시적 이벤트가 아니라
새 정상(new normal) — 기준선 자체를 다시 세워야 하는 종류의 변화.

기대 판정: DRIFT (severity high — price/channel 축이 임계 초과)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def make(out_dir: Path, *, seed: int = 7) -> tuple[Path, Path]:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    def days(n_days: int, price_mu: float, online_p: float) -> list[str]:
        rows = []
        for d in range(n_days):
            for _ in range(rng.integers(30, 50)):
                price = max(1.0, rng.normal(price_mu, price_mu * 0.08))
                channel = "online" if rng.random() < online_p else "store"
                qty = int(rng.integers(1, 5))
                rows.append(f"{d},{price:.0f},{channel},{qty}")
        return rows

    header = "day,price,channel,qty"
    ref = out_dir / "ref.csv"
    cur = out_dir / "cur.csv"
    ref.write_text("\n".join([header] + days(60, price_mu=100, online_p=0.25)) + "\n")
    cur.write_text("\n".join([header] + days(60, price_mu=180, online_p=0.80)) + "\n")
    return ref, cur


if __name__ == "__main__":
    r, c = make(Path(__file__).parent / "data")
    print(f"wrote {r} / {c}")
    print("next: ddoc diff data/ref.csv data/cur.csv --report note.html")

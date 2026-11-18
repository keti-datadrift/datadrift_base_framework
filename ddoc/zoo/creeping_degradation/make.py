"""Creeping degradation — 하루하루는 멀쩡해 보이는데, 한 달 전과
비교하면 센서가 죽어가고 있다.

온도 센서 로그(측정 단위 행). ref = 건강한 기준선 30일, cur = 열화가
누적된 **최근 2주**: 바이어스가 +8°C 수준까지 밀렸고 노이즈 폭이
커졌으며 포화 직전 스파이크가 늘었다. 어제-오늘 비교로는 안 잡히고,
열화 전 구간을 통째로 평균 내도 희석된다 — 기준선 vs 최근 창으로
비교해야 보이는 종류의 드리프트다.

기대 판정: DRIFT (reading 축 분포가 오른쪽으로 밀리고 퍼짐)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def make(out_dir: Path, *, seed: int = 11) -> tuple[Path, Path]:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    def window(bias_end: float, noise_end: float, spike_p: float,
               days: int = 30, frac_start: float = 0.0) -> list[str]:
        rows = []
        for d in range(days):
            frac = frac_start + (1.0 - frac_start) * (d / max(1, days - 1))
            bias = bias_end * frac
            noise = 0.6 + (noise_end - 0.6) * frac
            for h in range(24):
                # 시간당 4회 샘플링 — 측정 단위 로그
                for _ in range(4):
                    true_t = 20.0 + 6.0 * np.sin((h - 6) / 24 * 2 * np.pi)
                    reading = true_t + bias + rng.normal(0, noise)
                    if rng.random() < spike_p * frac:
                        reading += rng.choice([-1, 1]) * rng.uniform(10, 18)
                    rows.append(f"{h},{reading:.2f}")
        return rows

    header = "hour,reading"
    ref = out_dir / "ref.csv"
    cur = out_dir / "cur.csv"
    ref.write_text("\n".join([header] + window(bias_end=0.0, noise_end=0.6, spike_p=0.0)) + "\n")
    cur.write_text("\n".join(
        [header] + window(bias_end=8.0, noise_end=3.2, spike_p=0.08,
                          days=14, frac_start=0.55)) + "\n")
    return ref, cur


if __name__ == "__main__":
    r, c = make(Path(__file__).parent / "data")
    print(f"wrote {r} / {c}")
    print("next: ddoc diff data/ref.csv data/cur.csv --report note.html")

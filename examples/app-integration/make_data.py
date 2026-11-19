"""Write a baseline and a shifted CSV dataset for the integration demo.

    python make_data.py <out_dir>

Creates <out_dir>/baseline/sensors.csv and <out_dir>/today/sensors.csv.
The "today" data has a higher mean temperature and a different mix of
device types. Standard library only.
"""
import csv
import random
import sys
from pathlib import Path


def write(path: Path, *, temp_mean: float, devices: list, seed: int) -> None:
    rng = random.Random(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["temperature", "humidity", "device"])
        for _ in range(500):
            writer.writerow([
                round(rng.gauss(temp_mean, 2.0), 2),
                round(rng.gauss(45.0, 5.0), 2),
                rng.choice(devices),
            ])


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "source")
    write(out / "baseline" / "sensors.csv", temp_mean=21.0,
          devices=["a", "a", "b", "c"], seed=1)
    write(out / "today" / "sensors.csv", temp_mean=25.0,
          devices=["b", "c", "c", "c"], seed=2)
    print(f"wrote {out}/baseline and {out}/today")


if __name__ == "__main__":
    main()

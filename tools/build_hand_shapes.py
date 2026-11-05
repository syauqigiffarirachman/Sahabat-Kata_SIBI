"""Membuat sibi/data/hand_shapes.json dari dataset rekaman (training/dataset/*.csv).

Untuk tiap huruf diambil nilai median 21 landmark (x, y) dari seluruh frame,
(x, y, z; z dipakai untuk urutan tumpang-tindih jari) sehingga kamus dapat menampilkan gambar bentuk tangan tanpa file gambar.
Jalankan ulang setiap kali menambah rekaman huruf baru:

    python tools/build_hand_shapes.py
"""

import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATASET = ROOT / "training" / "dataset"
OUT = ROOT / "sibi" / "data" / "hand_shapes.json"


def median_shape(csv_path: Path):
    cols = [[[], [], []] for _ in range(21)]
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for i in range(21):
                cols[i][0].append(float(row[f"landmark_{i}_x"]))
                cols[i][1].append(float(row[f"landmark_{i}_y"]))
                cols[i][2].append(float(row[f"landmark_{i}_z"]))
    if not cols[0][0]:
        return None
    return [[round(statistics.median(a), 4) for a in c] for c in cols]


def main() -> None:
    shapes = {}
    for p in sorted(DATASET.glob("*.csv")):
        shape = median_shape(p)
        if shape:
            shapes[p.stem.upper()] = shape
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(shapes, separators=(",", ":")), encoding="utf-8")
    from sibi import ui

    ui.hand_shapes.cache_clear()
    n = ui.ensure_hand_files(force=True)
    print(f"{n} gambar SVG -> static/hands")
    print(f"{len(shapes)} bentuk tangan -> {OUT}: {', '.join(shapes)}")


if __name__ == "__main__":
    main()

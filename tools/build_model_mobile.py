"""Latih model huruf SIBI ringan untuk aplikasi HP dan ekspor ke JSON.

    python tools/build_model_mobile.py

Model desktop (Random Forest, 28 MB) terlalu berat untuk HP. Di sini dilatih
jaringan saraf kecil (MLP 63-128-64-26, ~20 ribu bobot) dari dataset yang sama,
dengan augmentasi agar tahan terhadap perbedaan kamera HP (rasio layar,
kemiringan tangan, jarak). Hasil: mobile/www/model/huruf.json (dipakai kamera.js).

Evaluasi memakai 20% rekaman TERAKHIR tiap huruf (bukan acak) agar frame yang
mirip tidak bocor ke data uji.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "mobile" / "www" / "model" / "huruf.json"


def muat():
    xs, ys, uji = [], [], []
    for f in sorted((ROOT / "training" / "dataset").glob("*.csv")):
        df = pd.read_csv(f)
        X = df[[c for c in df.columns if c.startswith("landmark_")]].to_numpy(np.float32)
        n = len(X)
        batas = int(n * 0.8)
        xs.append(X)
        ys.append(np.array([f.stem] * n))
        uji.append(np.arange(n) >= batas)
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(uji)


def normalisasi(P):
    """P: (N, 21, 3) -> (N, 63) sama persis dengan sibi/core/normalize.py."""
    P = P - P[:, :1, :]
    d = np.linalg.norm(P, axis=2).max(axis=1)
    d[d < 1e-6] = 1.0
    return (P / d[:, None, None]).reshape(len(P), 63)


def augmentasi(X, rng, kali=3):
    """Variasi realistis kamera HP: rotasi, rasio sumbu x/y, kedalaman, sedikit getar."""
    P = X.reshape(-1, 21, 3)
    out = [X]
    for _ in range(kali):
        Q = P.copy()
        a = rng.uniform(-0.30, 0.30, len(Q))  # +-17 derajat
        c, s = np.cos(a), np.sin(a)
        x, y = Q[:, :, 0].copy(), Q[:, :, 1].copy()
        Q[:, :, 0] = c[:, None] * x - s[:, None] * y
        Q[:, :, 1] = s[:, None] * x + c[:, None] * y
        Q[:, :, 0] *= rng.uniform(0.85, 1.15, len(Q))[:, None]  # rasio layar berbeda
        Q[:, :, 2] *= rng.uniform(0.7, 1.3, len(Q))[:, None]
        Q += rng.normal(0, 0.012, Q.shape)
        out.append(normalisasi(Q))
    return np.concatenate(out)


def main():
    rng = np.random.default_rng(42)
    X, y, uji = muat()
    Xtr, ytr, Xte, yte = X[~uji], y[~uji], X[uji], y[uji]
    reps = 4
    Xa = augmentasi(Xtr, rng, kali=reps - 1)
    ya = np.tile(ytr, reps)

    mlp = MLPClassifier(hidden_layer_sizes=(128, 64), activation="relu", alpha=1e-4,
                        batch_size=256, learning_rate_init=2e-3, max_iter=60,
                        early_stopping=True, n_iter_no_change=6, random_state=0)
    mlp.fit(Xa, ya)
    acc = float((mlp.predict(Xte) == yte).mean())

    rf = RandomForestClassifier(n_estimators=150, n_jobs=-1, random_state=0).fit(Xtr, ytr)
    acc_rf = float((rf.predict(Xte) == yte).mean())
    print(f"Akurasi data uji (20% rekaman terakhir): MLP HP {acc:.3f} | Random Forest desktop {acc_rf:.3f}")

    # Latih ulang dengan semua data untuk dipakai di HP
    Xa_all = augmentasi(X, rng, kali=reps - 1)
    mlp.set_params(early_stopping=False, max_iter=len(mlp.loss_curve_) + 2)
    mlp.fit(Xa_all, np.tile(y, reps))

    lapisan = [{"W": np.round(W, 5).tolist(), "b": np.round(b, 5).tolist()}
               for W, b in zip(mlp.coefs_, mlp.intercepts_)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "jenis": "mlp-relu-softmax",
        "kelas": [str(c) for c in mlp.classes_],
        "lapisan": lapisan,
        "akurasi_uji": round(acc, 4),
        "rasio_latih": 16 / 9,  # dataset direkam dengan kamera 1280x720 (sibi/core/camera.py)
    }, separators=(",", ":")), encoding="utf-8")
    print(f"Tersimpan {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

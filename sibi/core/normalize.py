"""Modul normalisasi koordinat landmark tangan untuk SIBI Translator.

Menstandarkan translasi dan skala titik tangan agar invariant terhadap
jarak tangan ke kamera serta posisi tangan di dalam frame video.
"""

from typing import List, Union
import numpy as np


def normalize_landmarks(
    landmarks: Union[List[List[float]], np.ndarray],
    as_numpy: bool = False
) -> Union[List[float], np.ndarray]:
    """Menstandarkan posisi dan ukuran koordinat tangan (21 landmark MediaPipe).

    Langkah-langkah:
    1. Validasi: Memastikan data landmark memiliki panjang 21 titik (x, y, z).
    2. Translasi: Menjadikan pergelangan tangan (titik index 0) sebagai titik pusat (0,0,0).
    3. Skala: Membagi seluruh koordinat dengan jarak terjauh dari pergelangan tangan,
       sehingga nilai berada dalam rentang seragam [-1.0, 1.0].

    Args:
        landmarks: Daftar 21 koordinat tangan [[x, y, z], ...].
        as_numpy: Jika True, kembalikan dalam bentuk np.ndarray 1D (panjang 63).

    Returns:
        Daftar 63 nilai float yang telah dinormalisasi, atau list kosong jika input tidak valid.
    """
    if landmarks is None or len(landmarks) != 21:
        return np.array([], dtype=np.float32) if as_numpy else []

    pts = np.asarray(landmarks, dtype=np.float32)

    if pts.shape != (21, 3):
        return np.array([], dtype=np.float32) if as_numpy else []

    # 1. Translasi: Wrist (index 0) sebagai titik asal (0, 0, 0)
    base = pts[0]
    pts = pts - base

    # 2. Skala: Jarak terjauh titik landmark dari wrist
    distances = np.linalg.norm(pts, axis=1)
    max_dist = float(np.max(distances))

    # 3. Normalisasi skala (hindari pembagian nol dengan epsilon)
    if max_dist > 1e-6:
        pts = pts / max_dist

    flat = pts.flatten()
    return flat if as_numpy else flat.tolist()

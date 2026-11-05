"""Modul klasifikasi isyarat kata SIBI (bentuk tangan diam & gerakan dalam rentang waktu).

Menganalisis rangkaian frame landmark tangan untuk mengenali kata sehari-hari seperti
HALO, YA, TIDAK, MAKAN, TERIMA KASIH, MAAF, SAYA, BAGUS, SAYANG, angka SATU-LIMA, dll.

Bila model kata terlatih (models/sibi_word_model.pkl) ada, model itulah yang dipakai.
Bila belum, dipakai pengenal berbasis aturan:
- bentuk jari (jari mana yang terbuka/terlipat) dihitung dari 63 koordinat ternormalisasi;
- gerak dihitung dari lintasan pergelangan di gambar (x, y, ukuran telapak) bila tersedia.

Logika yang sama ada di mobile/www/kamera.js (versi HP); jaga keduanya tetap sejalan.
"""

from pathlib import Path
import pickle
from typing import List, Optional, Sequence, Tuple

import numpy as np

# Kata yang dikenali pengenal aturan (lihat juga sibi/content.py: KATA_KAMERA).
KATA_GERAK = ["HALO", "YA", "TIDAK", "MAKAN", "TERIMA KASIH", "MAAF", "SAYA"]
KATA_DIAM = ["BAGUS", "SAYANG", "TELEPON", "SATU", "DUA", "TIGA", "EMPAT", "LIMA"]

# Pola jari (ibu jari, telunjuk, tengah, manis, kelingking) -> kata untuk pose diam.
POLA_DIAM = {
    (1, 1, 0, 0, 1): "SAYANG",
    (1, 0, 0, 0, 1): "TELEPON",
    (0, 1, 0, 0, 0): "SATU",
    (0, 1, 1, 0, 0): "DUA",
    (0, 1, 1, 1, 0): "TIGA",
    (1, 1, 1, 0, 0): "TIGA",
    (0, 1, 1, 1, 1): "EMPAT",
    (1, 1, 1, 1, 1): "LIMA",
}

_UJUNG = (8, 12, 16, 20)
_SENDI = (6, 10, 14, 18)


def _titik(frame: Sequence[float]) -> np.ndarray:
    return np.asarray(frame, dtype=np.float32).reshape(21, 3)[:, :2]


def bentuk_tangan(frame: Sequence[float]) -> dict:
    """Ciri bentuk tangan dari 63 fitur ternormalisasi (pergelangan di titik 0,0).

    Returns:
        dict: jari (tuple 5 nilai 0/1), jempol_atas (bool), kuncup (bool).
    """
    p = _titik(frame)
    telapak = float(np.linalg.norm(p[9])) or 1.0
    jari = []
    # ibu jari: ujungnya jauh dari pangkal telunjuk dan dari tengah telapak
    jari.append(int(np.linalg.norm(p[4] - p[5]) > 0.6 * telapak
                    and np.linalg.norm(p[4] - p[9]) > 0.75 * telapak))
    for u, s in zip(_UJUNG, _SENDI):
        jari.append(int(np.linalg.norm(p[u]) > np.linalg.norm(p[s]) * 1.15))
    # jempol ke atas: ujung ibu jari lebih tinggi dari semua titik lain (y gambar ke bawah)
    jempol_atas = bool(p[4, 1] < np.min(p[5:, 1]) - 0.15 * telapak)
    # kuncup: kelima ujung jari berkumpul, tapi jari tidak terlipat ke telapak (bukan kepalan)
    ujung = p[[4, 8, 12, 16, 20]]
    sebar = float(np.max(np.linalg.norm(ujung - ujung.mean(axis=0), axis=1)))
    kuncup = bool(sebar < 0.4 * telapak and np.linalg.norm(p[8]) > 1.2 * telapak)
    return {"jari": tuple(jari), "jempol_atas": jempol_atas, "kuncup": kuncup}


def jenis_tangan(frame: Sequence[float]) -> str:
    """Golongan bentuk tangan: kuncup / terbuka / tunjuk / kepal / jempol / lain."""
    b = bentuk_tangan(frame)
    j = b["jari"]
    if b["kuncup"]:
        return "kuncup"
    if sum(j[1:]) == 0:
        return "jempol" if j[0] and b["jempol_atas"] else "kepal"
    if sum(j[1:]) >= 4 or (sum(j[1:]) == 3 and j[0]):
        return "terbuka"
    if j[1] and not j[3] and not j[4]:
        return "tunjuk"
    return "lain"


def pose_diam(frame: Sequence[float]) -> Optional[str]:
    """Kata untuk bentuk tangan diam, atau None."""
    b = bentuk_tangan(frame)
    if b["kuncup"]:
        return None
    if b["jari"] == (1, 0, 0, 0, 0) and b["jempol_atas"]:
        return "BAGUS"
    return POLA_DIAM.get(b["jari"])


def bolak_balik(nilai: Sequence[float], ambang: float) -> int:
    """Berapa kali deret berbalik arah dengan ayunan minimal `ambang` (melambai, mengangguk)."""
    if len(nilai) < 3:
        return 0
    terendah = tertinggi = float(nilai[0])
    arah, ekstrem, balik = 0, 0.0, 0
    for v in map(float, nilai[1:]):
        if arah == 0:  # arah pertama: tunggu sampai ayunan cukup besar
            terendah, tertinggi = min(terendah, v), max(tertinggi, v)
            if v - terendah >= ambang:
                arah, ekstrem = 1, v
            elif tertinggi - v >= ambang:
                arah, ekstrem = -1, v
        elif arah == 1:
            if v > ekstrem:
                ekstrem = v
            elif ekstrem - v >= ambang:
                arah, ekstrem, balik = -1, v, balik + 1
        else:
            if v < ekstrem:
                ekstrem = v
            elif v - ekstrem >= ambang:
                arah, ekstrem, balik = 1, v, balik + 1
    return balik


def _mayoritas(nilai: List[str]) -> Tuple[str, float]:
    if not nilai:
        return "", 0.0
    uniq, n = np.unique(np.asarray(nilai), return_counts=True)
    i = int(np.argmax(n))
    return str(uniq[i]), float(n[i]) / len(nilai)


def tebak_dengan_gerak(frames: Sequence[Sequence[float]], gerak: Sequence[Sequence[float]]) -> Tuple[str, float]:
    """Tebak kata dari bentuk tangan + lintasan pergelangan.

    Args:
        frames: N frame berisi 63 fitur ternormalisasi.
        gerak: N baris (x, y, ukuran_telapak) pergelangan dalam koordinat gambar 0..1.
    """
    g = np.asarray(gerak, dtype=np.float32)
    if len(frames) < 8 or g.shape != (len(frames), 3):
        return "-", 0.0
    x, y, s = g[:, 0], g[:, 1], g[:, 2]
    ukuran = float(np.median(s)) or 0.1  # skala tangan di gambar: ambang ikut jarak ke kamera
    rentang_x, rentang_y = float(np.ptp(x)), float(np.ptp(y))
    jalur = float(np.sum(np.linalg.norm(np.diff(g[:, :2], axis=0), axis=1)))
    bersih = float(np.linalg.norm(g[-1, :2] - g[0, :2]))

    jenis, porsi = _mayoritas([jenis_tangan(f) for f in frames])
    ujung_x = [float(f[24]) for f in frames]  # ujung telunjuk relatif pergelangan (melambai/menggoyang)

    balik_x = bolak_balik(x, 0.25 * ukuran)
    balik_y = bolak_balik(y, 0.2 * ukuran)
    balik_s = bolak_balik(s, 0.08 * ukuran)
    balik_ujung = bolak_balik(ujung_x, 0.15)

    if porsi >= 0.6:
        if jenis == "kuncup" and (balik_y >= 2 or balik_s >= 2 or balik_x >= 2):
            return "MAKAN", 0.84
        if jenis == "terbuka" and (balik_x >= 2 or balik_ujung >= 2):
            return "HALO", min(0.93, 0.8 + 0.03 * max(balik_x, balik_ujung))
        if jenis == "tunjuk" and (balik_x >= 2 or balik_ujung >= 2):
            return "TIDAK", 0.86
        if jenis == "kepal" and _melingkar(rentang_x, rentang_y, jalur, bersih, ukuran):
            return "MAAF", 0.84
        if jenis == "kepal" and balik_y >= 2 and rentang_x < rentang_y * 0.6:
            return "YA", 0.85
        turun = float(y[-1] - y[0])
        if jenis == "terbuka" and turun > 0.5 * ukuran and turun > 0.7 * rentang_y and balik_x < 2:
            return "TERIMA KASIH", 0.82
        if jenis == "tunjuk" and turun > 0.45 * ukuran and turun > 0.7 * rentang_y:
            return "SAYA", 0.8

    # Pose diam: tangan tenang dan bentuknya sama hampir di sepanjang jendela
    tenang = rentang_x < 0.18 * ukuran and rentang_y < 0.18 * ukuran and float(np.ptp(s)) < 0.15 * ukuran
    if tenang:
        kata, porsi_kata = _mayoritas([pose_diam(f) or "-" for f in frames])
        if kata != "-" and porsi_kata >= 0.75:
            return kata, round(0.8 + 0.12 * porsi_kata, 3)
    return "-", 0.0


def _melingkar(rx: float, ry: float, jalur: float, bersih: float, ukuran: float) -> bool:
    besar = max(rx, ry)
    return (rx > 0.3 * ukuran and ry > 0.3 * ukuran and 0.4 < rx / max(ry, 1e-6) < 2.5
            and jalur > 2.2 * besar and bersih < 0.5 * besar)


class SIBIWordClassifier:
    """Pengklasifikasi kata berbasis rangkaian frame landmark."""

    DEFAULT_LABELS = KATA_GERAK + KATA_DIAM

    def __init__(
        self,
        sequence_length: int = 20,
        model_path: Optional[str] = None
    ):
        """Inisialisasi pengklasifikasi kata.

        Args:
            sequence_length: Jumlah frame yang dianalisis (default: 20 frame ~ 0.7 - 1 detik).
            model_path: Path opsional ke file model kata (.pkl).
        """
        self.sequence_length = sequence_length
        self.model = None
        self.labels = list(self.DEFAULT_LABELS)
        self.model_path = self._resolve_model_path(model_path)

        if self.model_path and Path(self.model_path).is_file():
            try:
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                if hasattr(self.model, 'classes_'):
                    self.labels = [str(c) for c in self.model.classes_]
            except Exception as e:
                print(f"Peringatan: Gagal memuat model kata dari {self.model_path}: {e}")
                self.model = None

    def _resolve_model_path(self, custom_path: Optional[str]) -> Optional[str]:
        """Mencari lokasi model kata secara fleksibel."""
        if custom_path:
            # Path yang diminta secara eksplisit dipakai apa adanya; jangan diam-diam
            # memuat model lain bila file itu tidak ada.
            return str(Path(custom_path).resolve())

        root_dir = Path(__file__).resolve().parents[2]
        candidates = [
            root_dir / "models" / "sibi_word_model.pkl",
            Path.cwd() / "models" / "sibi_word_model.pkl",
            Path.cwd() / "sibi_word_model.pkl",
        ]
        for p in candidates:
            if p.is_file():
                return str(p.resolve())

        return str((root_dir / "models" / "sibi_word_model.pkl").resolve())

    @property
    def is_loaded(self) -> bool:
        """Apakah model ML kata sudah dilatih dan dimuat."""
        return self.model is not None

    def predict(
        self,
        sequence_frames: List[List[float]],
        wrists: Optional[Sequence[Sequence[float]]] = None,
    ) -> Tuple[str, float]:
        """Menebak kata dari rangkaian frame gerakan tangan.

        Args:
            sequence_frames: List frame, masing-masing berisi 63 koordinat ternormalisasi.
            wrists: Opsional, lintasan pergelangan per frame (x, y, ukuran_telapak) dalam
                koordinat gambar. Tanpa ini hanya aturan lama (4 kata) yang dipakai.

        Returns:
            Tuple (kata_tebakan, confidence); '-' bila belum cukup/tidak dikenali.
        """
        if not sequence_frames or len(sequence_frames) < self.sequence_length:
            return "-", 0.0

        frames_to_use = sequence_frames[-self.sequence_length:]

        if self.model is not None:
            try:
                flat_data = np.asarray(frames_to_use, dtype=np.float32).flatten().reshape(1, -1)
                word = str(self.model.predict(flat_data)[0])
                if hasattr(self.model, 'predict_proba'):
                    prob = self.model.predict_proba(flat_data)[0]
                    confidence = float(np.max(prob))
                else:
                    confidence = 1.0
                return word, confidence
            except Exception as e:
                print(f"Kesalahan prediksi model kata: {e}")
                return "-", 0.0

        if wrists is not None and len(wrists) >= self.sequence_length:
            return tebak_dengan_gerak(frames_to_use, list(wrists)[-self.sequence_length:])
        return self._heuristic_gesture_detection(frames_to_use)

    def _heuristic_gesture_detection(self, frames: List[List[float]]) -> Tuple[str, float]:
        """Aturan lama (tanpa lintasan pergelangan): pose diam + 4 kata gerak dasar."""
        arr = np.asarray(frames, dtype=np.float32)  # shape: (N, 63)
        if arr.shape != (self.sequence_length, 63):
            return "-", 0.0

        awal = arr[0]
        akhir = arr[-1]
        kecepatan_rata = float(np.mean(np.abs(akhir - awal))) * 100.0

        if kecepatan_rata < 1.2:
            # tangan diam: coba kenali pose diam (BAGUS, SAYANG, angka, ...)
            kata, porsi = _mayoritas([pose_diam(f) or "-" for f in arr])
            if kata != "-" and porsi >= 0.75:
                return kata, round(0.8 + 0.12 * porsi, 3)
            return "-", 0.0

        dx = float(akhir[24] - awal[24])
        dy = float(akhir[25] - awal[25])

        osilasi_x = np.std(arr[:, 24])
        if osilasi_x > 0.08 and abs(dx) < 0.15:
            return "HALO", float(min(0.92, 0.70 + osilasi_x * 2.0))
        if dy > 0.15 and abs(dx) < 0.12:
            return "TERIMA KASIH", float(min(0.90, 0.72 + dy))
        if kecepatan_rata > 2.5:
            return "MAAF", 0.82
        if dy < -0.12:
            return "SAYA", 0.80
        return "-", 0.0

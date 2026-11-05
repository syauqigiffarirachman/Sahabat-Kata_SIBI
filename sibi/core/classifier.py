"""Modul klasifikasi huruf alfabet SIBI (Sistem Isyarat Bahasa Indonesia).

Menggunakan model Machine Learning (Scikit-Learn Random Forest) yang dilatih
dari koordinat 21 titik sendi tangan ternormalisasi.
"""

from pathlib import Path
import pickle
from typing import List, Optional, Tuple
import numpy as np


class SIBIClassifier:
    """Pengklasifikasi huruf SIBI statis berbasis model Scikit-Learn."""

    EXPECTED_FEATURES = 63  # 21 landmark x 3 sumbu (x, y, z)

    def __init__(self, model_path: Optional[str] = None):
        """Inisialisasi pengklasifikasi SIBI.

        Args:
            model_path: Path opsional ke file model (.pkl).
        """
        self.model = None
        self.labels: List[str] = []
        self.model_path = self._resolve_model_path(model_path)

        if self.model_path and Path(self.model_path).is_file():
            try:
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                if hasattr(self.model, 'classes_'):
                    self.labels = [str(c) for c in self.model.classes_]
            except Exception as e:
                print(f"Peringatan: Gagal memuat model SIBI dari {self.model_path}: {e}")
                self.model = None
                self.labels = []
        else:
            print(f"Peringatan: Model {self.model_path} tidak ditemukan.")

    def _resolve_model_path(self, custom_path: Optional[str]) -> Optional[str]:
        """Menemukan path file model secara fleksibel."""
        if custom_path:
            # Path yang diminta secara eksplisit dipakai apa adanya; jangan diam-diam
            # memuat model lain bila file itu tidak ada.
            return str(Path(custom_path).resolve())

        root_dir = Path(__file__).resolve().parents[2]
        candidates = [
            root_dir / "models" / "sibi_model.pkl",
            Path.cwd() / "models" / "sibi_model.pkl",
            Path.cwd() / "sibi_model.pkl",
        ]
        for p in candidates:
            if p.is_file():
                return str(p.resolve())

        return str((root_dir / "models" / "sibi_model.pkl").resolve())

    @property
    def is_loaded(self) -> bool:
        """Memeriksa apakah model AI berhasil dimuat."""
        return self.model is not None

    def predict(self, normalized_landmarks: List[float]) -> Tuple[str, float]:
        """Menebak huruf dari koordinat landmark tangan ternormalisasi.

        Args:
            normalized_landmarks: List 63 float hasil normalisasi landmark.

        Returns:
            Tuple (huruf_tebakan, confidence):
                huruf_tebakan: Label huruf (misal 'A', 'B'), atau '-' jika gagal.
                confidence: Nilai keyakinan model (0.0 sampai 1.0).
        """
        if not self.is_loaded or not normalized_landmarks:
            return "-", 0.0

        if len(normalized_landmarks) != self.EXPECTED_FEATURES:
            return "-", 0.0

        try:
            input_data = np.asarray(normalized_landmarks, dtype=np.float32).reshape(1, -1)
            huruf_tebakan = str(self.model.predict(input_data)[0])

            if hasattr(self.model, 'predict_proba'):
                probabilitas = self.model.predict_proba(input_data)[0]
                confidence = float(np.max(probabilitas))
            else:
                confidence = 1.0

            return huruf_tebakan, confidence
        except Exception as e:
            print(f"Kesalahan saat prediksi: {e}")
            return "-", 0.0

    def predict_top_k(
        self,
        normalized_landmarks: List[float],
        k: int = 3
    ) -> List[Tuple[str, float]]:
        """Mendapatkan top-k kandidat tebakan beserta probabilitasnya.

        Args:
            normalized_landmarks: List 63 float koordinat ternormalisasi.
            k: Jumlah kandidat teratas yang diinginkan.

        Returns:
            List tuple [(huruf, confidence), ...] terurut menurun.
        """
        if not self.is_loaded or not normalized_landmarks or len(normalized_landmarks) != self.EXPECTED_FEATURES:
            return []

        try:
            input_data = np.asarray(normalized_landmarks, dtype=np.float32).reshape(1, -1)
            if hasattr(self.model, 'predict_proba'):
                probs = self.model.predict_proba(input_data)[0]
                classes = [str(c) for c in self.model.classes_]
                indexed = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)
                return [(label, float(score)) for label, score in indexed[:k]]
            else:
                pred = str(self.model.predict(input_data)[0])
                return [(pred, 1.0)]
        except Exception as e:
            print(f"Kesalahan saat predict_top_k: {e}")
            return []

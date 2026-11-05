"""Modul deteksi tangan menggunakan MediaPipe Tasks HandLandmarker.

Mendeteksi sendi-sendi tangan (21 3D landmarks) dari frame gambar/video
serta menggambar visualisasi kerangka tangan.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class HandDetector:
    """Pendeteksi tangan berbasis MediaPipe Tasks Vision API."""

    # Koneksi garis antar sendi tangan (0 sampai 20)
    CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),        # Jempol
        (0, 5), (5, 6), (6, 7), (7, 8),        # Telunjuk
        (5, 9), (9, 10), (10, 11), (11, 12),   # Jari Tengah
        (9, 13), (13, 14), (14, 15), (15, 16), # Jari Manis
        (13, 17), (17, 18), (18, 19), (19, 20),# Kelingking
        (0, 17)                                # Telapak bawah
    ]

    MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/1/hand_landmarker.task"
    )

    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.6,
        min_presence_confidence: float = 0.6,
        min_tracking_confidence: float = 0.6,
        model_path: Optional[str] = None
    ):
        """Inisialisasi HandDetector.

        Args:
            max_num_hands: Jumlah maksimal tangan yang dideteksi (default: 2).
            min_detection_confidence: Ambang batas minimal deteksi tangan.
            min_presence_confidence: Ambang batas minimal keberadaan tangan.
            min_tracking_confidence: Ambang batas minimal tracking tangan.
            model_path: Path opsional ke file model hand_landmarker.task.
        """
        self.model_path = self._resolve_model_path(model_path)
        self.last_handedness: List[str] = []

        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
            running_mode=vision.RunningMode.IMAGE
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.connections = self.CONNECTIONS

    def _resolve_model_path(self, custom_path: Optional[str]) -> str:
        """Mencari lokasi model hand_landmarker.task secara robust."""
        candidate_paths = []
        if custom_path:
            candidate_paths.append(Path(custom_path))

        # 1. Root direktori proyek
        root_dir = Path(__file__).resolve().parents[2]
        candidate_paths.append(root_dir / "hand_landmarker.task")
        candidate_paths.append(root_dir / "models" / "hand_landmarker.task")

        # 2. Direktori kerja aktif saat ini
        candidate_paths.append(Path.cwd() / "hand_landmarker.task")
        candidate_paths.append(Path.cwd() / "models" / "hand_landmarker.task")

        # Periksa apakah model sudah ada di salah satu path
        for p in candidate_paths:
            if p.is_file():
                return str(p)

        # Jika belum ada di manapun, unduh ke root direktori proyek
        target_path = root_dir / "hand_landmarker.task"
        print(f"Mengunduh model AI pendeteksi tangan ke {target_path} (hanya sekali)...")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(self.MODEL_URL, str(target_path))
        print("Selesai mengunduh model hand_landmarker.task!")
        return str(target_path)

    def process(
        self,
        frame,
        draw: bool = True
    ) -> Tuple[any, List[List[List[float]]]]:
        """Memproses frame gambar untuk mendeteksi sendi tangan.

        Args:
            frame: Gambar format BGR dari OpenCV.
            draw: Jika True, gambar titik sendi dan garis kerangka di frame.

        Returns:
            Tuple (frame, landmarks_data):
                frame: Frame gambar (dengan atau tanpa visualisasi sendi).
                landmarks_data: List berisi koordinat [[x, y, z], ...] untuk setiap tangan.
        """
        if frame is None or frame.size == 0:
            self.last_handedness = []
            return frame, []

        # Konversi BGR ke RGB untuk MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        detection_result = self.detector.detect(mp_image)

        landmarks_data: List[List[List[float]]] = []
        self.last_handedness = []

        if detection_result.handedness:
            for handedness_list in detection_result.handedness:
                if handedness_list:
                    self.last_handedness.append(handedness_list[0].category_name)

        if detection_result.hand_landmarks:
            h, w, _ = frame.shape

            for hand_landmarks in detection_result.hand_landmarks:
                landmark_list: List[List[float]] = []

                for lm in hand_landmarks:
                    landmark_list.append([lm.x, lm.y, lm.z])
                    if draw:
                        x, y = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)

                if draw:
                    for conn in self.connections:
                        pt1 = hand_landmarks[conn[0]]
                        pt2 = hand_landmarks[conn[1]]
                        x1, y1 = int(pt1.x * w), int(pt1.y * h)
                        x2, y2 = int(pt2.x * w), int(pt2.y * h)
                        cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                landmarks_data.append(landmark_list)

        return frame, landmarks_data

    def close(self):
        """Menutup dan membebaskan resource detector MediaPipe."""
        if hasattr(self, 'detector') and self.detector:
            self.detector.close()

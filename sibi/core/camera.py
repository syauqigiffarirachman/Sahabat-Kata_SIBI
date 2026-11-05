"""Pembuka kamera yang tahan masalah backend Windows (MSMF sering gagal membaca frame)."""

import sys

import cv2


def open_camera(preferred_index: int = 0, width: int = 1280, height: int = 720):
    """Coba beberapa backend/indeks kamera, kembalikan VideoCapture yang benar-benar bisa membaca frame.

    Urutan di Windows: DirectShow lebih dulu (paling stabil), lalu default, lalu MSMF.
    Mengembalikan None bila semua gagal.
    """
    if sys.platform == "win32":
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY, cv2.CAP_MSMF]
    else:
        backends = [cv2.CAP_ANY]
    indices = [preferred_index] + [i for i in range(3) if i != preferred_index]

    for index in indices:
        for backend in backends:
            cap = cv2.VideoCapture(index, backend)
            if not cap.isOpened():
                cap.release()
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            # Kamera kadang butuh beberapa frame awal sebelum benar-benar siap.
            for _ in range(15):
                ok, _frame = cap.read()
                if ok:
                    return cap
            cap.release()
    return None


CAMERA_HELP = (
    "Kamera tidak dapat dibuka. Cek: (1) tutup aplikasi lain yang memakai kamera "
    "(Zoom, Teams, tab browser/Streamlit, desktop_app.py); (2) Windows Settings > Privacy > "
    "Camera: izinkan 'Desktop apps' mengakses kamera; (3) cabut-pasang webcam USB."
)

import cv2
import mediapipe as mp

# import tensorflow as tf  <-- Dimatikan sementara

def test_imports():
    """Memastikan semua library utama dapat di-import tanpa error."""
    assert cv2.__version__ is not None
    assert mp.__version__ is not None
    # assert tf.__version__ is not None  <-- Dimatikan sementara
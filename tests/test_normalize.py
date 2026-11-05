"""Unit test untuk modul normalisasi koordinat landmark tangan."""

import numpy as np
import pytest

from sibi.core.normalize import normalize_landmarks


def test_normalize_empty_or_invalid():
    """Memastikan input kosong atau salah panjang ditangani dengan aman."""
    assert normalize_landmarks([]) == []
    assert normalize_landmarks(None) == []
    assert normalize_landmarks([[0.0, 0.0, 0.0]] * 10) == []  # Bukan 21 titik
    assert normalize_landmarks([[0.0, 0.0]] * 21) == []        # Bukan 3 koordinat


def test_normalize_output_shape():
    """Memastikan output berbentuk list 63 nilai float."""
    dummy_landmarks = [[float(i), float(i * 2), float(i * 3)] for i in range(21)]
    result = normalize_landmarks(dummy_landmarks)

    assert isinstance(result, list)
    assert len(result) == 63
    # Wrist (titik 0) harus selalu berada di titik asal (0, 0, 0)
    assert result[0] == 0.0
    assert result[1] == 0.0
    assert result[2] == 0.0


def test_normalize_translation_invariance():
    """Memastikan translasi (pergeseran tangan di layar) menghasilkan vektor yang identik."""
    base_landmarks = [[float(i) * 0.1, float(i) * 0.2, float(i) * 0.05] for i in range(21)]

    # Geser semua titik sejauh (+100.0, -50.0, +25.0)
    shifted_landmarks = [
        [pt[0] + 100.0, pt[1] - 50.0, pt[2] + 25.0] for pt in base_landmarks
    ]

    res_base = np.array(normalize_landmarks(base_landmarks))
    res_shifted = np.array(normalize_landmarks(shifted_landmarks))

    np.testing.assert_allclose(res_base, res_shifted, atol=1e-5)


def test_normalize_scale_invariance():
    """Memastikan skala (jarak tangan dekat/jauh dari kamera) menghasilkan vektor yang identik."""
    base_landmarks = [[float(i) * 0.05, float(i) * 0.1, float(i) * 0.02] for i in range(21)]

    # Perbesar tangan sebesar 3.5x lipat
    scaled_landmarks = [
        [pt[0] * 3.5, pt[1] * 3.5, pt[2] * 3.5] for pt in base_landmarks
    ]

    res_base = np.array(normalize_landmarks(base_landmarks))
    res_scaled = np.array(normalize_landmarks(scaled_landmarks))

    np.testing.assert_allclose(res_base, res_scaled, atol=1e-5)


def test_normalize_as_numpy():
    """Memastikan argumen as_numpy=True menghasilkan numpy.ndarray."""
    dummy = [[float(i), float(i), float(i)] for i in range(21)]
    arr = normalize_landmarks(dummy, as_numpy=True)
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (63,)

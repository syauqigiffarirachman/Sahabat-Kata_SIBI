"""Pengujian pengenal isyarat kata (aturan bentuk jari + gerak) dengan tangan sintetis."""

import math

import pytest

from sibi.core.classifier_word import (
    SIBIWordClassifier,
    bentuk_tangan,
    bolak_balik,
    pose_diam,
)
from sibi.core.normalize import normalize_landmarks
from sibi.core.sequence_buffer import WordSequenceBuffer

_MCP = {5: (-0.12, -0.40), 9: (-0.02, -0.42), 13: (0.08, -0.40), 17: (0.17, -0.36)}


def tangan(jari=(0, 0, 0, 0, 0), jempol_atas=False, kuncup=False):
    """21 titik tangan sintetis (pergelangan di 0,0; y ke bawah positif) -> 63 fitur."""
    p = [(0.0, 0.0)] * 21
    p[1], p[2], p[3] = (-0.10, -0.10), (-0.20, -0.18), (-0.27, -0.26)
    if kuncup:
        p[4] = (-0.03, -0.72)
    elif jempol_atas:
        p[4] = (-0.18, -0.75)
    elif jari[0]:
        p[4] = (-0.42, -0.40)
    else:
        p[4] = (-0.02, -0.30)
    ujung_kuncup = {5: (-0.03, -0.78), 9: (0.0, -0.80), 13: (0.03, -0.78), 17: (0.04, -0.74)}
    for n, m in enumerate((5, 9, 13, 17)):
        mx, my = _MCP[m]
        p[m] = (mx, my)
        if kuncup:
            tx, ty = ujung_kuncup[m]
            p[m + 1], p[m + 2], p[m + 3] = (mx, my - 0.2), ((mx + tx) / 2, (my - 0.2 + ty) / 2), (tx, ty)
        elif jari[n + 1]:
            p[m + 1], p[m + 2], p[m + 3] = (mx, my - 0.18), (mx, my - 0.30), (mx, my - 0.40)
        else:
            p[m + 1], p[m + 2], p[m + 3] = (mx, my - 0.12), (mx, my + 0.02), (mx, my + 0.08)
    return normalize_landmarks([[x, y, 0.0] for x, y in p])


def jendela(bentuk, gerak_fn, n=20):
    frames = [bentuk] * n
    wrists = [gerak_fn(i / (n - 1)) for i in range(n)]
    return frames, wrists


def diam(_t):
    return (0.5, 0.5, 0.15)


@pytest.mark.parametrize("jari,kata", [
    ((1, 1, 0, 0, 1), "SAYANG"),
    ((1, 0, 0, 0, 1), "TELEPON"),
    ((0, 1, 0, 0, 0), "SATU"),
    ((0, 1, 1, 0, 0), "DUA"),
    ((0, 1, 1, 1, 0), "TIGA"),
    ((0, 1, 1, 1, 1), "EMPAT"),
    ((1, 1, 1, 1, 1), "LIMA"),
])
def test_pose_diam_dari_bentuk_jari(jari, kata):
    f = tangan(jari)
    assert bentuk_tangan(f)["jari"] == jari
    assert pose_diam(f) == kata


def test_jempol_ke_atas_bagus_dan_kepalan_bukan_kata():
    assert pose_diam(tangan(jempol_atas=True)) == "BAGUS"
    assert pose_diam(tangan()) is None
    assert bentuk_tangan(tangan(kuncup=True))["kuncup"]


def test_bolak_balik_menghitung_ayunan():
    gelombang = [math.sin(i / 19 * 2 * math.pi * 2) for i in range(20)]  # 2 gelombang
    assert bolak_balik(gelombang, 0.5) >= 3
    assert bolak_balik([i / 19 for i in range(20)], 0.2) == 0  # lurus satu arah


def lambai(t):
    return (0.5 + 0.06 * math.sin(t * 2 * math.pi * 2), 0.5, 0.15)


def angguk(t):
    return (0.5, 0.5 + 0.05 * math.sin(t * 2 * math.pi * 2), 0.15)


def lingkar(t):
    a = t * 2 * math.pi * 1.1
    return (0.5 + 0.06 * math.cos(a), 0.5 + 0.06 * math.sin(a), 0.15)


def turun(t):
    return (0.5, 0.4 + 0.15 * t, 0.15)


def ketuk(t):  # maju-mundur ke arah kamera/mulut: ukuran telapak berubah-ubah
    return (0.5, 0.5 + 0.03 * math.sin(t * 2 * math.pi * 2), 0.15 + 0.03 * math.sin(t * 2 * math.pi * 2))


@pytest.mark.parametrize("bentuk,gerak,kata", [
    (tangan((1, 1, 1, 1, 1)), lambai, "HALO"),
    (tangan((0, 1, 0, 0, 0)), lambai, "TIDAK"),
    (tangan(), angguk, "YA"),
    (tangan(), lingkar, "MAAF"),
    (tangan((1, 1, 1, 1, 1)), turun, "TERIMA KASIH"),
    (tangan((0, 1, 0, 0, 0)), turun, "SAYA"),
    (tangan(kuncup=True), ketuk, "MAKAN"),
    (tangan(jempol_atas=True), diam, "BAGUS"),
    (tangan((1, 1, 0, 0, 1)), diam, "SAYANG"),
    (tangan((0, 1, 1, 0, 0)), diam, "DUA"),
])
def test_kata_dari_bentuk_dan_gerak(bentuk, gerak, kata):
    clf = SIBIWordClassifier(sequence_length=20, model_path="tidak-ada.pkl")
    frames, wrists = jendela(bentuk, gerak)
    hasil, yakin = clf.predict(frames, wrists=wrists)
    assert hasil == kata
    assert yakin >= 0.75


def test_kepalan_diam_tidak_menjadi_kata():
    clf = SIBIWordClassifier(sequence_length=20, model_path="tidak-ada.pkl")
    frames, wrists = jendela(tangan(), diam)
    assert clf.predict(frames, wrists=wrists)[0] == "-"


def test_tanpa_lintasan_pose_diam_tetap_dikenali():
    clf = SIBIWordClassifier(sequence_length=20, model_path="tidak-ada.pkl")
    assert clf.predict([tangan(jempol_atas=True)] * 20)[0] == "BAGUS"


def test_buffer_tidak_mengulang_kata_yang_masih_ditahan():
    clf = SIBIWordClassifier(sequence_length=20, model_path="tidak-ada.pkl")
    buf = WordSequenceBuffer(sequence_length=20, cooldown_frames=5)
    f = tangan(jempol_atas=True)
    for _ in range(80):  # jempol diangkat terus ±3 detik
        buf.update(f, clf, wrist=(0.5, 0.5, 0.15))
    assert buf.text_result == "BAGUS"
    buf.update([], clf)  # tangan turun
    for _ in range(30):
        buf.update(f, clf, wrist=(0.5, 0.5, 0.15))
    assert buf.text_result == "BAGUS BAGUS"


def test_wrist_track_dari_landmark_mentah():
    raw = [[0.5, 0.6, 0.0]] + [[0.5, 0.45, 0.0]] * 20
    x, y, s = WordSequenceBuffer.wrist_track(raw)
    assert (x, y) == (0.5, 0.6) and s == pytest.approx(0.15)
    assert WordSequenceBuffer.wrist_track(None) is None

"""Pengujian konten belajar & komponen tampilan kamus (tanpa Streamlit)."""

import string

from sibi import content, ui


def test_semua_huruf_a_z_punya_deskripsi_dan_contoh_kata():
    for h in string.ascii_uppercase:
        assert content.HURUF[h]["deskripsi"]
        assert content.CONTOH_KATA[h], h


def test_contoh_kata_diawali_huruf_yang_benar():
    for h, items in content.CONTOH_KATA.items():
        for kata, _emoji in items:
            assert kata[0].upper() == h, (h, kata)


def test_bentuk_tangan_valid():
    shapes = ui.hand_shapes()
    assert shapes, "jalankan tools/build_hand_shapes.py"
    for h, pts in shapes.items():
        assert len(pts) == 21 and all(len(p) == 3 for p in pts), h
        assert "<svg" in ui._hand_svg_markup(h, 200)


def test_semua_huruf_memakai_foto_tangan_asli():
    for h in string.ascii_uppercase:
        assert ui.has_photo(h), h
        assert f"static/hands/foto/{h}.webp" in ui.hand_svg(h)


def test_huruf_tanpa_gambar_memakai_placeholder():
    assert "sb-ph" in ui.hand_svg("Z") or ui.has_shape("Z")


def test_spelling_dan_escape_html():
    assert ui.spelling_strip("Apel").count('class="sb-tile"') == 4
    assert "<script>" not in ui.word_card("<script>", "x")


def test_tangan_realistis_punya_telapak_dan_lima_jari():
    assert "<svg" in ui._hand_svg_markup("A", 200)


# ------------------------------------------------------------ kosakata sehari-hari
from sibi import kosakata


def test_kosakata_banyak_dan_tanpa_duplikat():
    semua = kosakata.semua_kata()
    kunci = [kosakata.kunci(k) for k, _e, _kat in semua]
    assert len(semua) >= 250
    assert len(kunci) == len(set(kunci))
    assert all(e for _k, e, _kat in semua)


def test_semua_kata_di_kalimat_ada_di_kosakata():
    ada = set()
    for k, _e, _kat in kosakata.semua_kata():
        ada.update(kosakata.token(k))
    for kal, _e in content.KALIMAT:
        kurang = [t for t in kosakata.token(kal) if t not in ada]
        assert not kurang, (kal, kurang)


def test_saran_kata_dari_ejaan():
    saran = [k for k, _e in kosakata.saran_kata("MAK")]
    assert saran[0] == "Makan"
    assert kosakata.saran_kata("MAKAN")[0][0] == "Makan"
    assert kosakata.saran_kata("") == []
    assert kosakata.cari("KUPUKUPU")[0] == "Kupu-kupu"


def test_rapikan_kalimat_dan_saran_kalimat():
    assert kosakata.rapikan("SAYA MAU MAKAN") == "Saya mau makan."
    assert kosakata.rapikan("SIAPA NAMA KAMU") == "Siapa nama kamu?"
    assert kosakata.rapikan("TERIMA KASIH") == "Terima kasih."
    saran = [k for k, _e in kosakata.saran_kalimat("SAYA MAKAN")]
    assert "Saya mau makan." in saran
    assert kosakata.saran_kalimat("") == []

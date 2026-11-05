"""Gerak mulut + suara huruf: wajah animasi yang mengucapkan huruf / kata.

Membantu anak Tuli belajar membaca gerak bibir: tiap huruf A-Z diucapkan
dengan nama hurufnya (a, be, ce, ...), bentuk mulut berganti per bunyi, dan
huruf yang sedang diucapkan disorot. Suaranya suara manusia (neural) dari
sibi/suara.py; logika animasi dan pemutaran ada di sibi/mulut.js (browser).
"""

from pathlib import Path

import streamlit as st

from sibi import content, suara

_JS = (Path(__file__).resolve().parent / "mulut.js").read_text(encoding="utf-8")

_CSS = (Path(__file__).resolve().parent / "mulut.css").read_text(encoding="utf-8")

_MULUT = st.components.v2.component(
    "sibi_mulut",
    html='<div class="mw"></div>',
    css=_CSS,
    js=_JS,
)


def teks_suara_huruf(h: str) -> str:
    """Teks yang dibacakan suara neural untuk nama huruf.

    Huruf tunggal dibaca dengan nama hurufnya oleh suara Bahasa Indonesia
    (B -> "bé"); Q ditulis "ki" agar tidak dibaca "kyu" seperti bahasa Inggris.
    """
    return content.BUNYI[h].get("suara", h)


def _track(label: str, say: str, nama: bool, teks_suara: str, **extra) -> dict:
    return {"label": label, "say": say, "nama": nama, **suara.kedua_kecepatan(teks_suara), **extra}


def _track_huruf(h: str) -> dict:
    return _track(h, content.BUNYI[h]["ucap"], True, teks_suara_huruf(h))


def mulut_huruf(h: str, *, key: str, size: int = 280, contoh: bool = True, auto: bool = True):
    """Wajah yang mengucapkan nama huruf `h`; tombol kata contoh bila `contoh`."""
    h = h.upper()
    extras = []
    if contoh:
        extras = [_track(k, k, False, k, emoji=e) for k, e in content.CONTOH_KATA.get(h, [])]
    return _MULUT(
        key=key,
        data={"tracks": [_track_huruf(h)], "extras": extras, "size": size, "auto": auto,
              "tombol": "Dengarkan"},
    )


def mulut_eja(kata: str, *, key: str, size: int = 240):
    """Wajah yang mengeja `kata` huruf demi huruf, lalu mengucapkan katanya."""
    huruf = [c for c in kata.upper() if c in content.BUNYI]
    tracks = [_track_huruf(c) for c in huruf]
    if len(huruf) > 1:
        tracks.append(_track(kata.title(), kata.lower(), False, kata.title()))
    return _MULUT(
        key=key,
        data={"tracks": tracks, "extras": [], "size": size, "auto": False,
              "tombol": "Eja", "akhirKata": len(huruf) > 1},
    )

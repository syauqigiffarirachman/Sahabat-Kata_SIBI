"""Kosakata sehari-hari anak: daftar kata, saran kata saat mengeja, dan saran kalimat.

Dipakai oleh kamus, kuis, dan penerjemah kamera (Streamlit). Versi HP memakai logika
yang sama di mobile/www/kosakata.js (data dari data/konten.json).
"""

from __future__ import annotations

import re
from functools import lru_cache

from sibi import content

LAIN = "Benda lain"


def kunci(teks: str) -> str:
    """Huruf saja, kapital: 'Kupu-kupu' -> 'KUPUKUPU' (cara kata dieja dengan jari)."""
    return re.sub(r"[^A-Z]", "", str(teks).upper())


def token(teks: str) -> list[str]:
    """Kata-kata dalam teks sebagai kunci: 'Halo, apa kabar?' -> ['HALO', 'APA', 'KABAR']."""
    return [kunci(t) for t in re.split(r"[\s,.!?]+", str(teks)) if kunci(t)]


@lru_cache(maxsize=1)
def semua_kata() -> tuple[tuple[str, str, str], ...]:
    """Semua kata bergambar tanpa duplikat: ((kata, emoji, kategori), ...), urut per kategori."""
    kategori_contoh = {k: kat for kat, daftar in content.KATEGORI_CONTOH.items() for k in daftar}
    urutan = list(content.KATEGORI) + [LAIN]
    hasil: dict[str, tuple[str, str, str]] = {}
    for kat, (_ikon, daftar) in content.KATEGORI.items():
        for kata, emoji in daftar:
            hasil.setdefault(kunci(kata), (kata, emoji, kat))
    for daftar in content.CONTOH_KATA.values():
        for kata, emoji in daftar:
            hasil.setdefault(kunci(kata), (kata, emoji, kategori_contoh.get(kata, LAIN)))
    return tuple(sorted(hasil.values(), key=lambda t: (urutan.index(t[2]), t[0].lower())))


def kategori() -> list[tuple[str, str, int]]:
    """[(nama, ikon, jumlah_kata)] sesuai urutan tampil."""
    hitung: dict[str, int] = {}
    for _k, _e, kat in semua_kata():
        hitung[kat] = hitung.get(kat, 0) + 1
    ikon = {k: v[0] for k, v in content.KATEGORI.items()}
    ikon[LAIN] = "🧩"
    return [(k, ikon[k], n) for k, n in hitung.items()]


@lru_cache(maxsize=1)
def _peta() -> dict[str, tuple[str, str]]:
    peta = {kunci(k): (k, e) for k, e, _ in semua_kata()}
    for k, v in content.KATA_KAMERA.items():
        peta.setdefault(kunci(k), (k.capitalize(), v["emoji"]))
    return peta


def cari(kata: str) -> tuple[str, str] | None:
    """Kata kosakata yang ejaannya sama persis (abaikan spasi/tanda hubung)."""
    return _peta().get(kunci(kata))


def saran_kata(awalan: str, n: int = 6) -> list[tuple[str, str]]:
    """Saran kata untuk huruf yang sudah dieja: 'MA' -> [('Main', ..), ('Makan', ..), ...].

    Kata yang sama persis didahulukan, lalu yang paling pendek (paling cepat selesai).
    """
    a = kunci(awalan)
    if not a:
        return []
    cocok = [(k, v) for k, v in _peta().items() if k.startswith(a)]
    cocok.sort(key=lambda kv: (kv[0] != a, len(kv[0]), kv[0]))
    return [v for _k, v in cocok[:n]]


def rapikan(teks: str) -> str:
    """Teks hasil kamera (kapital) -> kalimat wajar: 'SAYA MAU MAKAN' -> 'Saya mau makan.'"""
    kata = [t for t in str(teks).split() if t]
    if not kata:
        return ""
    keluar = []
    for t in kata:
        k = cari(t)
        keluar.append(k[0].lower() if k else t.lower())
    s = " ".join(keluar)
    s = s[0].upper() + s[1:]
    if s[-1] not in ".!?":
        tanya = {"APA", "SIAPA", "MANA", "KAPAN", "KENAPA", "BERAPA"}
        s += "?" if set(token(teks)) & tanya else "."
    return s


def saran_kalimat(teks: str, n: int = 3) -> list[tuple[str, str]]:
    """Kalimat sehari-hari yang paling mirip dengan kata-kata yang sudah dikenali kamera."""
    t = token(teks)
    if not t:
        return []
    ada = set(t)
    perlu = 1 if len(ada) == 1 else 2
    nilai = []
    for i, (kal, emoji) in enumerate(content.KALIMAT):
        kk = token(kal)
        sama = len(ada & set(kk))
        if sama >= min(perlu, len(kk)):
            # makin banyak kata yang cocok & makin sedikit yang kurang, makin atas
            nilai.append((-sama, len(kk) - sama, i, (kal, emoji)))
    nilai.sort()
    return [v[-1] for v in nilai[:n]]

"""Suara manusia (neural) Bahasa Indonesia untuk huruf, kata, dan kalimat.

Suara dibuat dengan suara neural Microsoft "Gadis" (id-ID-GadisNeural) lewat
paket `edge-tts`, lalu disimpan sebagai file MP3 di static/suara/ sehingga
aplikasi tidak perlu internet untuk huruf dan contoh kata. Tiap file punya
catatan kapan suara mulai dan berapa lama (ms) di sibi/data/suara.json, dipakai
untuk menyelaraskan gerak mulut dengan suara.

- Huruf A-Z dan contoh kata dibuat sekali: `python tools/build_suara.py`.
- Kata/kalimat lain (Eja kata, Kamera & suara) dibuat saat dibutuhkan bila ada
  internet, lalu disimpan di static/suara/cache/. Tanpa internet, aplikasi
  kembali memakai suara bawaan browser.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import threading
import time
from pathlib import Path

SUARA = "id-ID-GadisNeural"
# Sedikit lebih lambat dari bicara biasa agar jelas untuk anak; "pelan" untuk membaca gerak bibir.
KECEPATAN = {"normal": "-8%", "pelan": "-40%"}

_ROOT = Path(__file__).resolve().parents[1]
DIR = _ROOT / "static" / "suara"
CACHE_DIR = DIR / "cache"
URL = "app/static/suara"
MANIFEST = Path(__file__).resolve().parent / "data" / "suara.json"
_MAKS_CACHE = 400  # file suara sesuai permintaan yang disimpan

_lock = threading.Lock()
_manifest: dict | None = None
_gagal_sampai = 0.0  # jeda sebentar setelah gagal (mis. tanpa internet) agar halaman tetap cepat


def _kunci(teks: str, kecepatan: str) -> str:
    return f"{kecepatan}|{teks}"


def _nama_file(teks: str, kecepatan: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", teks.lower()).strip("-")[:40] or "suara"
    h = hashlib.sha1(f"{SUARA}|{KECEPATAN[kecepatan]}|{teks}".encode()).hexdigest()[:8]
    return f"{slug}-{kecepatan}-{h}.mp3"


def _muat() -> dict:
    global _manifest
    if _manifest is None:
        try:
            _manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _manifest = {}
    return _manifest


def _simpan() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    isi = json.dumps(_muat(), ensure_ascii=False, indent=1, sort_keys=True)
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(isi, encoding="utf-8")
    # Windows: file bisa sedang dibaca proses lain (mis. pemantau file Streamlit); coba lagi.
    for _ in range(10):
        try:
            tmp.replace(MANIFEST)
            return
        except PermissionError:
            time.sleep(0.05)
    MANIFEST.write_text(isi, encoding="utf-8")
    tmp.unlink(missing_ok=True)


async def _sintesis(teks: str, kecepatan: str, tujuan: Path) -> dict:
    import edge_tts

    kom = edge_tts.Communicate(teks, SUARA, rate=KECEPATAN[kecepatan], boundary="WordBoundary")
    audio = bytearray()
    batas = []
    async for ch in kom.stream():
        if ch["type"] == "audio":
            audio.extend(ch["data"])
        elif ch["type"] == "WordBoundary":
            batas.append((ch["offset"] / 10_000, (ch["offset"] + ch["duration"]) / 10_000))
    if not audio:
        raise RuntimeError("suara kosong")
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tujuan.write_bytes(bytes(audio))
    mulai = batas[0][0] if batas else 0.0
    selesai = batas[-1][1] if batas else mulai + 600.0
    return {"mulai": round(mulai), "lama": round(max(80.0, selesai - mulai))}


def buat(teks: str, kecepatan: str = "normal", *, cache: bool = False, timeout: float = 10.0) -> dict:
    """Buat (atau timpa) file suara untuk `teks`; kembalikan entri manifest."""
    sub = "cache/" if cache else ""
    nama = _nama_file(teks, kecepatan)
    tujuan = DIR / sub / nama
    info = asyncio.run(asyncio.wait_for(_sintesis(teks, kecepatan, tujuan), timeout))
    entri = {"file": sub + nama, "teks": teks, "kecepatan": kecepatan, "suara": SUARA, **info}
    with _lock:
        _muat()[_kunci(teks, kecepatan)] = entri
        if cache:
            _bersihkan_cache()
        _simpan()
    return entri


def _bersihkan_cache() -> None:
    m = _muat()
    cached = [(k, v) for k, v in m.items() if v["file"].startswith("cache/")]
    if len(cached) <= _MAKS_CACHE:
        return
    cached.sort(key=lambda kv: (DIR / kv[1]["file"]).stat().st_mtime if (DIR / kv[1]["file"]).exists() else 0)
    for k, v in cached[: len(cached) - _MAKS_CACHE]:
        (DIR / v["file"]).unlink(missing_ok=True)
        m.pop(k, None)


def _rapikan(teks: str) -> str:
    return " ".join(str(teks).split())


def audio(teks: str, kecepatan: str = "normal", *, boleh_buat: bool = True) -> dict | None:
    """Info suara untuk diputar browser: {"url", "mulai", "lama"} atau None.

    Bila belum ada dan `boleh_buat`, suara dibuat saat itu juga (butuh internet).
    """
    global _gagal_sampai
    teks = _rapikan(teks)
    if not teks:
        return None
    entri = _muat().get(_kunci(teks, kecepatan))
    if entri and (DIR / entri["file"]).exists():
        return {"url": f"{URL}/{entri['file']}", "mulai": entri["mulai"], "lama": entri["lama"]}
    if not boleh_buat or time.monotonic() < _gagal_sampai:
        return None
    try:
        entri = buat(teks, kecepatan, cache=True)
    except Exception:  # noqa: BLE001 - tanpa internet / layanan sibuk: pakai suara browser
        _gagal_sampai = time.monotonic() + 60
        return None
    return {"url": f"{URL}/{entri['file']}", "mulai": entri["mulai"], "lama": entri["lama"]}


def kedua_kecepatan(teks: str, *, boleh_buat: bool = True) -> dict:
    """{"audio": ..., "audioPelan": ...} untuk satu teks (dipakai komponen mulut)."""
    return {"audio": audio(teks, "normal", boleh_buat=boleh_buat),
            "audioPelan": audio(teks, "pelan", boleh_buat=boleh_buat)}


# ------------------------------------------------------------ pemutar suara
_JS_PUTAR = """
const SUDAH = new WeakMap();
export default function (component) {
  const { data, parentElement } = component;
  if (!data || !data.id || SUDAH.get(parentElement) === data.id) return;
  SUDAH.set(parentElement, data.id);
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  const browser = () => {
    if (!window.speechSynthesis || !data.teks) return;
    const u = new SpeechSynthesisUtterance(data.teks);
    u.lang = "id-ID";
    u.rate = 0.95;
    window.speechSynthesis.speak(u);
  };
  if (window.__sibiAudio) { try { window.__sibiAudio.pause(); } catch (e) {} }
  if (!data.url) return browser();
  const a = new Audio(data.url);
  window.__sibiAudio = a;
  a.onerror = browser;
  a.play().catch(browser);
}
"""

_PUTAR = None


def _komponen():
    global _PUTAR
    if _PUTAR is None:
        import streamlit as st

        _PUTAR = st.components.v2.component("sibi_putar_suara", html="<span></span>", js=_JS_PUTAR)
    return _PUTAR


def putar(teks: str, *, key: str, ulang_id: str | None = None) -> None:
    """Putar `teks` dengan suara manusia (cadangan: suara browser).

    `ulang_id` membedakan permintaan berulang untuk teks yang sama.
    """
    teks = _rapikan(teks)
    if not teks:
        return
    info = audio(teks)
    _komponen()(key=key, data={"id": ulang_id or f"{teks}|{time.time()}", "teks": teks,
                               "url": info["url"] if info else None}, height=0)

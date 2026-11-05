"""Buat file suara manusia (neural) untuk semua huruf dan kata di aplikasi.

    python tools/build_suara.py          # buat yang belum ada
    python tools/build_suara.py --ulang  # buat ulang semuanya (mis. setelah ganti suara)

Hasil: static/suara/*.mp3 dan sibi/data/suara.json. Butuh internet.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sibi import content, kosakata, suara
from sibi.mulut import teks_suara_huruf


def daftar_teks() -> list[tuple[str, tuple[str, ...]]]:
    """(teks, kecepatan...) untuk semua suara bawaan aplikasi."""
    out = []
    for h in content.HURUF:
        out.append((teks_suara_huruf(h), ("normal", "pelan")))
    for kata_list in content.CONTOH_KATA.values():
        for kata, _emoji in kata_list:
            out.append((kata, ("normal", "pelan")))
    for kata in content.KATA_ISYARAT:
        out.append((kata.capitalize(), ("normal",)))
    # kosakata sehari-hari, isyarat kamera, dan kalimat (kecepatan normal saja agar APK tetap ringan)
    sudah = {t for t, _ in out}
    tambahan = [k for k, _e, _kat in kosakata.semua_kata()]
    tambahan += [k.capitalize() for k in content.KATA_KAMERA]
    tambahan += [k for k, _e in content.KALIMAT]
    for teks in tambahan:
        if teks not in sudah:
            sudah.add(teks)
            out.append((teks, ("normal",)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ulang", action="store_true", help="buat ulang walau sudah ada")
    args = ap.parse_args()
    dibuat = 0
    for teks, kecepatan in daftar_teks():
        for kc in kecepatan:
            if not args.ulang and suara.audio(teks, kc, boleh_buat=False):
                continue
            for coba in range(3):
                try:
                    e = suara.buat(teks, kc, timeout=30)
                    break
                except Exception as err:
                    if coba == 2:
                        raise SystemExit(f"Gagal membuat suara '{teks}' ({kc}): {err}") from err
            dibuat += 1
            print(f"{teks:>16} {kc:<6} mulai {e['mulai']:>4} ms, lama {e['lama']:>4} ms -> {e['file']}")
    print(f"Selesai. {dibuat} file baru di {suara.DIR}")


if __name__ == "__main__":
    main()

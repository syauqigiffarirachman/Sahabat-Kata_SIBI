"""Rakit aplikasi HP (web offline) ke dalam proyek Android.

    python tools/build_mobile.py

Menyalin mobile/www (kode aplikasi HP), wajah bicara (sibi/mulut.js + .css),
foto tangan, file suara manusia, model huruf HP, MediaPipe, dan font ke
android/app/src/main/assets/www/, lalu menulis data/konten.json dari
sibi/content.py dan sibi/data/suara.json. Jalankan ulang setiap kali isi
aplikasi berubah, lalu build APK (lihat android/README.md).
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sibi import content, kosakata

OUT = ROOT / "android" / "app" / "src" / "main" / "assets" / "www"


def salin(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # 1. kode aplikasi HP
    www = ROOT / "mobile" / "www"
    for f in www.rglob("*"):
        if f.is_file():
            salin(f, OUT / f.relative_to(www))
    model = OUT / "model" / "huruf.json"
    if not model.exists():
        raise SystemExit("model/huruf.json belum ada. Jalankan dulu: python tools/build_model_mobile.py")

    # 2. wajah bicara (dipakai bersama dengan versi Streamlit)
    salin(ROOT / "sibi" / "mulut.js", OUT / "mulut.js")
    salin(ROOT / "sibi" / "mulut.css", OUT / "mulut.css")

    # 3. pustaka pihak ketiga (offline)
    vendor = ROOT / "mobile" / "vendor"
    for f in vendor.rglob("*"):
        if f.is_file():
            rel = f.relative_to(vendor)
            # .mjs -> .js agar WebView/servers mana pun memakai MIME JavaScript
            if f.name == "vision_bundle.mjs":
                rel = rel.with_name("vision_bundle.js")
            salin(f, OUT / "vendor" / rel)
    salin(ROOT / "hand_landmarker.task", OUT / "model" / "hand_landmarker.task")

    # 4. foto tangan
    for h in content.HURUF:
        src = ROOT / "static" / "hands" / "foto" / f"{h}.webp"
        if not src.exists():
            raise SystemExit(f"Foto tangan {src} tidak ada.")
        salin(src, OUT / "foto" / f"{h}.webp")

    # 5. suara manusia (hanya yang bawaan, bukan cache)
    manifest = json.loads((ROOT / "sibi" / "data" / "suara.json").read_text(encoding="utf-8"))
    suara = {"normal": {}, "pelan": {}}
    for e in manifest.values():
        if e["file"].startswith("cache/"):
            continue
        src = ROOT / "static" / "suara" / e["file"]
        if not src.exists():
            continue
        salin(src, OUT / "suara" / e["file"])
        suara[e["kecepatan"]][e["teks"]] = {"url": f"suara/{e['file']}", "mulai": e["mulai"], "lama": e["lama"]}

    # 6. konten
    konten = {
        "huruf": [{"h": h, **v, **content.BUNYI[h]} for h, v in content.HURUF.items()],
        "contoh": {h: [list(x) for x in v] for h, v in content.CONTOH_KATA.items()},
        "kataIsyarat": content.KATA_ISYARAT,
        "kosakata": [list(x) for x in kosakata.semua_kata()],
        "kategori": [list(x) for x in kosakata.kategori()],
        "kalimat": [list(x) for x in content.KALIMAT],
        "kataKamera": content.KATA_KAMERA,
        "suara": suara,
    }
    (OUT / "data").mkdir(exist_ok=True)
    (OUT / "data" / "konten.json").write_text(json.dumps(konten, ensure_ascii=False, separators=(",", ":")),
                                              encoding="utf-8")

    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    n = sum(1 for f in OUT.rglob("*") if f.is_file())
    jml_suara = len(suara["normal"]) + len(suara["pelan"])
    print(f"Aset HP siap: {OUT} ({n} file, {total / 1e6:.1f} MB, {jml_suara} suara)")


if __name__ == "__main__":
    main()

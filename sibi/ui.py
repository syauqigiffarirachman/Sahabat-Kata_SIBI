"""Komponen tampilan belajar SIBI: foto tangan asli (cadangan: gambar SVG) dan kartu kata.

Foto tangan asli ada di static/hands/foto/. Bila foto suatu huruf tidak ada, tangan digambar dari 21 titik sendi hasil rekaman: telapak, jari berbentuk tabung
dengan ujung membulat, bayangan lembut, dan lengan baju. Urutan tumpang-tindih jari
memakai kedalaman (z) sehingga jari yang menekuk ke depan tampak di depan telapak.
"""

import html
import json
import math
from functools import lru_cache
from pathlib import Path

from sibi import content

_SHAPES_FILE = Path(__file__).resolve().parent / "data" / "hand_shapes.json"

# Jari: (nama, indeks titik dari pangkal ke ujung, lebar relatif terhadap lebar telapak)
_FINGERS = [
    ("ibu jari", (1, 2, 3, 4), 0.34),
    ("telunjuk", (5, 6, 7, 8), 0.27),
    ("tengah", (9, 10, 11, 12), 0.28),
    ("manis", (13, 14, 15, 16), 0.26),
    ("kelingking", (17, 18, 19, 20), 0.22),
]
_TAPER = (1.0, 0.94, 0.86)  # lebar tiap ruas makin kecil ke ujung

SKIN, SKIN_DARK, SKIN_LIGHT = "#F4C7A1", "#C98B61", "#FBE0C8"
SLEEVE, SLEEVE_DARK = "#4C6FFF", "#3550D6"

CSS = """
<style>
.stApp{background:radial-gradient(1200px 500px at 10% -10%,#FFE9C7 0%,transparent 60%),
  radial-gradient(900px 500px at 100% 0%,#DCE6FF 0%,transparent 55%),#FFFBF5}
.block-container{max-width:1180px;padding-top:4.2rem !important}
.sb-hero{display:flex;align-items:center;gap:16px;padding:18px 24px;border-radius:24px;
  background:linear-gradient(120deg,#4C6FFF 0%,#7B5CFF 100%);color:#fff;
  box-shadow:0 10px 30px rgba(76,111,255,.28);margin-bottom:14px}
.sb-hero h1{margin:0;font-size:clamp(26px,4vw,40px);font-weight:800;color:#fff;padding:0}
.sb-hero p{margin:2px 0 0;font-size:clamp(14px,2vw,18px);opacity:.92;color:#fff}
.sb-hero .sb-hand{font-size:clamp(40px,6vw,60px)}
.sb-card{background:#fff;border:2px solid #EEE3D3;border-radius:22px;padding:16px;
  text-align:center;box-shadow:0 6px 18px rgba(80,60,20,.08);transition:transform .15s,box-shadow .15s}
.sb-card:hover{transform:translateY(-3px);box-shadow:0 12px 26px rgba(80,60,20,.14)}
.sb-bigletter{font-size:clamp(90px,14vw,150px);font-weight:900;line-height:1;color:#4C6FFF;
  text-shadow:0 6px 0 #DCE6FF}
.sb-handbox{display:flex;justify-content:center;align-items:center;padding:8px;border-radius:26px;
  background:linear-gradient(160deg,#DCE9FF 0%,#F1E6FF 100%);box-shadow:inset 0 0 0 3px #fff}
.sb-handbox img{max-width:100%;height:auto}
.sb-desc{font-size:clamp(18px,2.2vw,24px);line-height:1.65;font-weight:600;color:#2B2D42}
.sb-tip{margin-top:12px;padding:12px 16px;border-radius:16px;background:#FFF3CD;
  border-left:6px solid #FFB800;font-size:clamp(16px,2vw,20px);font-weight:600;color:#5C4400}
.sb-ucap{margin-top:6px;font-size:clamp(16px,2vw,20px);font-weight:800;color:#6B7499}
.sb-mouth{margin-top:12px;padding:12px 16px;border-radius:16px;background:#FDECEC;
  border-left:6px solid #D9786F;font-size:clamp(16px,2vw,20px);font-weight:600;color:#6A2A2A}
.sb-word{font-size:30px;font-weight:800;color:#2B2D42}
.sb-emoji{font-size:64px;line-height:1.1}
.sb-strip{display:flex;gap:8px;overflow-x:auto;padding:8px 2px 10px;justify-content:center;flex-wrap:wrap}
.sb-tile{flex:0 0 auto;text-align:center;background:#F6F8FF;border-radius:14px;padding:6px 6px 4px;
  border:2px solid #E4EAFF}
.sb-tile b{display:block;font-size:22px;font-weight:900;color:#4C6FFF}
.sb-ph{width:100%;max-width:240px;aspect-ratio:1;display:flex;align-items:center;justify-content:center;
  border:3px dashed #C9D3F5;border-radius:20px;margin:auto;padding:12px;color:#7480A8;font-weight:700}
/* tombol besar & ramah sentuhan */
div.stButton>button,div.stDownloadButton>button{border-radius:16px;font-weight:800;font-size:18px;
  min-height:52px;border:2px solid #E4EAFF;transition:transform .12s,box-shadow .12s}
div.stButton>button:hover{transform:translateY(-2px);box-shadow:0 8px 16px rgba(76,111,255,.22)}
[class*="st-key-pick_"] button{min-width:62px;height:62px;border-radius:18px}
[class*="st-key-pick_"] button p{font-size:26px;font-weight:900}
[class*="st-key-kuis_"] button{min-height:92px;border-radius:20px}
[class*="st-key-kuis_"] button p{font-size:42px;font-weight:900}
div.stButton>button p{font-weight:800}
[data-baseweb="button-group"] button{font-size:17px;font-weight:800}
.sb-star{font-size:22px;font-weight:800;color:#B7791F}
.sb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
.sb-grid .sb-card{padding:12px}
.sb-grid .sb-emoji{font-size:48px}
.sb-grid .sb-word{font-size:24px}
.sb-grid .sb-tile b{font-size:14px}
.sb-grid .sb-strip{gap:4px;padding:6px 0 2px}
.sb-grid .sb-tile{padding:2px 2px 1px;border-radius:10px}
.sb-grid .sb-handbox{padding:1px;border-radius:8px;box-shadow:none}
.sb-kalimat{background:#fff;border:2px solid #EEE3D3;border-radius:18px;padding:12px 16px;margin-bottom:10px;
  font-size:22px;font-weight:800;color:#2B2D42;display:flex;gap:12px;align-items:center}
.sb-kalimat span{font-size:34px}
.sb-soal{font-size:clamp(24px,3vw,34px);font-weight:900;color:#2B2D42;text-align:center;margin:6px 0}
.sb-soal u{color:#4C6FFF;text-decoration:none;border-bottom:4px dashed #4C6FFF;padding:0 18px}
.sb-susun{min-height:58px;border:3px dashed #C9D3F5;border-radius:18px;padding:10px 14px;font-size:24px;
  font-weight:900;color:#4C6FFF;text-align:center;background:#F6F8FF}
[class*="st-key-kk_"] button{min-height:72px;border-radius:20px}
[class*="st-key-kk_"] button p{font-size:22px;font-weight:900}
@media (max-width:640px){.block-container{padding:4.2rem .7rem .8rem !important}.sb-hero{padding:14px 16px}
 [class*="st-key-pick_"] button{min-width:44px;height:46px;padding:0 4px;border-radius:14px}
 [class*="st-key-pick_"] button p{font-size:20px}
 [class*="st-key-pick_"]{flex:0 0 auto}}
</style>
"""

# Tampilan APK / aplikasi HP: app bar tetap di atas, navigasi bawah, satu kolom,
# area sentuh besar. Dipasang SETELAH CSS agar menimpa gaya versi web.
CSS_APK = """
<style>
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"],footer{display:none !important}
.stApp{background:#F4F6FF}
.block-container{max-width:560px !important;padding:76px 12px calc(96px + env(safe-area-inset-bottom)) !important}
.sb-appbar{position:fixed;top:0;left:50%;transform:translateX(-50%);width:100%;max-width:560px;z-index:100;
  box-sizing:border-box;display:flex;align-items:center;gap:10px;color:#fff;
  padding:calc(10px + env(safe-area-inset-top)) 16px 12px;border-radius:0 0 22px 22px;
  background:linear-gradient(120deg,#4C6FFF 0%,#7B5CFF 100%);box-shadow:0 6px 18px rgba(76,111,255,.35)}
.sb-appbar .sb-ic{font-size:30px;line-height:1}
.sb-appbar b{display:block;font-size:19px;font-weight:900;line-height:1.15}
.sb-appbar small{display:block;font-size:12px;opacity:.9;font-weight:600}
/* kolom tetap berdampingan di layar sempit (tidak ditumpuk) */
.st-key-apk [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;gap:8px !important}
.st-key-apk [data-testid="stColumn"]{min-width:0 !important;flex:1 1 0 !important}
/* deretan huruf: geser ke samping seperti chip aplikasi */
.st-key-chiprow{flex-wrap:nowrap !important;overflow-x:auto;scrollbar-width:none;
  margin:0 -12px;padding:2px 12px 8px;scroll-snap-type:x proximity}
.st-key-chiprow::-webkit-scrollbar{display:none}
.st-key-chiprow>*{flex:0 0 auto !important}
.st-key-apk .sb-bigletter{font-size:84px;text-align:center}
.st-key-apk .sb-desc{font-size:17px;line-height:1.6}
.st-key-apk .sb-tip,.st-key-apk .sb-mouth{font-size:15px}
.st-key-apk .sb-ucap{text-align:center;font-size:15px}
.st-key-apk .sb-card{padding:12px;border-radius:20px}
.st-key-apk .sb-emoji{font-size:52px}
.st-key-apk .sb-word{font-size:24px}
.st-key-apk .sb-handbox{border-radius:22px}
.st-key-apk .sb-handbox img{width:min(100%,300px);height:auto}
.st-key-apk div.stButton>button{min-height:50px;font-size:16px}
.st-key-apk [class*="st-key-kuis_"] button{min-height:84px}
.st-key-apk [class*="st-key-kuis_"] button p{font-size:38px}
/* navigasi bawah */
.st-key-bottomnav{position:fixed;left:50%;transform:translateX(-50%);bottom:0;width:100%;max-width:560px;
  z-index:100;box-sizing:border-box;background:#fff;border-top:1px solid #E4EAFF;
  box-shadow:0 -6px 18px rgba(40,50,120,.10);padding:6px 6px calc(6px + env(safe-area-inset-bottom))}
.st-key-bottomnav div.stButton>button{flex-direction:column;gap:2px;min-height:56px;padding:4px 2px;
  border:0;border-radius:16px;background:transparent;box-shadow:none;transform:none;color:#6B7499}
.st-key-bottomnav div.stButton>button p{font-size:11px;font-weight:800}
.st-key-bottomnav div.stButton>button span{font-size:24px}
.st-key-bottomnav div.stButton>button[kind="primary"]{background:#EEF1FF;color:#4C6FFF}
</style>
"""


@lru_cache(maxsize=1)
def hand_shapes() -> dict:
    """Bentuk tangan (21 titik x,y,z) per huruf hasil rekaman dataset."""
    try:
        return json.loads(_SHAPES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def has_photo(letter: str) -> bool:
    """Ada foto tangan asli (static/hands/foto/<HURUF>.webp)?"""
    return (PHOTO_DIR / f"{letter.upper()}.webp").exists()


def has_shape(letter: str) -> bool:
    return has_photo(letter) or letter.upper() in hand_shapes()


def _f(v: float) -> str:
    return f"{v:.2f}"


def _stroke_path(points, width, color, extra=""):
    d = "M" + " L".join(f"{_f(x)} {_f(y)}" for x, y in points)
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{_f(width)}" '
            f'stroke-linecap="round" stroke-linejoin="round" {extra}/>')


STATIC_DIR = Path(__file__).resolve().parents[1] / "static" / "hands"
STATIC_URL = "app/static/hands"
# Foto tangan asli (latar dihapus). Sumber: dataset "asl_letters" (EitanG98, Hugging Face),
# lisensi Unlicense / domain publik. Lihat static/hands/foto/SUMBER.md.
PHOTO_DIR = STATIC_DIR / "foto"
PHOTO_URL = f"{STATIC_URL}/foto"


def hand_svg(letter: str, size: int = 300) -> str:
    """HTML gambar tangan untuk satu huruf; kotak petunjuk bila belum ada gambar.

    Memakai foto tangan asli (static/hands/foto/<HURUF>.webp) bila tersedia,
    selain itu gambar SVG dari rekaman (static/hands/<HURUF>.svg, dibuat oleh
    ensure_hand_files()). st.html membuang <svg> dan data URI, jadi gambar
    disajikan sebagai file statis.
    """
    letter = letter.upper()
    if not has_shape(letter):
        return (f'<div class="sb-ph" style="max-width:{size}px">Gambar huruf '
                f'{html.escape(letter)} belum ada. Ikuti penjelasan di samping.</div>')
    src = f"{PHOTO_URL}/{letter}.webp" if has_photo(letter) else f"{STATIC_URL}/{letter}.svg"
    return (f'<div class="sb-handbox"><img src="{src}" width="{size}" height="{size}" '
            f'alt="Bentuk tangan huruf {html.escape(letter)}" loading="lazy"></div>')


def ensure_hand_files(force: bool = False) -> int:
    """Tulis static/hands/<HURUF>.svg dari hand_shapes.json bila belum ada / usang."""
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _SHAPES_FILE.stat().st_mtime if _SHAPES_FILE.exists() else 0
    n = 0
    for letter in hand_shapes():
        f = STATIC_DIR / f"{letter}.svg"
        if force or not f.exists() or f.stat().st_mtime < stamp:
            f.write_text(_hand_svg_markup(letter, 300), encoding="utf-8")
            n += 1
    return n


def _geometry(pts3):
    """Titik 2D, kedalaman, dan sudut-sudut lengan baju untuk satu tangan (satuan data)."""
    pts = [(p[0], p[1]) for p in pts3]
    zs = [p[2] for p in pts3]
    palm_w = math.dist(pts[5], pts[17]) or 0.3
    ax, ay = pts[0][0] - pts[9][0], pts[0][1] - pts[9][1]
    n = math.hypot(ax, ay) or 1.0
    ux, uy = ax / n, ay / n
    px, py = -uy, ux
    wr, cuff, arm_len = palm_w * 0.46, palm_w * 0.12, palm_w * 0.8
    wx, wy = pts[0]
    g = {
        "pts": pts, "zs": zs, "palm_w": palm_w,
        "wrist_l": (wx + px * wr, wy + py * wr),
        "wrist_r": (wx - px * wr, wy - py * wr),
        "sleeve_a": (wx + ux * cuff * 1.5 + px * wr * 1.12, wy + uy * cuff * 1.5 + py * wr * 1.12),
        "sleeve_b": (wx + ux * cuff * 1.5 - px * wr * 1.12, wy + uy * cuff * 1.5 - py * wr * 1.12),
        "arm_a": (wx + ux * arm_len + px * wr * 1.25, wy + uy * arm_len + py * wr * 1.25),
        "arm_b": (wx + ux * arm_len - px * wr * 1.25, wy + uy * arm_len - py * wr * 1.25),
    }
    xs = [p[0] for p in pts] + [g["arm_a"][0], g["arm_b"][0]]
    ys = [p[1] for p in pts] + [g["arm_a"][1], g["arm_b"][1]]
    g["bbox"] = (min(xs), max(xs), min(ys), max(ys))
    return g


@lru_cache(maxsize=1)
def _common_scale() -> float:
    """Satu skala untuk semua huruf agar ukuran tangan konsisten antar gambar."""
    span = 0.0
    for pts3 in hand_shapes().values():
        x0, x1, y0, y1 = _geometry(pts3)["bbox"]
        span = max(span, x1 - x0, y1 - y0)
    return (100 - 2 * 8.0) / (span or 1.0)


def _hand_svg_markup(letter: str, size: int):
    pts3 = hand_shapes().get(letter.upper())
    if not pts3:
        return None

    g = _geometry(pts3)
    pts, zs, palm_w = g["pts"], g["zs"], g["palm_w"]
    wrist_l, wrist_r = g["wrist_l"], g["wrist_r"]
    sleeve_a, sleeve_b, arm_a, arm_b = g["sleeve_a"], g["sleeve_b"], g["arm_a"], g["arm_b"]
    x0, x1, y0, y1 = g["bbox"]
    k = _common_scale()
    ox = 50 - (x0 + x1) / 2 * k
    oy = 50 - (y0 + y1) / 2 * k

    def T(p):
        return (p[0] * k + ox, p[1] * k + oy)

    pt = [T(p) for p in pts]
    pw = palm_w * k
    out = []

    # lengan baju (paling belakang)
    arm = [T(sleeve_a), T(arm_a), T(arm_b), T(sleeve_b)]
    out.append(f'<polygon points="{" ".join(f"{_f(x)},{_f(y)}" for x, y in arm)}" '
               f'fill="{SLEEVE}" stroke="{SLEEVE_DARK}" stroke-width="1.1" stroke-linejoin="round"/>')
    # pergelangan (kulit) antara telapak dan baju
    wrist = [T(wrist_l), T(sleeve_a), T(sleeve_b), T(wrist_r)]
    out.append(f'<polygon points="{" ".join(f"{_f(x)},{_f(y)}" for x, y in wrist)}" '
               f'fill="{SKIN}" stroke="{SKIN_DARK}" stroke-width="1" stroke-linejoin="round"/>')

    # objek tangan yang diurutkan menurut kedalaman: (z_rata2, svg)
    layers = []

    palm_idx = (0, 1, 5, 9, 13, 17)
    palm_pts = [pt[i] for i in palm_idx]
    palm_str = " ".join(f"{_f(x)},{_f(y)}" for x, y in palm_pts)
    puff = pw * 0.20
    palm_svg = (
        f'<polygon points="{palm_str}" fill="{SKIN_DARK}" stroke="{SKIN_DARK}" '
        f'stroke-width="{_f(puff + 1.6)}" stroke-linejoin="round"/>'
        f'<polygon points="{palm_str}" fill="url(#skin-{letter})" stroke="{SKIN}" '
        f'stroke-width="{_f(puff)}" stroke-linejoin="round"/>'
    )
    layers.append((sum(zs[i] for i in palm_idx) / len(palm_idx) + 0.02, palm_svg))

    for _name, idx, rel in _FINGERS:
        base_w = rel * pw
        segs = list(zip(idx[:-1], idx[1:]))
        outline, fill, shine = [], [], []
        for s, (a, b) in enumerate(segs):
            w = base_w * _TAPER[s]
            outline.append(_stroke_path([pt[a], pt[b]], w + 1.7, SKIN_DARK))
            fill.append(_stroke_path([pt[a], pt[b]], w, SKIN))
            shine.append(_stroke_path([pt[a], pt[b]], w * 0.38, SKIN_LIGHT, 'opacity=".75"'))
        # lipatan buku jari
        creases = []
        for j in idx[1:3]:
            cx, cy = pt[j]
            creases.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(base_w * 0.07)}" fill="{SKIN_DARK}" opacity=".45"/>')
        z = sum(zs[i] for i in idx) / len(idx)
        layers.append((z, "".join(outline) + "".join(fill) + "".join(shine) + "".join(creases)))

    layers.sort(key=lambda t: -t[0])  # terjauh dulu, terdekat (z paling kecil) terakhir
    out.extend(svg for _z, svg in layers)

    defs = (f'<defs><linearGradient id="skin-{letter}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{SKIN_LIGHT}"/><stop offset="1" stop-color="{SKIN}"/>'
            f'</linearGradient><filter id="sh-{letter}" x="-20%" y="-20%" width="140%" height="140%">'
            f'<feDropShadow dx="0" dy="1.6" stdDeviation="1.6" flood-color="#3b2a8a" flood-opacity=".25"/>'
            f'</filter></defs>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">'
            f'{defs}<g filter="url(#sh-{letter})">{"".join(out)}</g></svg>')


def hand_tile(letter: str, size: int = 96, label: bool = True) -> str:
    """Kotak kecil: gambar tangan + huruf di bawahnya (untuk deretan ejaan).

    label=False menyembunyikan hurufnya (dipakai kuis agar jawaban tidak terlihat).
    """
    letter = letter.upper()
    if has_shape(letter):
        img = hand_svg(letter, size)
        if not label:
            img = img.replace(f'alt="Bentuk tangan huruf {html.escape(letter)}"', 'alt="Isyarat huruf"')
    else:
        img = f'<div class="sb-ph" style="max-width:{size}px;font-size:{size // 2}px">{html.escape(letter)}</div>'
    teks = f"<b>{html.escape(letter)}</b>" if label else ""
    return f'<div class="sb-tile">{img}{teks}</div>'


def spelling_strip(word: str, size: int = 96, label: bool = True) -> str:
    """Deretan isyarat huruf demi huruf untuk satu kata."""
    tiles = "".join(hand_tile(c, size, label) for c in word.upper() if c.isalpha())
    return f'<div class="sb-strip">{tiles}</div>'


def word_card(word: str, emoji: str) -> str:
    """Kartu kata: gambar, tulisan besar, lalu isyarat tiap huruf."""
    return (f'<div class="sb-card"><div class="sb-emoji">{emoji}</div>'
            f'<div class="sb-word">{html.escape(word)}</div>{spelling_strip(word, 84)}</div>')


def all_words() -> list:
    """Semua contoh kata: [(kata, emoji, huruf_awal)]."""
    out = []
    for letter, items in content.CONTOH_KATA.items():
        for word, emoji in items:
            out.append((word, emoji, letter))
    return sorted(out, key=lambda t: t[0].lower())


def word_grid(items, tile: int = 56) -> str:
    """Banyak kartu kata dalam satu grid HTML (lebih cepat dari satu st.html per kartu)."""
    cards = "".join(
        f'<div class="sb-card"><div class="sb-emoji">{e}</div>'
        f'<div class="sb-word">{html.escape(k)}</div>{spelling_strip(k, tile)}</div>'
        for k, e in items
    )
    return f'<div class="sb-grid">{cards}</div>'


def sentence_card(kalimat: str, emoji: str) -> str:
    return f'<div class="sb-kalimat"><span>{emoji}</span>{html.escape(kalimat)}</div>'

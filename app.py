"""SIBI Translator: kamus dan media belajar huruf & contoh kata untuk anak Tuli.

Halaman utama (cepat, tanpa kamera / model AI):
1. Belajar huruf : gambar tangan realistis A-Z, cara membentuk, tips, contoh kata
2. Kamus kata    : 300+ kosakata anak per kategori, isyarat kata, kalimat
3. Kuis          : tebak huruf, kata, dan kalimat dari isyarat
4. Eja kata      : ketik kata, lihat deretan isyarat hurufnya
5. Kamera & suara: fitur lanjutan (dimuat hanya saat dibuka)
"""

import random
import time

import streamlit as st

from sibi import content, kosakata, mulut, suara, ui

st.set_page_config(
    page_title="Belajar Isyarat SIBI",
    page_icon=":material/sign_language:",
    layout="wide",
)

ui.ensure_hand_files()
HURUF = list(content.HURUF)
HALAMAN = {
    "belajar": ":material/menu_book: Belajar huruf",
    "kamus": ":material/search: Kamus kata",
    "kuis": ":material/quiz: Kuis",
    "eja": ":material/spellcheck: Eja kata",
    "kamera": ":material/photo_camera: Kamera & suara",
}


TAMPILAN = {
    "web": ":material/computer: Web",
    "apk": ":material/smartphone: Aplikasi HP",
}
# Navigasi bawah (APK): (kunci, ikon, label pendek)
NAV_APK = [
    ("belajar", ":material/menu_book:", "Belajar"),
    ("kamus", ":material/search:", "Kamus"),
    ("kuis", ":material/quiz:", "Kuis"),
    ("eja", ":material/spellcheck:", "Eja"),
    ("kamera", ":material/photo_camera:", "Kamera"),
]


def _hp_dari_user_agent() -> bool:
    try:
        ua = st.context.headers.get("User-Agent", "")
    except Exception:
        return False
    return any(k in ua for k in ("Android", "iPhone", "iPod", "Mobile"))


def apk() -> bool:
    return st.session_state.tampilan == "apk"


def ganti_tampilan():
    st.session_state.tampilan = st.session_state.pilih_tampilan
    st.query_params["tampilan"] = st.session_state.tampilan


def buka(kunci: str):
    st.session_state.halaman = kunci


def init_state():
    ss = st.session_state
    if "tampilan" not in ss:
        # ?tampilan=apk / ?tampilan=web memaksa; selain itu ikuti perangkat.
        q = st.query_params.get("tampilan")
        ss.tampilan = q if q in TAMPILAN else ("apk" if _hp_dari_user_agent() else "web")
    ss.setdefault("pilih_tampilan", ss.tampilan)
    ss.setdefault("halaman", "belajar")
    ss.setdefault("huruf", "A")
    ss.setdefault("bisa", set())
    ss.setdefault("quiz", None)
    ss.setdefault("skor", 0)
    ss.setdefault("soal", 0)
    ss.setdefault("jawaban", None)
    ss.setdefault("dirayakan", False)
    ss.setdefault("skor_kuis", {})


def pilih(h: str):
    st.session_state.huruf = h


def geser(delta: int):
    i = HURUF.index(st.session_state.huruf)
    st.session_state.huruf = HURUF[(i + delta) % len(HURUF)]


def tandai_bisa():
    st.session_state.bisa.symmetric_difference_update({st.session_state.huruf})


def bicara(teks: str):
    """Minta suara diputar; pemutar dipasang di akhir halaman (lihat main)."""
    st.session_state.putar = {"teks": teks, "id": f"{teks}|{time.time()}"}


# ---------------------------------------------------------------- halaman
def halaman_belajar():
    bisa = st.session_state.bisa
    with st.container(horizontal=True, gap="small", key="chiprow",
                      horizontal_alignment="left" if apk() else "center"):
        for h in HURUF:
            st.button(
                h, key=f"pick_{h}", on_click=pilih, args=(h,),
                type="primary" if h == st.session_state.huruf else "secondary",
                icon=":material/star:" if h in bisa else None,
            )

    st.progress(len(bisa) / len(HURUF), text=f"{len(bisa)} dari {len(HURUF)} huruf sudah bisa")

    h = st.session_state.huruf
    info = content.HURUF[h]
    if apk():  # satu kolom: gambar, lalu penjelasan
        kiri, kanan = st.container(), st.container()
    else:
        kiri, kanan = st.columns([1.15, 1.5], gap="large", vertical_alignment="center")
    with kiri:
        st.html(ui.hand_svg(h, 300 if apk() else 380))
    with kanan:
        huruf_html = (f'<div class="sb-bigletter">{h}</div>'
                      f'<div class="sb-ucap">dibaca “{content.BUNYI[h]["ucap"]}”</div>')
        if apk():  # layar sempit: huruf di atas, wajah selebar layar
            st.html(huruf_html)
            mulut.mulut_huruf(h, key="mulut_belajar", size=280)
        else:
            huruf_col, mulut_col = st.columns([1, 1.5], vertical_alignment="center")
            huruf_col.html(huruf_html)
            with mulut_col:
                mulut.mulut_huruf(h, key="mulut_belajar", size=260)
        st.html(f'<div class="sb-desc">{info["deskripsi"]}</div>'
                f'<div class="sb-tip">💡 {info["tips"]}</div>'
                f'<div class="sb-mouth">👄 <b>Gerak mulut:</b> {content.BUNYI[h]["mulut"]}</div>')
        if h in ("J", "Z"):
            st.info("Huruf ini bergerak. Gambar menunjukkan posisi awal tangan.", icon=":material/info:")
        b1, b2, b3 = st.columns(3)
        b1.button("Kembali" if apk() else "Sebelumnya", on_click=geser, args=(-1,),
                  icon=":material/arrow_back:", width="stretch")
        b2.button(
            ("Bisa!" if apk() else "Sudah bisa!") if h in bisa else ("Bisa" if apk() else "Sudah bisa"),
            on_click=tandai_bisa,
            icon=":material/star:", type="primary" if h in bisa else "secondary", width="stretch",
        )
        b3.button("Lanjut" if apk() else "Berikutnya", on_click=geser, args=(1,),
                  icon=":material/arrow_forward:", width="stretch")

    st.subheader(f"Kata yang diawali huruf {h}")
    contoh = content.CONTOH_KATA.get(h, [])
    cols = [st.container() for _ in contoh] if apk() else st.columns(max(len(contoh), 2), gap="medium")
    for col, (kata, emoji) in zip(cols, contoh):
        with col:
            st.html(ui.word_card(kata, emoji))
            st.button(f"Dengarkan “{kata}”", key=f"say_{kata}", on_click=bicara, args=(kata,),
                      icon=":material/volume_up:", width="stretch")


def halaman_kamus():
    bagian = st.segmented_control(
        "Bagian kamus", ["kata", "isyarat", "kalimat"], default="kata", required=True,
        format_func={"kata": "🖼️ Kata bergambar", "isyarat": "👋 Isyarat kata", "kalimat": "💬 Kalimat"}.get,
        label_visibility="collapsed", key="kamus_bagian",
    )
    q = st.text_input("Cari", placeholder="Contoh: makan, kucing, merah",
                      icon=":material/search:", key="kamus_cari").strip().lower()

    if bagian == "kata":
        kat_list = kosakata.kategori()
        pilih_kat = st.pills(
            "Kategori", ["Semua"] + [k for k, _i, _n in kat_list], default="Semua",
            format_func=lambda k: "🌈 Semua" if k == "Semua" else next(f"{i} {k} ({n})" for kk, i, n in kat_list if kk == k),
            label_visibility="collapsed", key="kamus_kat",
        ) or "Semua"
        hasil = [(k, e) for k, e, kat in kosakata.semua_kata()
                 if (pilih_kat == "Semua" or kat == pilih_kat) and (not q or q in k.lower())]
        if not hasil:
            st.info("Kata tidak ditemukan. Coba kategori “Semua” atau kata lain.", icon=":material/search_off:")
            return
        st.caption(f"{len(hasil)} kata bergambar")
        st.html(ui.word_grid(hasil, 44 if apk() else 52))

    elif bagian == "isyarat":
        kata_isyarat = {
            k: v for k, v in content.KATA_ISYARAT.items()
            if not q or q in k.lower() or q in v["deskripsi"].lower()
        }
        if not kata_isyarat:
            st.info("Isyarat kata tidak ditemukan.", icon=":material/search_off:")
            return
        st.caption(f"{len(kata_isyarat)} isyarat kata sehari-hari. "
                   "Kata bertanda 📷 juga bisa dikenali kamera (mode Isyarat kata).")
        for kata, v in kata_isyarat.items():
            kam = content.KATA_KAMERA.get(kata)
            with st.expander(kata.title() + (" 📷" if kam else ""), icon=":material/waving_hand:"):
                st.html(f'<div class="sb-desc">{v["deskripsi"]}</div><div class="sb-tip">💡 {v["tips"]}</div>')
                if kam:
                    st.caption(f"📷 Di kamera: {kam['cara']}")
                st.button("Dengarkan", key=f"dengar_is_{kata}", on_click=bicara, args=(kata.capitalize(),),
                          icon=":material/volume_up:")

    else:
        kal = [(k, e) for k, e in content.KALIMAT if not q or q in k.lower()]
        if not kal:
            st.info("Kalimat tidak ditemukan.", icon=":material/search_off:")
            return
        st.caption(f"{len(kal)} kalimat sehari-hari. Buka untuk melihat isyarat tiap katanya.")
        for kalimat, emoji in kal:
            with st.expander(f"{emoji} {kalimat}"):
                for t in kalimat.rstrip(".?!").replace(",", "").split():
                    st.html(f'<b style="font-size:20px">{t}</b>{ui.spelling_strip(t, 52)}')
                st.button("Dengarkan", key=f"dengar_kal_{kalimat}", on_click=bicara, args=(kalimat,),
                          icon=":material/volume_up:")


# ---------------------------------------------------------------- kuis
JENIS_KUIS = {"huruf": "🔤 Huruf", "kata": "🖼️ Kata", "kalimat": "💬 Kalimat"}
_KATA_KECIL = {"DI", "KE", "DAN", "ITU", "INI", "DARI", "YA"}


def _kata_kuis() -> list:
    """Kata bergambar yang enak dieja di kuis: satu kata, 3-7 huruf."""
    return [(k, e, kat) for k, e, kat in kosakata.semua_kata()
            if k.isalpha() and 3 <= len(k) <= 7]


def soal_baru():
    punya = [h for h in HURUF if ui.has_shape(h)]
    if len(punya) < 4:
        st.session_state.quiz = None
        return
    benar = random.choice(punya)
    pilihan = random.sample([h for h in punya if h != benar], 3) + [benar]
    random.shuffle(pilihan)
    st.session_state.quiz = {"benar": benar, "pilihan": pilihan}
    st.session_state.jawaban = None
    st.session_state.dirayakan = False


def soal_kata():
    semua = _kata_kuis()
    k, e, kat = random.choice(semua)
    sekategori = [x for x in semua if x[2] == kat and x[0] != k]
    lain = [x for x in semua if x[2] != kat]
    pengecoh = random.sample(sekategori, min(2, len(sekategori)))
    pengecoh += random.sample(lain, 3 - len(pengecoh))
    pilihan = [(x[0], x[1]) for x in pengecoh] + [(k, e)]
    random.shuffle(pilihan)
    st.session_state.kuis_kata = {"benar": k, "emoji": e, "pilihan": pilihan, "jawab": None}


def soal_kalimat():
    kalimat, emoji = random.choice(content.KALIMAT)
    kata = kalimat.rstrip(".?!").replace(",", "").split()
    if random.random() < 0.5 and len(kata) >= 2:
        calon = [i for i, t in enumerate(kata) if kosakata.kunci(t) not in _KATA_KECIL and len(t) >= 3]
        i = random.choice(calon)
        benar = kata[i].capitalize()
        lain = [k for k, _e, _kat in _kata_kuis() if kosakata.kunci(k) != kosakata.kunci(benar)]
        pilihan = random.sample(lain, 3) + [benar]
        random.shuffle(pilihan)
        st.session_state.kuis_kal = {"jenis": "lengkapi", "kalimat": kalimat, "emoji": emoji, "kata": kata,
                                     "i": i, "benar": benar, "pilihan": pilihan, "jawab": None}
    else:
        acak = list(range(len(kata)))
        while len(kata) > 1 and acak == sorted(acak):
            random.shuffle(acak)
        st.session_state.kuis_kal = {"jenis": "susun", "kalimat": kalimat, "emoji": emoji, "kata": kata,
                                     "acak": acak, "susun": [], "jawab": None}


def _catat(jenis: str, benar: bool):
    skor = st.session_state.skor_kuis.setdefault(jenis, [0, 0])
    skor[1] += 1
    if benar:
        skor[0] += 1


def jawab(h: str):
    qz = st.session_state.quiz
    if qz and st.session_state.jawaban is None:
        st.session_state.jawaban = h
        st.session_state.soal += 1
        if h == qz["benar"]:
            st.session_state.skor += 1


def jawab_kata(k: str):
    qz = st.session_state.kuis_kata
    if qz["jawab"] is None:
        qz["jawab"] = k
        _catat("kata", k == qz["benar"])
        bicara(qz["benar"])


def jawab_lengkapi(k: str):
    qz = st.session_state.kuis_kal
    if qz["jawab"] is None:
        qz["jawab"] = k
        _catat("kalimat", k == qz["benar"])
        bicara(qz["kalimat"])


def pilih_susun(i: int):
    qz = st.session_state.kuis_kal
    if qz["jawab"] is None and i not in qz["susun"]:
        qz["susun"].append(i)
        if len(qz["susun"]) == len(qz["kata"]):
            dapat = " ".join(qz["kata"][j] for j in qz["susun"])
            qz["jawab"] = dapat
            _catat("kalimat", dapat == " ".join(qz["kata"]))
            bicara(qz["kalimat"])


def ulang_susun():
    qz = st.session_state.kuis_kal
    if qz["jawab"] is None:
        qz["susun"] = []


def _rayakan(ok: bool, kunci: str):
    if ok and st.session_state.get("dirayakan_" + kunci) != id(st.session_state.get(kunci)):
        st.session_state["dirayakan_" + kunci] = id(st.session_state.get(kunci))
        st.balloons()


def kuis_huruf():
    if st.session_state.quiz is None:
        soal_baru()
    qz = st.session_state.quiz
    if qz is None:
        st.warning("Kuis butuh minimal 4 huruf yang gambar tangannya sudah ada.")
        return

    st.subheader("Huruf apa ini?")
    if apk():
        kiri, kanan = st.container(), st.container()
    else:
        kiri, kanan = st.columns([1.1, 1.4], gap="large", vertical_alignment="center")
    with kiri:
        st.html(ui.hand_svg(qz["benar"], 280 if apk() else 360))
    with kanan:
        st.metric("Skor", f"{st.session_state.skor} / {st.session_state.soal}", border=True)
        per_baris = 2 if apk() else 4  # APK: pilihan 2x2 agar mudah ditekan
        for i in range(0, 4, per_baris):
            for col, h in zip(st.columns(per_baris), qz["pilihan"][i:i + per_baris]):
                col.button(h, key=f"kuis_{h}", on_click=jawab, args=(h,), width="stretch",
                           disabled=st.session_state.jawaban is not None)
        j = st.session_state.jawaban
        if j is not None:
            if j == qz["benar"]:
                st.success(f"Hebat! Ini huruf {qz['benar']}.", icon=":material/celebration:")
                if not st.session_state.dirayakan:
                    st.session_state.dirayakan = True
                    st.balloons()
            else:
                st.error(f"Belum tepat. Jawabannya huruf {qz['benar']}. Ayo coba lagi!", icon=":material/refresh:")
            st.button("Soal berikutnya", on_click=soal_baru, type="primary",
                      icon=":material/arrow_forward:", width="stretch")


def _skor(jenis: str):
    b, s = st.session_state.skor_kuis.get(jenis, [0, 0])
    st.metric("Skor", f"{b} / {s}", border=True)


def _pilihan_kata(items, on_click, kunci, nonaktif, benar=None):
    per_baris = 2
    for i in range(0, len(items), per_baris):
        for col, (label, nilai) in zip(st.columns(per_baris), items[i:i + per_baris]):
            col.button(label, key=f"kk_{kunci}_{nilai}", on_click=on_click, args=(nilai,),
                       width="stretch", disabled=nonaktif,
                       type="primary" if benar is not None and nilai == benar else "secondary")


def kuis_kata():
    if st.session_state.get("kuis_kata") is None:
        soal_kata()
    qz = st.session_state.kuis_kata
    st.subheader("Kata apa ini? Baca isyarat hurufnya!")
    _skor("kata")
    st.html(ui.spelling_strip(qz["benar"], 70 if apk() else 96, label=False))
    _pilihan_kata([(f"{e} {k}", k) for k, e in qz["pilihan"]], jawab_kata, "kata",
                  qz["jawab"] is not None, qz["benar"] if qz["jawab"] else None)
    if qz["jawab"] is not None:
        ok = qz["jawab"] == qz["benar"]
        if ok:
            st.success(f"Hebat! Ini kata {qz['emoji']} {qz['benar']}.", icon=":material/celebration:")
        else:
            st.error(f"Belum tepat. Jawabannya {qz['emoji']} {qz['benar']}. Ayo coba lagi!", icon=":material/refresh:")
        _rayakan(ok, "kuis_kata")
        st.button("Soal berikutnya", on_click=soal_kata, type="primary",
                  icon=":material/arrow_forward:", width="stretch", key="lanjut_kata")


def kuis_kalimat():
    if st.session_state.get("kuis_kal") is None:
        soal_kalimat()
    qz = st.session_state.kuis_kal
    _skor("kalimat")
    if qz["jenis"] == "lengkapi":
        st.subheader("Lengkapi kalimatnya!")
        kata = [("<u>?</u>" if i == qz["i"] and qz["jawab"] is None else t) for i, t in enumerate(qz["kata"])]
        st.html(f'<div class="sb-soal">{qz["emoji"]} {" ".join(kata)}</div>'
                f'<p style="text-align:center;font-weight:700;color:#6B7499">Isyarat kata yang hilang:</p>'
                f'{ui.spelling_strip(qz["benar"], 64 if apk() else 84, label=False)}')
        _pilihan_kata([(k, k) for k in qz["pilihan"]], jawab_lengkapi, "lengkapi",
                      qz["jawab"] is not None, qz["benar"] if qz["jawab"] else None)
        ok = qz["jawab"] == qz["benar"]
    else:
        st.subheader("Susun kalimatnya! Baca isyarat tiap kata, lalu tekan kata sesuai urutan.")
        st.html(f'<div class="sb-soal">{qz["emoji"]}</div>'
                + "".join(ui.spelling_strip(t, 40 if apk() else 52, label=False) for t in qz["kata"]))
        tersusun = " ".join(qz["kata"][j] for j in qz["susun"])
        st.html(f'<div class="sb-susun">{tersusun or "…"}</div>')
        with st.container(horizontal=True, gap="small"):
            for j in qz["acak"]:
                st.button(qz["kata"][j], key=f"kk_susun_{j}", on_click=pilih_susun, args=(j,),
                          disabled=qz["jawab"] is not None or j in qz["susun"])
        if qz["susun"] and qz["jawab"] is None:
            st.button("Ulangi susunan", on_click=ulang_susun, icon=":material/undo:")
        ok = qz["jawab"] == " ".join(qz["kata"])
    if qz["jawab"] is not None:
        if ok:
            st.success(f"Hebat! {qz['kalimat']}", icon=":material/celebration:")
        else:
            st.error(f"Belum tepat. Kalimatnya: {qz['kalimat']} Ayo coba lagi!", icon=":material/refresh:")
        _rayakan(ok, "kuis_kal")
        st.button("Soal berikutnya", on_click=soal_kalimat, type="primary",
                  icon=":material/arrow_forward:", width="stretch", key="lanjut_kal")


def halaman_kuis():
    jenis = st.segmented_control("Jenis kuis", list(JENIS_KUIS), format_func=JENIS_KUIS.get,
                                 default="huruf", required=True, label_visibility="collapsed",
                                 key="jenis_kuis")
    {"huruf": kuis_huruf, "kata": kuis_kata, "kalimat": kuis_kalimat}[jenis]()


def halaman_eja():
    teks = st.text_input("Ketik kata atau nama", value="APEL", max_chars=30,
                         icon=":material/edit:").upper().strip()
    kata_list = "".join(c for c in teks if c.isalpha() or c == " ").split()
    if not kata_list:
        st.info("Ketik satu kata untuk melihat urutan isyarat hurufnya.", icon=":material/keyboard:")
        return
    for i, kata in enumerate(kata_list):
        st.subheader(kata)
        if apk():
            st.html(ui.spelling_strip(kata, 76))
            mulut.mulut_eja(kata, key=f"mulut_eja_{i}", size=220)
        else:
            kiri, kanan = st.columns([1, 2.4], gap="large", vertical_alignment="center")
            with kiri:
                mulut.mulut_eja(kata, key=f"mulut_eja_{i}", size=240)
            kanan.html(ui.spelling_strip(kata, 120))


def halaman_kamera():
    st.caption("Fitur lanjutan. Dimuat hanya saat dibutuhkan agar kamus tetap ringan.")
    sub = st.segmented_control("Fitur", ["Kamera", "Suara", "Status model"], default="Kamera",
                               required=True, label_visibility="collapsed")
    if sub == "Kamera":
        if st.toggle("Aktifkan penerjemah kamera"):
            from sibi.camera_tab import render_camera
            render_camera()
    elif sub == "Suara":
        from sibi.camera_tab import render_audio
        render_audio()
    else:
        from sibi.camera_tab import render_status
        render_status()


PAGES = {
    "belajar": halaman_belajar, "kamus": halaman_kamus, "kuis": halaman_kuis,
    "eja": halaman_eja, "kamera": halaman_kamera,
}


def pilih_tampilan():
    st.segmented_control(
        "Tampilan", list(TAMPILAN), format_func=TAMPILAN.get, required=True,
        key="pilih_tampilan", on_change=ganti_tampilan,
    )


def layout_web():
    """Versi website: header lebar, menu tab di atas, konten 2 kolom."""
    with st.container(key="web"):
        st.html(
            '<div class="sb-hero"><span class="sb-hand">🤟</span><div>'
            "<h1>Belajar Isyarat SIBI</h1>"
            "<p>Kenali bentuk tangan huruf A–Z dan kata-kata pertamamu</p></div></div>"
        )
        st.segmented_control(
            "Menu", list(HALAMAN), format_func=HALAMAN.get, default=st.session_state.halaman,
            required=True, label_visibility="collapsed", key="halaman_web",
            on_change=lambda: buka(st.session_state.halaman_web),
        )
        PAGES[st.session_state.halaman]()
        st.caption("Deskripsi bentuk tangan sebaiknya dicocokkan dengan guru SLB atau pedoman resmi SIBI.")
        pilih_tampilan()


def layout_apk():
    """Versi APK / HP: app bar tetap, satu kolom, navigasi di bawah."""
    halaman = st.session_state.halaman
    judul = {k: label for k, _ic, label in NAV_APK}[halaman]
    with st.container(key="apk"):
        st.html(
            f'<div class="sb-appbar"><span class="sb-ic">🤟</span><div>'
            f"<b>Isyarat SIBI</b><small>{judul}</small></div></div>"
        )
        PAGES[halaman]()
        st.caption("Deskripsi bentuk tangan sebaiknya dicocokkan dengan guru SLB atau pedoman resmi SIBI.")
        pilih_tampilan()
        with st.container(key="bottomnav"):
            for col, (kunci, ikon, label) in zip(st.columns(len(NAV_APK)), NAV_APK):
                col.button(label, key=f"nav_{kunci}", icon=ikon, on_click=buka, args=(kunci,),
                           type="primary" if kunci == halaman else "tertiary", width="stretch")


def main():
    init_state()
    st.html(ui.CSS)
    if apk():
        st.html(ui.CSS_APK)
        layout_apk()
    else:
        layout_web()
    if st.session_state.get("putar"):
        p = st.session_state.putar
        suara.putar(p["teks"], key="putar_suara", ulang_id=p["id"])


main()

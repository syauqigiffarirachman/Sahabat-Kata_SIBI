"""Tab Kamera, Suara, dan Status Model (fitur lanjutan SIBI Translator).

Modul ini sengaja dipisah dan dimuat HANYA saat tab dibuka, sehingga
OpenCV / MediaPipe / WebRTC (berat) tidak memperlambat kamus & belajar huruf.
"""

from pathlib import Path
import queue

import streamlit as st
import streamlit.components.v1 as components

from sibi import content, kosakata


@st.cache_resource
def load_shared_models():
    """Memuat model AI berat sekali saja untuk efisiensi memori."""
    from sibi.core.classifier import SIBIClassifier
    from sibi.core.classifier_word import SIBIWordClassifier
    from sibi.core.hand_detector import HandDetector

    detector = HandDetector(max_num_hands=2, min_detection_confidence=0.6)
    return detector, SIBIClassifier(), SIBIWordClassifier(sequence_length=20)


def init_session_state():
    """Menjamin setiap tab / pengguna memiliki buffer dan antrian mandiri."""
    from sibi.core.sequence_buffer import SequenceBuffer, WordSequenceBuffer

    if "buf_huruf" not in st.session_state:
        st.session_state.buf_huruf = SequenceBuffer(frame_threshold=8, min_confidence=0.65)
    if "buf_kata" not in st.session_state:
        st.session_state.buf_kata = WordSequenceBuffer(sequence_length=20, min_confidence=0.75)
    if "msg_queue" not in st.session_state:
        st.session_state.msg_queue = queue.Queue(maxsize=100)
    if "translated_sentence" not in st.session_state:
        st.session_state.translated_sentence = ""


def speak_text(text: str):
    """Menyuarakan teks Bahasa Indonesia dengan suara manusia (neural).

    Memakai sibi/suara.py (suara "Gadis"); bila tidak ada internet, otomatis
    kembali ke suara bawaan browser.
    """
    if text and text.strip():
        from sibi import suara

        suara.putar(text.strip(), key="putar_kamera")


def gabung_kata(teks: str, kata: str) -> str:
    """Tambahkan satu kata ke akhir teks dengan satu spasi pemisah."""
    teks = teks.rstrip()
    return f"{teks} {kata}" if teks else kata


def create_video_callback(mode, buf_huruf, buf_kata, msg_q, detector, classifier_huruf, classifier_kata):
    """Membuat fungsi callback thread-safe untuk Streamlit-WebRTC."""
    def video_frame_callback(frame):
        import av
        import cv2
        from sibi.core.normalize import normalize_landmarks

        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)  # Cermin
        h, w, _ = img.shape

        try:
            img_drawn, landmarks = detector.process(img, draw=True)
            current_label = "-"
            confidence = 0.0
            sentence = ""
            progress = 0.0

            if mode == "Isyarat Huruf":
                if landmarks:
                    norm = normalize_landmarks(landmarks[0])
                    if len(norm) == 63:
                        current_label, confidence = classifier_huruf.predict(norm)

                sentence = buf_huruf.update(current_label, confidence)
                progress = buf_huruf.progress

            else:  # Isyarat Kata: kata yang dikenali ditambahkan ke teks yang sama
                norm = []
                wrist = None
                if landmarks:
                    norm = normalize_landmarks(landmarks[0])
                    wrist = buf_kata.wrist_track(landmarks[0])
                _teks, detected_word, conf = buf_kata.update(norm, classifier_kata, wrist=wrist)
                if detected_word != "-":
                    current_label = detected_word
                    confidence = conf
                    buf_huruf.text_result = gabung_kata(buf_huruf.text_result, detected_word)
                    buf_huruf.last_added_char = ""
                sentence = buf_huruf.text_result
                progress = len(buf_kata.frames) / float(buf_kata.sequence_length)

            # Kirim update ke UI non-blocking
            if not msg_q.full():
                try:
                    msg_q.put_nowait({
                        "sentence": sentence,
                        "label": current_label,
                        "conf": confidence,
                        "progress": progress
                    })
                except queue.Full:
                    pass

            # Gambar HUD langsung pada video frame (30 FPS tanpa lag UI)
            # 1. Overlay Header
            cv2.rectangle(img_drawn, (0, 0), (w, 50), (20, 20, 25), -1)
            cv2.putText(
                img_drawn,
                f"SIBI AI: {mode}",
                (15, 33),
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                (0, 230, 115) if mode == "Isyarat Huruf" else (255, 180, 50),
                2
            )

            # 2. Box Prediksi
            if current_label != "-":
                cv2.rectangle(img_drawn, (15, 65), (320, 140), (30, 30, 40), -1)
                cv2.rectangle(img_drawn, (15, 65), (320, 140), (0, 255, 120), 1)
                cv2.putText(
                    img_drawn,
                    f"{'Huruf' if mode == 'Isyarat Huruf' else 'Kata'}: {current_label}",
                    (25, 95),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.8,
                    (255, 255, 255),
                    2
                )
                cv2.putText(
                    img_drawn,
                    f"Akurasi: {confidence*100:.0f}%",
                    (25, 120),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (180, 255, 180),
                    1
                )

                # Progress bar penahanan pose
                bx, by, bw, bh = 25, 128, 150, 6
                cv2.rectangle(img_drawn, (bx, by), (bx + bw, by + bh), (70, 70, 70), -1)
                fill_w = int(bw * max(0.0, min(1.0, progress)))
                cv2.rectangle(img_drawn, (bx, by), (bx + fill_w, by + bh), (0, 255, 0), -1)

            # 3. Footer Banner Kalimat
            cv2.rectangle(img_drawn, (0, h - 55), (w, h), (15, 15, 20), -1)
            display_text = sentence if sentence.strip() else "Arahkan tangan ke kamera..."
            cv2.putText(
                img_drawn,
                display_text,
                (20, h - 20),
                cv2.FONT_HERSHEY_DUPLEX,
                0.75,
                (255, 255, 255) if sentence.strip() else (130, 130, 130),
                2
            )

            return av.VideoFrame.from_ndarray(img_drawn, format="bgr24")

        except Exception as err:
            return av.VideoFrame.from_ndarray(img, format="bgr24")

    return video_frame_callback


def _set_teks(teks: str):
    buf = st.session_state.buf_huruf
    buf.text_result = teks
    buf.last_added_char = ""
    st.session_state.translated_sentence = teks


def _pakai_saran_kata(kata: str):
    """Ganti huruf yang sedang dieja dengan kata lengkap, lalu beri spasi."""
    teks = st.session_state.buf_huruf.text_result
    awal = teks.rsplit(" ", 1)[0] + " " if " " in teks.rstrip() else ""
    _set_teks(f"{awal}{kata.upper()} ")


def _pakai_kalimat(kalimat: str):
    _set_teks(" ".join(kosakata.token(kalimat)))


def _hapus(mode: str):
    teks = st.session_state.buf_huruf.text_result
    if mode == "Isyarat Huruf":
        _set_teks(teks[:-1])
    else:
        _set_teks(" ".join(teks.split()[:-1]))


@st.fragment(run_every=0.8)
def _panel_hasil(mode: str):
    """Teks hasil kamera, diperbarui sendiri tiap ±1 detik, plus saran kata & kalimat."""
    q = st.session_state.msg_queue
    while not q.empty():
        msg = q.get_nowait()
        if msg.get("sentence") is not None:
            st.session_state.translated_sentence = msg["sentence"]
    teks = st.session_state.buf_huruf.text_result

    if teks.strip():
        st.success(f"### {teks}")
        st.markdown(f"**Kalimat:** {kosakata.rapikan(teks)}")
    else:
        st.info("*(Menunggu isyarat tangan di depan kamera...)*")

    # Saran kata: huruf yang sedang dieja (belum diberi spasi) -> kata lengkap
    sedang = "" if (not teks or teks.endswith(" ")) else teks.split()[-1]
    saran = kosakata.saran_kata(sedang, n=6) if sedang else []
    if saran and not (len(saran) == 1 and kosakata.kunci(saran[0][0]) == sedang):
        st.caption("Maksudnya kata ini? Tekan untuk memakai:")
        with st.container(horizontal=True, gap="small"):
            for kata, emoji in saran:
                st.button(f"{emoji} {kata}", key=f"saran_kata_{kata}", on_click=_pakai_saran_kata, args=(kata,))

    kalimat = kosakata.saran_kalimat(teks, n=3)
    if kalimat:
        st.caption("Kalimat yang mirip:")
        for kal, emoji in kalimat:
            st.button(f"{emoji} {kal}", key=f"saran_kal_{kal}", on_click=_pakai_kalimat, args=(kal,),
                      width="stretch")

    b_spasi, b_hapus, b_reset = st.columns(3)
    b_spasi.button("␣ Spasi", width="stretch", on_click=lambda: _set_teks(teks.rstrip() + " " if teks.strip() else ""))
    b_hapus.button("⌫ Hapus", width="stretch", on_click=_hapus, args=(mode,))
    b_reset.button("🗑️ Reset", width="stretch", on_click=lambda: (_set_teks(""), st.session_state.buf_huruf.clear(),
                                                                  st.session_state.buf_kata.clear()))
    if st.button("🔊 Suarakan kalimat", type="primary", width="stretch"):
        speak_text(kosakata.rapikan(teks))


def render_camera():
    """Penerjemah kamera real-time (dimuat saat pengguna menekan tombol aktifkan)."""
    from streamlit_webrtc import RTCConfiguration, WebRtcMode, webrtc_streamer

    rtc_config = RTCConfiguration({"iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:global.stun.twilio.com:3478"]},
    ]})
    init_session_state()
    detector, classifier_huruf, classifier_kata = load_shared_models()

    st.subheader("🎥 Penerjemah Kamera Real-time")

    col_cam, col_ctrl = st.columns([3, 2])

    with col_ctrl:
        mode = st.radio(
            "Pilih cara berisyarat:",
            ["Isyarat Huruf", "Isyarat Kata"],
            format_func={"Isyarat Huruf": "🔤 Eja huruf → kata", "Isyarat Kata": "🤟 Isyarat kata"}.get,
            horizontal=True,
            help="Eja huruf: eja kata huruf demi huruf, lalu pilih saran kata. "
                 "Isyarat kata: tunjukkan isyarat kata sederhana (lihat daftar). Keduanya mengisi kalimat yang sama.",
        )
        kamera_pos = st.radio("Posisi Kamera:", ["Kamera Depan (User)", "Kamera Belakang (Environment)"], horizontal=True)
        facing_mode = "user" if kamera_pos == "Kamera Depan (User)" else "environment"

        st.markdown("#### 📝 Hasil terjemahan")
        _panel_hasil(mode)

        with st.expander(f"🤟 {len(content.KATA_KAMERA)} isyarat kata yang dikenali kamera"):
            for kata, v in content.KATA_KAMERA.items():
                jenis = "tahan diam" if v["jenis"] == "diam" else "bergerak"
                st.markdown(f"{v['emoji']} **{kata.title()}** ({jenis}): {v['cara']}")
            st.caption(f"Kata lain ({len(kosakata.semua_kata())} kosakata anak) bisa dieja huruf demi huruf; "
                       "saran kata muncul otomatis.")

    with col_cam:
        cb = create_video_callback(
            mode=mode,
            buf_huruf=st.session_state.buf_huruf,
            buf_kata=st.session_state.buf_kata,
            msg_q=st.session_state.msg_queue,
            detector=detector,
            classifier_huruf=classifier_huruf,
            classifier_kata=classifier_kata,
        )

        webrtc_streamer(
            key=f"streamer_{mode.replace(' ', '_')}_{kamera_pos}",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=rtc_config,
            video_frame_callback=cb,
            media_stream_constraints={"video": {"facingMode": facing_mode}, "audio": False},
            video_html_attrs={"autoPlay": True, "controls": False, "playsinline": True},
            async_processing=True
        )
        st.caption("💡 Huruf: tahan pose ±0,5 detik sampai garis hijau penuh. "
                   "Kata: lakukan gerakannya, atau tahan bentuk tangan diam ±1 detik.")


def render_audio():
    """Hub suara: teks ke suara dan suara ke teks."""
    init_session_state()
    st.subheader("🎙️ Hub Komunikasi Audio Dua Arah (TTS & STT)")
    st.write("Jembatan komunikasi antara Teman Tuli (isyarat/teks) dan Teman Dengar (suara/audio).")

    col_tts, col_stt = st.columns(2)

    with col_tts:
        st.markdown("#### 🔊 Text-to-Speech (Teks ke Suara)")
        st.caption("Ubah tulisan hasil terjemahan menjadi suara berbahasa Indonesia.")
        tts_input = st.text_area(
            "Teks yang ingin disuarakan:",
            value=st.session_state.translated_sentence if st.session_state.translated_sentence else "Halo, selamat datang di SIBI Translator",
            height=120
        )
        if st.button("▶️ Putar Suara (Play Audio)", type="primary", width="stretch"):
            speak_text(tts_input)

    with col_stt:
        st.markdown("#### 🎤 Speech-to-Text (Suara ke Isyarat)")
        st.caption("Bicara melalui mikrofon untuk diterjemahkan menjadi teks dan isyarat jari SIBI.")

        # Komponen Web Speech API untuk pengenalan suara Bahasa Indonesia
        stt_html = """
        <div style="padding: 12px; border: 1px dashed #555; border-radius: 8px; text-align: center;">
            <button id="recordBtn" style="background-color: #e53935; color: white; border: none; padding: 10px 20px; font-size: 15px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                🎙️ Mulai Bicara (Mikrofon)
            </button>
            <p id="sttStatus" style="font-size: 13px; color: #aaa; margin-top: 8px;">Klik tombol di atas untuk merekam suara Bahasa Indonesia</p>
            <div id="sttResult" style="margin-top: 12px; font-size: 18px; font-weight: bold; color: #00e673; min-height: 30px;"></div>
        </div>

        <script>
            const btn = document.getElementById('recordBtn');
            const status = document.getElementById('sttStatus');
            const result = document.getElementById('sttResult');

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

            if (!SpeechRecognition) {
                status.innerHTML = "⚠️ Browser Anda belum mendukung Web Speech Recognition (Gunakan Chrome atau Edge).";
                btn.disabled = true;
            } else {
                const recognition = new SpeechRecognition();
                recognition.lang = 'id-ID';
                recognition.interimResults = false;
                recognition.maxAlternatives = 1;

                let recognizing = false;

                btn.addEventListener('click', () => {
                    if (recognizing) {
                        recognition.stop();
                    } else {
                        recognition.start();
                    }
                });

                recognition.onstart = () => {
                    recognizing = true;
                    btn.innerHTML = "⏹️ Berhenti Merekam...";
                    btn.style.backgroundColor = "#ff9800";
                    status.innerHTML = "Mendengarkan suara Anda... Silakan berbicara!";
                };

                recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    result.innerHTML = `💬 Terdeteksi: "${transcript}"`;
                };

                recognition.onerror = (event) => {
                    status.innerHTML = "Error suara: " + event.error;
                };

                recognition.onend = () => {
                    recognizing = false;
                    btn.innerHTML = "🎙️ Mulai Bicara (Mikrofon)";
                    btn.style.backgroundColor = "#e53935";
                    status.innerHTML = "Perekaman selesai.";
                };
            }
        </script>
        """
        components.html(stt_html, height=220)


def render_status():
    """Status model AI dan dataset pelatihan."""
    detector, classifier_huruf, classifier_kata = load_shared_models()
    st.subheader("📊 Status Otak AI & Informasi Dataset")

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown("#### 🧠 Model AI Huruf (Random Forest)")
        if classifier_huruf.is_loaded:
            st.success(f"✅ Model Terpasang: `{classifier_huruf.model_path}`")
            st.markdown(f"**Jumlah Label Huruf:** {len(classifier_huruf.labels)}")
            st.markdown(f"**Daftar Label Terlatih:** `{'`, `'.join(classifier_huruf.labels)}`")
        else:
            st.warning("⚠️ Model huruf `.pkl` belum dimuat.")

        st.markdown("---")
        st.markdown("#### 🤲 Model AI Kata (Sequence Kinematics)")
        if classifier_kata.is_loaded:
            st.success("✅ Model Kata Khusus dimuat.")
        else:
            st.info("ℹ️ Menggunakan Heuristik Dinamis Real-time untuk kata: " + ", ".join(classifier_kata.DEFAULT_LABELS))

    with col_m2:
        st.markdown("#### 📁 Status File Dataset Pelatihan")
        dataset_path = Path(__file__).resolve().parents[1] / "training" / "dataset"
        csv_files = sorted(list(dataset_path.glob("*.csv"))) if dataset_path.exists() else []

        if csv_files:
            st.write(f"Ditemukan **{len(csv_files)}** file dataset rekaman:")
            ds_info = []
            for f in csv_files:
                size_kb = f.stat().st_size / 1024
                ds_info.append({"Huruf": f.stem, "Ukuran (KB)": f"{size_kb:.1f} KB"})
            st.dataframe(ds_info, width="stretch", height=260)
        else:
            st.info("Folder dataset belum berisi file rekaman.")

        st.markdown("---")
        st.markdown("#### 🛠️ Perintah CLI Cepat:")
        st.code("python training/train_model.py   # Latih ulang model dari dataset CSV\npython desktop_app.py           # Jalankan aplikasi Desktop OpenCV", language="bash")

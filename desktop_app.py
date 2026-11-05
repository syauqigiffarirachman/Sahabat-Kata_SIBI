"""Aplikasi Desktop SIBI Translator Real-time (OpenCV + MediaPipe + AI).

Menerjemahkan bahasa isyarat SIBI secara langsung melalui webcam
dengan visualisasi HUD modern, stabilisasi pose, dan fitur Text-to-Speech.
"""

from pathlib import Path
import subprocess
import sys
import threading
from typing import Optional

import cv2
import numpy as np

# Pastikan import modul core berjalan lancar
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sibi.core.camera import CAMERA_HELP, open_camera
from sibi.core.classifier import SIBIClassifier
from sibi.core.classifier_word import SIBIWordClassifier
from sibi.core.hand_detector import HandDetector
from sibi.core.normalize import normalize_landmarks
from sibi.core.sequence_buffer import SequenceBuffer, WordSequenceBuffer


def speak_async(text: str) -> None:
    """Mengucapkan teks dalam background thread tanpa menghentikan frame rate kamera."""
    if not text or not text.strip():
        return

    def _worker(teks: str):
        try:
            # Gunakan Windows SAPI SpeechSynthesizer secara native (ringan, tanpa dependensi ekstra)
            escaped = teks.replace("'", "''").replace('"', '`"')
            ps_cmd = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$synth.Rate = 0; "
                f"$synth.Speak('{escaped}');"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                check=False
            )
        except Exception as err:
            print(f"[TTS Error] {err}")

    t = threading.Thread(target=_worker, args=(text.strip(),), daemon=True)
    t.start()


def draw_hud(
    frame: np.ndarray,
    mode: str,
    current_label: str,
    confidence: float,
    progress: float,
    sentence: str,
    top_candidates: list
) -> np.ndarray:
    """Menggambar antarmuka HUD (Heads-Up Display) modern pada frame OpenCV."""
    h, w, _ = frame.shape

    # 1. Header Atas (Translucent Dark Bar)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 55), (20, 20, 25), -1)
    # 2. Footer Bawah (Kalimat Terjemahan)
    cv2.rectangle(overlay, (0, h - 85), (w, h), (20, 20, 25), -1)
    # Blend overlay transparansi
    alpha = 0.75
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    # Info Header
    mode_color = (0, 230, 115) if mode == "HURUF" else (255, 178, 50)
    cv2.putText(
        frame,
        f"SIBI TRANSLATOR [MODE: {mode}]",
        (15, 35),
        cv2.FONT_HERSHEY_DUPLEX,
        0.75,
        mode_color,
        2
    )

    # Info Kontrol Cepat di Kanan Atas
    hints = "[M] Mode  [SPACE] Spasi  [BS] Hapus  [C] Reset  [S] Suara  [Q] Keluar"
    cv2.putText(
        frame,
        hints,
        (w - 620, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (200, 200, 200),
        1
    )

    # 3. Card Prediksi Saat Ini (Kiri Atas)
    if current_label != "-":
        cv2.rectangle(frame, (15, 70), (220, 155), (35, 35, 45), -1)
        cv2.rectangle(frame, (15, 70), (220, 155), mode_color, 1)

        cv2.putText(
            frame,
            f"Isyarat: {current_label}",
            (25, 105),
            cv2.FONT_HERSHEY_DUPLEX,
            0.9,
            (255, 255, 255),
            2
        )
        cv2.putText(
            frame,
            f"Akurasi: {confidence * 100:.0f}%",
            (25, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (180, 255, 180),
            1
        )

        # Progress bar penahanan pose
        bar_x, bar_y, bar_w, bar_h = 25, 135, 180, 8
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 80, 80), -1)
        fill_w = int(bar_w * max(0.0, min(1.0, progress)))
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), (0, 255, 0), -1)

    # 4. Top Kandidat (Kanan Bawah dari Frame Tangan)
    if top_candidates:
        cand_text = " | ".join([f"{lbl}: {sc*100:.0f}%" for lbl, sc in top_candidates])
        cv2.putText(
            frame,
            f"Kandidat: {cand_text}",
            (15, h - 95),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (220, 220, 150),
            1
        )

    # 5. Kalimat Terjemahan (Footer)
    tampilan_teks = sentence if sentence.strip() else "(Menunggu isyarat tangan Anda...)"
    teks_color = (255, 255, 255) if sentence.strip() else (140, 140, 140)
    cv2.putText(
        frame,
        "TERJEMAHAN:",
        (15, h - 55),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 200, 255),
        1
    )
    cv2.putText(
        frame,
        tampilan_teks,
        (15, h - 22),
        cv2.FONT_HERSHEY_DUPLEX,
        0.85,
        teks_color,
        2
    )

    return frame


def main() -> None:
    """Fungsi utama menjalankan aplikasi desktop."""
    print("=" * 60)
    print("🤟 MEMULAI SIBI TRANSLATOR DESKTOP")
    print("=" * 60)

    try:
        detector = HandDetector(max_num_hands=2)
    except Exception as e:
        print(f"Error inisialisasi HandDetector: {e}")
        return

    classifier_huruf = SIBIClassifier()
    classifier_kata = SIBIWordClassifier(sequence_length=20)

    buf_huruf = SequenceBuffer(frame_threshold=8, min_confidence=0.65)
    buf_kata = WordSequenceBuffer(sequence_length=20, min_confidence=0.75)

    mode = "HURUF"  # Pilihan: 'HURUF' atau 'KATA'

    cap = open_camera()
    if cap is None:
        print(f"Error: {CAMERA_HELP}", file=sys.stderr)
        return

    # Set resolusi standar yang nyaman dan responsif
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("Kamera aktif!")
    print("Tombol kontrol:")
    print("  - [M]         : Ganti mode (HURUF / KATA)")
    print("  - [SPACE]     : Tambah spasi")
    print("  - [BACKSPACE] : Hapus karakter/kata terakhir")
    print("  - [C]         : Reset / Bersihkan teks")
    print("  - [S]         : Suarakan teks (TTS)")
    print("  - [Q] / [ESC] : Keluar")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error membaca frame video.")
                break

            # Cermin agar natural seperti bercermin
            frame = cv2.flip(frame, 1)

            # Deteksi landmark tangan
            frame_drawn, landmarks = detector.process(frame, draw=True)

            current_label = "-"
            confidence = 0.0
            progress = 0.0
            top_candidates = []

            if mode == "HURUF":
                if landmarks:
                    norm = normalize_landmarks(landmarks[0])
                    if len(norm) == 63:
                        current_label, confidence = classifier_huruf.predict(norm)
                        top_candidates = classifier_huruf.predict_top_k(norm, k=3)

                sentence = buf_huruf.update(current_label, confidence)
                progress = buf_huruf.progress

            else:  # mode == "KATA"
                norm = []
                wrist = None
                if landmarks:
                    norm = normalize_landmarks(landmarks[0])
                    wrist = buf_kata.wrist_track(landmarks[0])
                sentence, detected_word, conf = buf_kata.update(norm, classifier_kata, wrist=wrist)
                if detected_word != "-":
                    current_label = detected_word
                    confidence = conf
                progress = len(buf_kata.frames) / float(buf_kata.sequence_length)

            # Gambar visualisasi HUD
            frame_hud = draw_hud(
                frame_drawn,
                mode=mode,
                current_label=current_label,
                confidence=confidence,
                progress=progress,
                sentence=sentence,
                top_candidates=top_candidates
            )

            cv2.imshow("SIBI Translator Desktop", frame_hud)

            # Keyboard Input Handling
            key = cv2.waitKey(1) & 0xFF

            if key in (ord('q'), 27):  # 'q' atau ESC
                print("Keluar dari aplikasi.")
                break

            elif key == ord('m') or key == ord('M'):
                mode = "KATA" if mode == "HURUF" else "HURUF"
                print(f"[Mode berganti ke: {mode}]")

            elif key == 32:  # Tombol SPACE
                if mode == "HURUF":
                    buf_huruf.add_space()
                else:
                    buf_kata.add_space()

            elif key in (8, 127):  # Tombol BACKSPACE
                if mode == "HURUF":
                    buf_huruf.backspace()
                else:
                    buf_kata.backspace()

            elif key == ord('c') or key == ord('C'):
                if mode == "HURUF":
                    buf_huruf.clear()
                else:
                    buf_kata.clear()
                print("[Teks dibersihkan]")

            elif key == ord('s') or key == ord('S'):
                current_text = buf_huruf.text_result if mode == "HURUF" else buf_kata.text_result
                if current_text:
                    print(f"[Menyuarakan: '{current_text}']")
                    speak_async(current_text)

    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()


if __name__ == "__main__":
    main()

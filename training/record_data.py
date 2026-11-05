"""Modul perekaman data koordinat tangan untuk dataset pelatihan SIBI.

Membuka kamera, mengekstrak 21 landmark tangan MediaPipe,
menormalisasikannya, dan menyimpannya ke dalam file CSV di folder training/dataset/.
"""

import csv
import os
from pathlib import Path
import sys
import time

import cv2

# Pastikan root direktori proyek dapat diakses
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sibi.core.camera import CAMERA_HELP, open_camera
from sibi.core.hand_detector import HandDetector
from sibi.core.normalize import normalize_landmarks


def record_data():
    """Merekam sekuens koordinat tangan untuk sebuah label isyarat."""
    dataset_dir = ROOT_DIR / "training" / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 50)
    print("📹 PEREKAM DATASET KOORDINAT ISYARAT SIBI")
    print("=" * 50)

    try:
        label = input("Masukkan huruf/kata SIBI yang ingin direkam (misal: A): ").strip().upper()
    except (KeyboardInterrupt, EOFError):
        print("\nDibatalkan oleh pengguna.")
        return

    if not label:
        print("Error: Label tidak boleh kosong!")
        return

    try:
        input_frames = input("Berapa frame data yang ingin direkam? [Default: 300]: ").strip()
        jumlah_data = int(input_frames) if input_frames else 300
    except ValueError:
        print("Nilai frame tidak valid, menggunakan default 300.")
        jumlah_data = 300

    file_path = dataset_dir / f"{label}.csv"

    # Inisialisasi detector
    try:
        detector = HandDetector(max_num_hands=1)
    except Exception as e:
        print(f"Error inisialisasi HandDetector: {e}")
        return

    cap = open_camera()
    if cap is None:
        print(f"Error: {CAMERA_HELP}")
        return

    if file_path.exists() and file_path.stat().st_size > 1024:
        jawab = input(f"{file_path.name} sudah berisi data. Timpa? [y/N]: ").strip().lower()
        if jawab != "y":
            print("Dibatalkan, data lama tidak diubah.")
            cap.release()
            return

    header = ['frame_id']
    for i in range(21):
        header.extend([f'landmark_{i}_x', f'landmark_{i}_y', f'landmark_{i}_z'])
    header.append('label')

    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)

            # Hitung mundur 3 detik dengan tampilan di kamera
            print(f"\nPosisi tangan Anda! Perekaman untuk '{label}' akan dimulai dalam 3 detik...")
            start_countdown = time.time()
            while time.time() - start_countdown < 3.0:
                ret, frame = cap.read()
                if not ret:
                    break
                frame = cv2.flip(frame, 1)
                remaining = int(4 - (time.time() - start_countdown))
                cv2.putText(
                    frame,
                    f"SIAP-SIAP DALAM: {remaining}",
                    (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2,
                    (0, 165, 255),
                    3
                )
                cv2.putText(
                    frame,
                    f"Merekam Label: {label}",
                    (50, 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    2
                )
                cv2.imshow("Perekam Data SIBI", frame)
                if cv2.waitKey(30) & 0xFF == ord('q'):
                    print("Dibatalkan sebelum mulai.")
                    return

            frame_id = 0
            print(f"🔴 Merekam {jumlah_data} frame untuk '{label}'...")

            while frame_id < jumlah_data:
                ret, frame = cap.read()
                if not ret:
                    print("Gagal membaca frame kamera.")
                    break

                frame = cv2.flip(frame, 1)
                frame_processed, landmarks = detector.process(frame.copy(), draw=True)

                if landmarks:
                    norm_data = normalize_landmarks(landmarks[0])
                    if len(norm_data) == 63:
                        row = [frame_id] + norm_data + [label]
                        writer.writerow(row)
                        frame_id += 1

                        # HUD Status
                        pct = int((frame_id / jumlah_data) * 100)
                        cv2.putText(
                            frame_processed,
                            f"MEREKAM '{label}': {frame_id}/{jumlah_data} ({pct}%)",
                            (10, 35),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2
                        )
                else:
                    cv2.putText(
                        frame_processed,
                        "TANGAN TIDAK TERDETEKSI! Arahkan ke kamera",
                        (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 0, 255),
                        2
                    )

                cv2.putText(
                    frame_processed,
                    "Tekan 'q' untuk berhenti lebih awal",
                    (10, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (200, 200, 200),
                    1
                )

                cv2.imshow("Perekam Data SIBI", frame_processed)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\nPerekaman dihentikan pengguna.")
                    break

        print(f"\n✅ Selesai! {frame_id} data berhasil disimpan di: {file_path}")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()


if __name__ == "__main__":
    record_data()

# SIBI Translator 🤟

Aplikasi penerjemah Sistem Isyarat Bahasa Indonesia (SIBI) dua arah berbasis Computer Vision dan Machine Learning menggunakan Python, OpenCV, MediaPipe Tasks, dan Scikit-Learn. Aplikasi ini berjalan sepenuhnya *on-device* untuk menjamin privasi pengguna dan kecepatan inferensi maksimal.

---

## 🚀 Cara Pakai (tanpa perlu paham kode)

| Versi | Cara memakai |
|---|---|
| 🌐 **Web** (laptop / HP) | Buka **https://syauqigiffarirachman.github.io/Sahabat-Kata_SIBI/** di Chrome atau Edge. Tidak perlu instal apa pun. Izinkan kamera & mikrofon saat diminta. |
| 📱 **Android (APK)** | Unduh file `.apk` terbaru di halaman [**Releases**](https://github.com/syauqigiffarirachman/Sahabat-Kata_SIBI/releases), buka di HP, izinkan "instal dari sumber tidak dikenal", lalu pasang. Android 8.0+. |
| 🖥️ **Desktop / Streamlit** (Windows, macOS, Linux) | Perlu Python 3.10–3.12. Unduh kode lewat tombol hijau **Code → Download ZIP**, ekstrak, lalu ikuti [Panduan Instalasi](#️-panduan-instalasi--penggunaan) di bawah. |

Versi web dan APK berisi aplikasi yang sama dan semua prosesnya berjalan di perangkat sendiri
(gambar kamera tidak dikirim ke internet).

> **Untuk pengembang:** versi web ada di folder `docs/` (disajikan GitHub Pages). Setelah mengubah isi
> aplikasi, rakit ulang dengan `python tools/build_mobile.py --web`, lalu commit & push folder `docs/`.

---

## 🌟 Fitur Utama

**Fokus utama: kamus & media belajar huruf dan contoh kata untuk anak Tuli** (tab pertama di `app.py`, cepat, tanpa kamera/AI):
`Belajar Huruf` (A-Z + gambar bentuk tangan + contoh kata bergambar), `Kamus Kata` (300+ kosakata sehari-hari anak
per kategori, 39 isyarat kata, 40 kalimat sehari-hari), `Kuis` (huruf, kata, kalimat), `Eja Kata`.
Kosakata, kalimat, dan isyarat kamera ada di `sibi/content.py` (`KATEGORI`, `KALIMAT`, `KATA_KAMERA`);
logika saran kata/kalimat di `sibi/kosakata.py` (versi HP: `mobile/www/kosakata.js`).
Kamera, suara, dan status model ada di tab `Kamera & Suara` dan baru dimuat saat dibuka.
Konten ada di `sibi/content.py`. Gambar tangan realistis (kulit, jari, telapak, lengan baju) dibuat dari dataset lewat
`python tools/build_hand_shapes.py` yang menulis `sibi/data/hand_shapes.json` dan `static/hands/<HURUF>.svg`
(disajikan oleh Streamlit static serving, lihat `.streamlit/config.toml`). Jalankan ulang setelah merekam ulang huruf.
Deskripsi bentuk tangan perlu diverifikasi guru SLB / pedoman resmi SIBI.

1. **🤟 Isyarat ke Teks (Real-time Hand Tracking)**
   - Deteksi 21 koordinat 3D sendi tangan menggunakan MediaPipe HandLandmarker.
   - Normalisasi posisi dan skala (invariant terhadap jarak dan sudut kamera).
   - Klasifikasi huruf statis (A-Z) dan 15 isyarat kata sederhana: gerak (HALO, YA, TIDAK, MAKAN,
     TERIMA KASIH, MAAF, SAYA) dan pose diam (BAGUS, SAYANG, TELEPON, SATU-LIMA), dari bentuk jari + lintasan pergelangan.
   - Eja huruf → kata: saran kata dari kosakata anak muncul saat mengeja; kata & isyarat kata tersusun menjadi
     satu kalimat yang dirapikan ("Saya mau makan.") dengan saran kalimat sehari-hari yang mirip.
   - Stabilisasi pengetikan dengan *hold progress indicator* dan anti-jitter.
   - Pengenal kata masih berbasis aturan; untuk isyarat SIBI yang lebih banyak/akurat perlu rekaman data kata
     dan model kata terlatih (`models/sibi_word_model.pkl`, otomatis dipakai bila ada).

2. **✍️ Teks ke Isyarat (Visualisasi Ejaan Jari)**
   - Mengubah teks Bahasa Indonesia menjadi rangkaian visualisasi gerakan tangan dan ejaan alfabet SIBI.

3. **📖 Kamus SIBI Interaktif**
   - Panduan lengkap bentuk tangan huruf alfabet SIBI (A-Z) dan kata dasar.
   - Disertai deskripsi detail posisi jari, tips akurasi, dan fitur pencarian interaktif.

4. **🎙️ Audio Hub Dua Arah (TTS & STT)**
   - **Text-to-Speech (TTS)**: Membaca teks hasil terjemahan dalam suara Bahasa Indonesia alami.
   - **Speech-to-Text (STT)**: Menerjemahkan suara Teman Dengar melalui mikrofon menjadi teks dan isyarat jari untuk Teman Tuli.

5. **🖥️ Pilihan Antarmuka Ganda**
   - **Web App (Streamlit + WebRTC)**: Tampilan visual interaktif, ramah pengguna, dan multi-tab.
   - **Desktop App (OpenCV Native)**: Ultra-ringan, latensi rendah, dengan visualisasi HUD modern dan shortcut keyboard.

---

## 📱 Aplikasi Android (APK)

File siap pasang: **`dist/IsyaratSIBI-1.1.0.apk`** (Android 8.0+, ±30 MB, berjalan tanpa internet).
Isinya: Belajar huruf (foto tangan + wajah bicara + suara manusia), Kamus, Kuis, Eja kata, dan
Kamera & suara (isyarat → teks dengan MediaPipe di HP, suara/teks → isyarat).
Cara pasang, build ulang, dan kunci tanda tangan: lihat [android/README.md](android/README.md).

---

## 📁 Struktur Direktori

```text
sibi-translator/
├── app.py                     # Aplikasi Web Streamlit multi-fitur
├── desktop_app.py             # Aplikasi Desktop OpenCV real-time dengan HUD
├── hand_landmarker.task       # Model MediaPipe Tasks pendeteksi tangan
├── requirements.txt           # Daftar pustaka & dependensi Python
├── README.md                  # Dokumentasi proyek
├── .gitignore                 # Filter file build, cache, dan venv
│
├── sibi/
│   └── core/
│       ├── classifier.py      # Pengklasifikasi huruf SIBI (Random Forest)
│       ├── classifier_word.py # Pengklasifikasi kata dinamis (Kinematika & ML)
│       ├── hand_detector.py   # Detektor tangan MediaPipe Tasks
│       ├── normalize.py       # Algoritma normalisasi translasi & skala
│       └── sequence_buffer.py # Penstabil sekuens huruf & kata
│
├── models/
│   ├── sibi_model.pkl         # Model ML terlatih untuk klasifikasi huruf
│   └── model_metadata.json    # Informasi kelas, akurasi, & tanggal pelatihan
│
├── training/
│   ├── record_data.py         # Skrip perekam dataset isyarat baru dari kamera
│   ├── train_model.py         # Skrip pelatihan model Random Forest dari CSV
│   └── dataset/               # Dataset koordinat landmark CSV (A.csv, B.csv, ...)
│
└── tests/
    ├── test_environment.py    # Pengujian modul dependensi
    ├── test_normalize.py      # Pengujian translasi & skala normalisasi
    ├── test_sequence_buffer.py# Pengujian logika buffer & toleransi jitter
    └── test_classifier.py     # Pengujian modul pengklasifikasi
```

---

## ⚙️ Panduan Instalasi & Penggunaan

### 1. Prasyarat Lingkungan
Pastikan Anda telah menginstal **Python 3.10, 3.11, atau 3.12**.

### 2. Buat & Aktifkan Virtual Environment
```bash
# Buat virtual environment baru
python -m venv .venv

# Aktivasi di Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Atau di Command Prompt (CMD):
.venv\Scripts\activate.bat

# Atau di Linux/macOS:
source .venv/bin/activate
```

### 3. Instal Dependensi
```bash
pip install -r requirements.txt
```

---

## 🚀 Menjalankan Aplikasi

### A. Menjalankan Aplikasi Web (Streamlit)
```bash
streamlit run app.py
```
Aplikasi akan otomatis terbuka di browser pada alamat `http://localhost:8501`.

### B. Menjalankan Aplikasi Desktop (OpenCV Native)
```bash
python desktop_app.py
```

**Tombol Pintas Aplikasi Desktop:**
- `[M]` : Beralih antara mode **HURUF** dan **KATA**
- `[SPACE]` : Menambahkan spasi pada kalimat
- `[BACKSPACE]` : Menghapus satu karakter/kata terakhir
- `[C]` : Membersihkan / mereset seluruh teks
- `[S]` : Menyuarakan kalimat dengan Text-to-Speech (TTS)
- `[Q]` atau `[ESC]` : Keluar dari aplikasi

---

## 🎓 Menambah & Melatih Dataset Baru

Jika Anda ingin merekam huruf baru atau memperkaya dataset:

1. **Merekam Data Isyarat Baru:**
   ```bash
   python training/record_data.py
   ```
   - Masukkan huruf yang ingin direkam (misal: `G`).
   - Tahan pose isyarat tangan Anda di depan kamera selama proses perekaman.
   - File dataset akan tersimpan di `training/dataset/{HURUF}.csv`.

2. **Melatih Model AI:**
   ```bash
   python training/train_model.py
   ```
   - Skrip akan membaca seluruh file CSV di `training/dataset/`, melatih Random Forest Classifier, mencetak metrik akurasi & laporan klasifikasi, dan menyimpan model terbaru ke `models/sibi_model.pkl`.

---

## 🧪 Menjalankan Pengujian (Unit Tests)
```bash
pytest tests/ -v
```

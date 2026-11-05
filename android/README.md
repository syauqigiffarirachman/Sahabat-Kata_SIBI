# Isyarat SIBI — aplikasi Android (APK)

Aplikasi HP ini adalah versi offline dari SIBI Translator: Belajar huruf (foto tangan,
wajah bicara + suara manusia), Kamus kata, Kuis, Eja kata, serta Kamera & suara
(isyarat → teks dan suara/teks → isyarat). Semuanya berjalan di HP tanpa internet.

## Pasang di HP

1. Salin `dist/IsyaratSIBI-1.1.0.apk` ke HP (kabel USB, Google Drive, atau WhatsApp ke diri sendiri).
2. Buka file APK di HP. Bila diminta, izinkan **Instal aplikasi tidak dikenal** untuk aplikasi
   yang dipakai membuka file (mis. File Manager / Chrome).
3. Buka **Isyarat SIBI**. Izin kamera diminta saat fitur Kamera dipakai, izin mikrofon saat tombol *Bicara* dipakai.

Syarat: Android 8.0 ke atas. Suara huruf & contoh kata sudah ada di dalam APK; kata lain
memakai suara Bahasa Indonesia bawaan HP (Google TTS). Fitur *Bicara* memakai pengenal
suara Google (butuh internet, atau paket bahasa Indonesia offline).

## Susunan

| Bagian | Isi |
|---|---|
| `mobile/www/` | Kode aplikasi HP (HTML/CSS/JS): `app.js`, `kamera.js`, `suara.js` |
| `sibi/mulut.js`, `sibi/mulut.css` | Wajah bicara, dipakai bersama dengan versi Streamlit |
| `mobile/vendor/` | MediaPipe Tasks Vision 0.10.14 (Apache 2.0) dan font Nunito (OFL) |
| `android/app/src/main/java/.../MainActivity.java` | WebView, penyaji aset offline, jembatan TTS / pengenal suara / getar |
| `android/app/src/main/assets/www/` | **Dibuat otomatis** oleh `tools/build_mobile.py` (jangan diedit) |

## Build ulang APK

```bash
python tools/build_model_mobile.py   # hanya bila dataset huruf berubah
python tools/build_suara.py          # hanya bila huruf/contoh kata berubah
python tools/build_mobile.py         # rakit aset ke android/app/src/main/assets/www
cd android
gradle assembleRelease               # butuh JDK 17 + Android SDK 34
```

Hasil: `android/app/build/outputs/apk/release/app-release.apk`.

Di komputer pengembang ini alatnya ada di `D:\android-tools` (JDK 17, Gradle 8.7, Android SDK):

```bash
set JAVA_HOME=D:\android-tools\jdk17
set GRADLE_USER_HOME=D:\android-tools\gradle-home
D:\android-tools\gradle-8.7\bin\gradle assembleRelease
```

Naikkan `versionCode` dan `versionName` di `android/app/build.gradle` setiap rilis baru.

## Kunci tanda tangan (PENTING)

APK rilis ditandatangani dengan `android/sibi-rilis.jks`; kata sandinya ada di
`android/keystore.properties`. **Simpan cadangan kedua file ini di tempat aman dan jangan
dibagikan.** Pembaruan aplikasi di HP yang sudah terpasang hanya bisa dipasang bila
ditandatangani dengan kunci yang sama.

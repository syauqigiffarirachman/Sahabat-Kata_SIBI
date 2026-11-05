# Panduan Merekam Huruf yang Belum Ada Gambarnya

Huruf yang masih kosong (16): **G, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z**

Gambar bentuk tangan di kamus dibuat dari rekaman kamera. Rekam tiap huruf sekali, lalu bangun ulang gambarnya.

## Langkah (per huruf)

1. Aktifkan virtual environment, lalu jalankan `python training/record_data.py`.
2. Ketik hurufnya (misal `L`), tekan Enter. Jumlah frame biarkan default (300), Enter.
3. Bentuk tangan sesuai deskripsi di bawah, tahan **diam** sampai selesai. Tekan `q` untuk batal.
4. Ulangi untuk huruf berikutnya.
5. Setelah semua selesai: `python tools/build_hand_shapes.py` (gambar kamus & kuis ikut bertambah).
6. Agar huruf baru juga dikenali kamera: `python training/train_model.py`.

## Tips agar hasil bagus

- Cahaya terang dari depan, latar polos, satu tangan saja di tengah layar.
- Tangan yang sama dan jarak yang sama tiap huruf; telapak menghadap kamera kecuali deskripsi menyebut lain.
- Pelan-pelan gerakkan sedikit tangan (maju-mundur, miring tipis) selama merekam agar model tidak kaku.
- J dan Z bergerak: gambar kamus hanya menunjukkan posisi awal, rekam posisi awalnya saja.
- Minta guru SLB memeriksa bentuk tangan sebelum direkam; deskripsi di bawah belum diverifikasi resmi.

## Daftar huruf dan bentuknya

| Huruf | Bentuk tangan | Tips |
|---|---|---|
| **G** | Arahkan jari telunjuk dan ibu jari mendatar horizontal ke samping sejajar, jari lainnya menekuk. | Kedua jari terentang sejajar seperti memegang objek kecil. |
| **L** | Buka ibu jari dan jari telunjuk membentuk sudut siku-siku 90 derajat (huruf L), lipat jari lainnya. | Bentuk sudut L yang jelas tegak lurus. |
| **M** | Selipkan ibu jari di bawah tiga jari pertama (telunjuk, tengah, manis) yang melipat ke bawah. | Ibu jari muncul di antara jari manis dan kelingking. |
| **N** | Selipkan ibu jari di bawah dua jari pertama (telunjuk dan tengah) yang melipat ke bawah. | Mirip M tapi hanya melewati 2 jari. |
| **O** | Pertemukan seluruh ujung jari dengan ujung ibu jari sehingga membentuk bulatan oval 'O'. | Pastikan lubang lingkaran terlihat dari depan. |
| **P** | Bentuk huruf 'K' namun arahkan pergelangan tangan dan kedua jari menunduk ke arah bawah. | Posisi K yang dibalik mengarah ke bawah. |
| **Q** | Bentuk huruf 'G' namun arahkan ujung jari telunjuk dan ibu jari ke bawah diagonal. | Posisi G yang mengarah ke lantai. |
| **R** | Silangkan jari tengah di belakang jari telunjuk yang keduanya berdiri tegak lurus. | Posisi jari menyilang seperti gesture 'fingers crossed'. |
| **S** | Kepalkan seluruh jari dengan ibu jari melintang di depan jari-jari lainnya. | Ibu jari berada di depan telunjuk, tengah, dan manis. |
| **T** | Selipkan ibu jari di bawah jari telunjuk yang melipat, di antara telunjuk dan jari tengah. | Ibu jari mencuat di antara telunjuk dan tengah. |
| **U** | Tegakkan jari telunjuk dan jari tengah lurus ke atas rapat tanpa celah, lipat jari lainnya. | Dua jari tegak merapat rapat. |
| **V** | Tegakkan jari telunjuk dan jari tengah lurus ke atas membuka membentuk huruf V. | Kedua jari terbuka lebar membentuk huruf V. |
| **W** | Tegakkan jari telunjuk, jari tengah, dan jari manis lurus ke atas membuka huruf 'W'. | Tiga jari tegak seperti garpu. |
| **X** | Tegakkan jari telunjuk lalu tekuk ruas atasnya membentuk pengait/kait. | Jari telunjuk melengkung seperti kait pancing. |
| **Y** | Rentangkan ibu jari dan kelingking lebar ke samping, kepalkan tiga jari tengah. | Gesture 'Hang Loose' / telepon. |
| **Z** | Gunakan jari telunjuk yang tegak untuk menggambar pola huruf 'Z' di udara. | Gerakan dinamis zig-zag di udara. |

## Checklist

- [ ] G
- [ ] L
- [ ] M
- [ ] N
- [ ] O
- [ ] P
- [ ] Q
- [ ] R
- [ ] S
- [ ] T
- [ ] U
- [ ] V
- [ ] W
- [ ] X
- [ ] Y
- [ ] Z

"""Modul penstabil sekuens (stabilizer buffer) untuk deteksi huruf dan kata SIBI.

Mencegah flickering / bouncing pembacaan isyarat, memberikan mekanisme penahanan pose,
serta menyediakan fasilitas manipulasi teks (spasi, hapus, reset).
"""

from collections import deque
from typing import Deque, List, Optional, Tuple


class SequenceBuffer:
    """Penstabil untuk HURUF (Pose Statis).

    Mengharuskan pengguna menahan pose isyarat selama sejumlah frame berturut-turut
    sebelum huruf diakui dan diketikkan ke dalam kalimat.
    """

    def __init__(
        self,
        frame_threshold: int = 10,
        min_confidence: float = 0.65,
        repeat_threshold: int = 35
    ):
        """Inisialisasi SequenceBuffer.

        Args:
            frame_threshold: Jumlah frame berturut-turut untuk mengetikkan huruf.
            min_confidence: Ambang keyakinan minimal model untuk memproses huruf.
            repeat_threshold: Jumlah frame tahanan untuk mengulang pengetikan huruf yang sama.
        """
        self.frame_threshold = frame_threshold
        self.min_confidence = min_confidence
        self.repeat_threshold = repeat_threshold

        self.current_char: str = ""
        self.char_count: int = 0
        self.last_added_char: str = ""
        self.text_result: str = ""
        self.last_confidence: float = 0.0
        self.empty_frame_tolerance: int = 0  # Toleransi 2 frame kosong/jitter

    @property
    def progress(self) -> float:
        """Persentase progress penahanan pose saat ini (0.0 sampai 1.0)."""
        if not self.current_char or self.frame_threshold <= 0:
            return 0.0
        return min(1.0, float(self.char_count) / float(self.frame_threshold))

    def update(self, char: str, confidence: float) -> str:
        """Memperbarui buffer dengan tebakan frame saat ini.

        Args:
            char: Huruf tebakan saat ini (misal 'A', 'B', atau '-').
            confidence: Skor keyakinan model (0.0 - 1.0).

        Returns:
            Kalimat/teks akumulasi hasil terjemahan.
        """
        self.last_confidence = confidence

        # Tangani jika tangan tidak terdeteksi atau confidence rendah
        if char == "-" or confidence < self.min_confidence:
            self.empty_frame_tolerance += 1
            if self.empty_frame_tolerance > 2:
                # Reset penahan setelah 3 frame berturut-turut hilang
                self.current_char = ""
                self.char_count = 0
                self.last_added_char = ""
                self.empty_frame_tolerance = 0
            return self.text_result

        # Reset toleransi jika frame valid
        self.empty_frame_tolerance = 0

        # Jika huruf sama dengan frame sebelumnya
        if char == self.current_char:
            self.char_count += 1
        else:
            self.current_char = char
            self.char_count = 1

        # Kondisi 1: Huruf baru mencapai threshold
        if self.char_count == self.frame_threshold and self.current_char != self.last_added_char:
            self.text_result += self.current_char
            self.last_added_char = self.current_char

        # Kondisi 2: Pengguna sengaja menahan huruf sangat lama (repeat typing)
        elif self.char_count >= self.repeat_threshold:
            self.text_result += self.current_char
            self.char_count = self.frame_threshold  # Beri jeda siklus berikutnya

        return self.text_result

    def clear(self) -> str:
        """Mereset seluruh teks dan buffer."""
        self.text_result = ""
        self.last_added_char = ""
        self.current_char = ""
        self.char_count = 0
        return self.text_result

    def add_space(self) -> str:
        """Menambahkan spasi ke dalam teks hasil."""
        if self.text_result and not self.text_result.endswith(" "):
            self.text_result += " "
            self.last_added_char = " "
        return self.text_result

    def backspace(self) -> str:
        """Menghapus 1 karakter terakhir."""
        if self.text_result:
            self.text_result = self.text_result[:-1]
            self.last_added_char = ""
        return self.text_result

    def get_status(self) -> dict:
        """Mendapatkan snapshot status buffer untuk monitoring UI."""
        return {
            "current_char": self.current_char,
            "char_count": self.char_count,
            "progress": self.progress,
            "confidence": self.last_confidence,
            "text": self.text_result
        }


class WordSequenceBuffer:
    """Penstabil untuk KATA (Gerakan Dinamis).

    Mengumpulkan sekumpulan frame secara sliding window untuk mengenali
    pola gestur kata berurutan.
    """

    def __init__(
        self,
        sequence_length: int = 20,
        cooldown_frames: int = 25,
        min_confidence: float = 0.75
    ):
        """Inisialisasi WordSequenceBuffer.

        Args:
            sequence_length: Jumlah frame yang dianalisis dalam 1 window.
            cooldown_frames: Jumlah frame jeda setelah kata terdeteksi.
            min_confidence: Ambang keyakinan minimal deteksi kata.
        """
        self.sequence_length = sequence_length
        self.cooldown_frames = cooldown_frames
        self.min_confidence = min_confidence

        self.frames: Deque[List[float]] = deque(maxlen=sequence_length)
        self.wrists: Deque[Tuple[float, float, float]] = deque(maxlen=sequence_length)
        self.cooldown: int = 0
        self.text_result: str = ""
        self.last_detected_word: str = "-"
        self.last_confidence: float = 0.0
        # Kata yang baru saja diketik: tidak diketik ulang selama isyaratnya masih ditahan
        # (mis. jempol tetap diangkat). Dilepas saat tangan turun atau isyarat berganti.
        self._ditahan: str = ""

    @staticmethod
    def wrist_track(raw_landmarks) -> Optional[Tuple[float, float, float]]:
        """(x, y, ukuran_telapak) pergelangan dari 21 landmark mentah (koordinat gambar 0..1)."""
        if raw_landmarks is None or len(raw_landmarks) != 21:
            return None
        x0, y0 = float(raw_landmarks[0][0]), float(raw_landmarks[0][1])
        x9, y9 = float(raw_landmarks[9][0]), float(raw_landmarks[9][1])
        return (x0, y0, ((x9 - x0) ** 2 + (y9 - y0) ** 2) ** 0.5)

    def update(
        self,
        normalized_landmarks: Optional[List[float]],
        classifier,
        wrist: Optional[Tuple[float, float, float]] = None,
    ) -> Tuple[str, str, float]:
        """Memperbarui buffer gerakan kata.

        Args:
            normalized_landmarks: Koordinat landmark ternormalisasi frame saat ini.
            classifier: Objek SIBIWordClassifier yang memiliki method predict().
            wrist: Opsional (x, y, ukuran_telapak) pergelangan di gambar, lihat wrist_track().
                Dengan ini lebih banyak kata gerak bisa dikenali.

        Returns:
            Tuple (text_result, detected_word, confidence):
                text_result: Teks lengkap kalimat kata yang tersusun.
                detected_word: Kata yang baru terdeteksi pada frame ini (atau '-').
                confidence: Skor keyakinan model.
        """
        detected_word = "-"
        confidence = 0.0

        if self.cooldown > 0:
            self.cooldown -= 1
            self.frames.clear()
            self.wrists.clear()
            if not normalized_landmarks:
                self._ditahan = ""
            return self.text_result, detected_word, confidence

        if not normalized_landmarks:
            self.frames.clear()
            self.wrists.clear()
            self._ditahan = ""
            return self.text_result, detected_word, confidence

        self.frames.append(normalized_landmarks)
        if wrist is not None:
            self.wrists.append(tuple(wrist))
        else:
            self.wrists.clear()

        # Jika sliding window penuh
        if len(self.frames) == self.sequence_length:
            if len(self.wrists) == self.sequence_length:
                word, conf = classifier.predict(list(self.frames), wrists=list(self.wrists))
            else:
                word, conf = classifier.predict(list(self.frames))
            confidence = conf

            if word != self._ditahan:
                self._ditahan = ""
            if conf >= self.min_confidence and word != "-" and word != self._ditahan:
                detected_word = word
                self._ditahan = word
                self.last_detected_word = word
                self.last_confidence = conf

                if not self.text_result:
                    self.text_result = word
                else:
                    self.text_result += " " + word

                self.cooldown = self.cooldown_frames
                self.frames.clear()
                self.wrists.clear()

        return self.text_result, detected_word, confidence

    def clear(self) -> str:
        """Mereset seluruh teks kata."""
        self.text_result = ""
        self.last_detected_word = "-"
        self.frames.clear()
        self.wrists.clear()
        self.cooldown = 0
        self._ditahan = ""
        return self.text_result

    def backspace(self) -> str:
        """Menghapus kata terakhir."""
        words = self.text_result.strip().split()
        if words:
            self.text_result = " ".join(words[:-1])
        else:
            self.text_result = ""
        return self.text_result

    def add_space(self) -> str:
        """Menambahkan pemisah spasi."""
        if self.text_result and not self.text_result.endswith(" "):
            self.text_result += " "
        return self.text_result

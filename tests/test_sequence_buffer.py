"""Unit test untuk SequenceBuffer dan WordSequenceBuffer."""

import pytest

from sibi.core.sequence_buffer import SequenceBuffer, WordSequenceBuffer


def test_sequence_buffer_char_accumulation():
    """Memastikan huruf baru diketik setelah mencapai ambang batas frame."""
    buf = SequenceBuffer(frame_threshold=5, min_confidence=0.7)

    # 4 frame 'A': belum mencapai threshold (5)
    for _ in range(4):
        res = buf.update("A", 0.9)
    assert res == ""
    assert buf.progress < 1.0

    # Frame ke-5 'A': threshold tercapai
    res = buf.update("A", 0.9)
    assert res == "A"
    assert buf.progress == 1.0

    # Frame ke-6 'A': tidak mengulang ketik sebelum repeat threshold
    res = buf.update("A", 0.9)
    assert res == "A"


def test_sequence_buffer_text_editing():
    """Memastikan fitur spasi, backspace, dan clear berfungsi dengan tepat."""
    buf = SequenceBuffer(frame_threshold=3)

    buf.text_result = "HALO"
    buf.add_space()
    assert buf.text_result == "HALO "

    # Menambahkan spasi lagi tidak membuat spasi ganda berturut-turut
    buf.add_space()
    assert buf.text_result == "HALO "

    buf.backspace()
    assert buf.text_result == "HALO"

    buf.clear()
    assert buf.text_result == ""
    assert buf.current_char == ""


def test_sequence_buffer_jitter_tolerance():
    """Memastikan jitter 1-2 frame tidak langsung mereset progres huruf."""
    buf = SequenceBuffer(frame_threshold=5, min_confidence=0.7)

    # 3 frame A
    for _ in range(3):
        buf.update("A", 0.9)
    assert buf.char_count == 3

    # 1 frame jitter / frame kosong
    buf.update("-", 0.0)
    # Toleransi jitter harus menjaga char_count tidak langsung 0
    assert buf.char_count == 3

    # Frame A kembali valid
    buf.update("A", 0.9)
    assert buf.char_count == 4


def test_word_sequence_buffer_cooldown():
    """Memastikan WordSequenceBuffer menerapkan windowing dan cooldown."""
    buf = WordSequenceBuffer(sequence_length=5, cooldown_frames=3, min_confidence=0.8)

    class MockClassifier:
        sequence_length = 5
        def predict(self, frames):
            return "HALO", 0.95

    mock_clf = MockClassifier()
    dummy_frame = [0.1] * 63

    # 4 frame: belum penuh
    for _ in range(4):
        text, word, conf = buf.update(dummy_frame, mock_clf)
        assert text == ""
        assert word == "-"

    # Frame ke-5: sliding window penuh -> prediksi terpicu
    text, word, conf = buf.update(dummy_frame, mock_clf)
    assert text == "HALO"
    assert word == "HALO"
    assert conf >= 0.8
    assert buf.cooldown == 3


def test_word_sequence_buffer_backspace():
    """Memastikan penghapusan satu kata terakhir bekerja secara teratur."""
    buf = WordSequenceBuffer()
    buf.text_result = "HALO SAYA BUDI"
    buf.backspace()
    assert buf.text_result == "HALO SAYA"
    buf.backspace()
    assert buf.text_result == "HALO"
    buf.backspace()
    assert buf.text_result == ""

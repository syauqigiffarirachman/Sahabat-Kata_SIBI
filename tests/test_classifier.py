"""Unit test untuk modul pengklasifikasi huruf dan kata SIBI."""

from sibi.core.classifier import SIBIClassifier
from sibi.core.classifier_word import SIBIWordClassifier


def test_sibi_classifier_invalid_inputs():
    """Memastikan SIBIClassifier menangani input tidak valid tanpa error."""
    clf = SIBIClassifier(model_path="non_existent_file.pkl")

    # Model tidak tersedia
    assert not clf.is_loaded
    label, conf = clf.predict([])
    assert label == "-"
    assert conf == 0.0

    # Input dengan panjang tidak sesuai 63 fitur
    label, conf = clf.predict([0.1] * 20)
    assert label == "-"
    assert conf == 0.0

    assert clf.predict_top_k([0.1] * 20) == []


def test_sibi_word_classifier_heuristics():
    """Memastikan SIBIWordClassifier heuristik mendeteksi ketiadaan gerak dan input pendek."""
    clf = SIBIWordClassifier(sequence_length=10)

    # Frame kurang dari sequence length (10)
    frames_pendek = [[0.0] * 63 for _ in range(5)]
    word, conf = clf.predict(frames_pendek)
    assert word == "-"
    assert conf == 0.0

    # Gerakan diam statis (semua frame nilainya sama persis)
    frames_diam = [[0.5] * 63 for _ in range(10)]
    word, conf = clf.predict(frames_diam)
    assert word == "-"
    assert conf == 0.0

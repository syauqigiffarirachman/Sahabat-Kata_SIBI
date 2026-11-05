"""Modul pelatihan model Machine Learning untuk klasifikasi isyarat SIBI.

Membaca dataset koordinat CSV dari folder training/dataset/,
melatih Random Forest Classifier, mengevaluasi metrik akurasi & classification report,
dan menyimpan bobot model ke models/sibi_model.pkl beserta metadata.
"""

from datetime import datetime
import json
from pathlib import Path
import pickle
import sys
from typing import Optional

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


def train_sibi(
    dataset_dir: Optional[str] = None,
    output_model_path: Optional[str] = None,
    test_size: float = 0.2,
    random_state: int = 42
) -> Optional[dict]:
    """Melatih model klasifikasi huruf SIBI dari dataset CSV.

    Args:
        dataset_dir: Direktori berisi file rekaman CSV.
        output_model_path: Path tujuan penyimpanan file model .pkl.
        test_size: Proporsi data uji (default 0.2 = 20%).
        random_state: Seed random untuk reprodusibilitas.

    Returns:
        Dictionary ringkasan hasil pelatihan atau None jika gagal.
    """
    root_dir = Path(__file__).resolve().parents[1]

    if dataset_dir:
        data_path = Path(dataset_dir)
    else:
        data_path = root_dir / "training" / "dataset"

    if output_model_path:
        model_file = Path(output_model_path)
    else:
        model_file = root_dir / "models" / "sibi_model.pkl"

    csv_files = sorted(list(data_path.glob("*.csv")))
    if not csv_files:
        print(f"Error: Tidak ada file CSV ditemukan di direktori {data_path}!", file=sys.stderr)
        return None

    print("=" * 60)
    print("🚀 MEMULAI PELATIHAN MODEL SIBI TRANSLATOR")
    print("=" * 60)
    print(f"Direktori Dataset : {data_path}")
    print(f"Jumlah File Data  : {len(csv_files)} file")

    # 1. Menggabungkan seluruh data CSV
    dfs = []
    class_counts = {}
    for f in csv_files:
        df_temp = pd.read_csv(f)
        label_name = f.stem
        count = len(df_temp)
        class_counts[label_name] = count
        print(f"  - Membaca '{label_name}': {count} baris data")
        dfs.append(df_temp)

    data = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal Sampel Keseluruhan: {len(data)} baris")

    # 2. Memisahkan Fitur (X) dan Target (y)
    drop_cols = [col for col in ['frame_id', 'label'] if col in data.columns]
    X = data.drop(columns=drop_cols)
    y = data['label'].astype(str)

    expected_features = 63
    if X.shape[1] != expected_features:
        print(f"Peringatan: Jumlah fitur ({X.shape[1]}) berbeda dari standar ({expected_features})!")

    # 3. Bagi data Train dan Test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    print(f"Ukuran Data Belajar (Train): {len(X_train)} ({100-test_size*100:.0f}%)")
    print(f"Ukuran Data Uji (Test)     : {len(X_test)} ({test_size*100:.0f}%)")

    # 4. Melatih Random Forest Classifier
    print("\n⏳ Melatih Random Forest Classifier (150 estimator)...")
    clf = RandomForestClassifier(
        n_estimators=150,
        max_depth=25,
        random_state=random_state,
        n_jobs=-1
    )
    clf.fit(X_train, y_train)

    # 5. Evaluasi Performa
    y_pred = clf.predict(X_test)
    akurasi = float(accuracy_score(y_test, y_pred))
    report = classification_report(y_test, y_pred, output_dict=True)

    print("\n" + "=" * 60)
    print(f"🎯 HASIL EVALUASI MODEL: AKURASI = {akurasi * 100:.2f}%")
    print("=" * 60)
    print(classification_report(y_test, y_pred))

    # 6. Simpan Model dan Metadata
    model_file.parent.mkdir(parents=True, exist_ok=True)
    with open(model_file, 'wb') as f:
        pickle.dump(clf, f)
    print(f"✅ Model tersimpan di: {model_file}")

    metadata = {
        "created_at": datetime.now().isoformat(),
        "accuracy": akurasi,
        "n_samples": len(data),
        "classes": sorted(list(y.unique())),
        "class_counts": class_counts,
        "n_features": X.shape[1],
        "model_type": "RandomForestClassifier(n_estimators=150)",
    }
    meta_path = model_file.parent / "model_metadata.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f"📋 Metadata tersimpan di: {meta_path}\n")

    return metadata


if __name__ == "__main__":
    train_sibi()

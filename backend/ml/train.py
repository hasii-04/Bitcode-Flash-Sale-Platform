"""
Trainer Agent
=============
Trains a Random Forest classifier on bot_training_data.csv.
Saves the trained model to ml/bot_model.joblib and prints Precision / Recall.

Usage (from the backend/ directory):
    python -m ml.train
"""

import os
import sys
import pathlib

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, precision_score, recall_score
import joblib

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE = pathlib.Path(__file__).parent          # …/backend/ml/
DATA_PATH = HERE / "bot_training_data.csv"
MODEL_PATH = HERE / "bot_model.joblib"

FEATURES = ["req_per_sec", "click_latency_ms", "is_mobile", "header_consistency"]
TARGET   = "is_bot"


def train() -> None:
    # ── 1. Load data ──────────────────────────────────────────────────────────
    if not DATA_PATH.exists():
        print(f"[ERROR] Training data not found at {DATA_PATH}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    print(f"[INFO] Loaded {len(df)} samples from {DATA_PATH.name}")
    print(f"[INFO] Class distribution:\n{df[TARGET].value_counts().to_string()}\n")

    X = df[FEATURES]
    y = df[TARGET]

    # ── 2. Train / test split ─────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ── 3. Train model ────────────────────────────────────────────────────────
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=2,
        class_weight="balanced",   # handles any class imbalance gracefully
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)
    print("[INFO] Model trained successfully.\n")

    # ── 4. Evaluate ───────────────────────────────────────────────────────────
    y_pred = clf.predict(X_test)

    precision = precision_score(y_test, y_pred, pos_label=1)
    recall    = recall_score(y_test, y_pred, pos_label=1)

    print("=" * 50)
    print("  BOT-DETECTION MODEL — EVALUATION RESULTS")
    print("=" * 50)
    print(f"  Precision (bot class):  {precision:.4f}")
    print(f"  Recall    (bot class):  {recall:.4f}")
    print("=" * 50)
    print("\nFull classification report:")
    print(classification_report(y_test, y_pred, target_names=["Human", "Bot"]))

    # ── 5. Feature importance ─────────────────────────────────────────────────
    importances = dict(zip(FEATURES, clf.feature_importances_))
    print("Feature importances:")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        print(f"  {feat:<25} {imp:.4f}")

    # ── 6. Save model ─────────────────────────────────────────────────────────
    joblib.dump(clf, MODEL_PATH)
    print(f"\n[INFO] Model saved -> {MODEL_PATH}")


if __name__ == "__main__":
    train()

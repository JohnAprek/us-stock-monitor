"""Filter AI/ML: belajar dari hasil backtest strategi dasar.

Model memprediksi probabilitas sebuah sinyal berakhir profit (TP kena duluan).
Trade hanya diambil jika probabilitas >= threshold di config.
Split train/test berbasis waktu (bukan acak) supaya tidak bocor data masa depan.
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from src.features.indicators import FEATURE_COLS


def train(trades: pd.DataFrame, model_path: str, test_frac: float = 0.25) -> dict:
    data = trades.dropna(subset=FEATURE_COLS).sort_values("signal_time")
    if len(data) < 50:
        raise ValueError(
            f"Trade terlalu sedikit untuk training ({len(data)}). "
            "Perpanjang periode data atau longgarkan strategi."
        )

    X, y = data[FEATURE_COLS], data["win"]
    split = int(len(data) * (1 - test_frac))
    X_tr, X_te = X.iloc[:split], X.iloc[split:]
    y_tr, y_te = y.iloc[:split], y.iloc[split:]

    model = GradientBoostingClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8,
        random_state=42,
    )
    model.fit(X_tr, y_tr)

    proba = model.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, proba) if y_te.nunique() > 1 else float("nan")

    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    return {
        "n_train": len(X_tr),
        "n_test": len(X_te),
        "test_auc": round(auc, 3),
        "base_winrate_test": round(y_te.mean() * 100, 1),
        "model_path": model_path,
    }


def load(model_path: str):
    p = Path(model_path)
    if not p.exists():
        return None
    return joblib.load(p)

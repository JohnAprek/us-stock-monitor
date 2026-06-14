"""Backtester sederhana berbasis bar dengan SL/TP dari ATR.

- Entry di open bar berikutnya setelah sinyal (tidak ada lookahead).
- SL/TP dicek dari high/low tiap bar; jika SL dan TP kena di bar yang sama,
  diasumsikan SL duluan (konservatif).
- Spread dibebankan ke harga entry.
- Hasil tiap trade dinyatakan dalam R-multiple (risiko per trade = 1R),
  equity dihitung compounding: equity *= 1 + risk_per_trade * R.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.features.indicators import FEATURE_COLS


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.Series
    stats: dict = field(default_factory=dict)


def run_backtest(df: pd.DataFrame, signals: pd.Series, cfg: dict,
                 ml_model=None) -> BacktestResult:
    s = cfg["strategy"]
    spread = cfg["backtest"]["spread"]
    risk = cfg["risk"]["risk_per_trade"]
    equity = float(cfg["backtest"]["initial_equity"])
    threshold = cfg["ml"]["threshold"]

    opens = df["open"].values
    highs = df["high"].values
    lows = df["low"].values
    atrs = df["atr"].values
    idx = df.index

    trades = []
    eq_points = [(idx[0], equity)]
    i = 0
    n = len(df)

    while i < n - 1:
        sig = signals.iloc[i]
        if sig == 0:
            i += 1
            continue

        # filter ML: probabilitas menang harus >= threshold
        ml_prob = np.nan
        if ml_model is not None:
            feats = df.iloc[[i]][FEATURE_COLS]
            if feats.isna().any(axis=None):
                i += 1
                continue
            ml_prob = float(ml_model.predict_proba(feats)[0, 1])
            if ml_prob < threshold:
                i += 1
                continue

        entry_i = i + 1
        atr_val = atrs[i]
        if not np.isfinite(atr_val) or atr_val <= 0:
            i += 1
            continue

        entry = opens[entry_i] + spread if sig == 1 else opens[entry_i] - spread
        sl_dist = s["sl_atr"] * atr_val
        tp_dist = s["tp_atr"] * atr_val
        if sig == 1:
            sl, tp = entry - sl_dist, entry + tp_dist
        else:
            sl, tp = entry + sl_dist, entry - tp_dist

        # jalan maju sampai SL/TP kena
        r_mult = None
        exit_i = None
        for j in range(entry_i, n):
            if sig == 1:
                if lows[j] <= sl:
                    r_mult, exit_i = -1.0, j
                    break
                if highs[j] >= tp:
                    r_mult, exit_i = tp_dist / sl_dist, j
                    break
            else:
                if highs[j] >= sl:
                    r_mult, exit_i = -1.0, j
                    break
                if lows[j] <= tp:
                    r_mult, exit_i = tp_dist / sl_dist, j
                    break
        if r_mult is None:  # data habis, tutup di close terakhir
            exit_i = n - 1
            pnl = (df["close"].iloc[-1] - entry) * (1 if sig == 1 else -1)
            r_mult = pnl / sl_dist

        equity *= 1 + risk * r_mult
        eq_points.append((idx[exit_i], equity))

        row = {
            "signal_time": idx[i],
            "exit_time": idx[exit_i],
            "direction": int(sig),
            "entry": entry,
            "r_multiple": r_mult,
            "win": int(r_mult > 0),
            "ml_prob": ml_prob,
        }
        for c in FEATURE_COLS:
            row[c] = df[c].iloc[i]
        trades.append(row)

        i = exit_i + 1  # satu posisi pada satu waktu

    trades_df = pd.DataFrame(trades)
    eq = pd.Series(dict(eq_points)).sort_index()
    stats = _compute_stats(trades_df, eq, cfg)
    return BacktestResult(trades=trades_df, equity_curve=eq, stats=stats)


def _compute_stats(trades: pd.DataFrame, eq: pd.Series, cfg: dict) -> dict:
    if trades.empty:
        return {"n_trades": 0}
    r = trades["r_multiple"]
    gross_win = r[r > 0].sum()
    gross_loss = -r[r <= 0].sum()
    peak = eq.cummax()
    dd = (eq / peak - 1).min()
    return {
        "n_trades": len(trades),
        "winrate": round(trades["win"].mean() * 100, 1),
        "avg_r": round(r.mean(), 3),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else float("inf"),
        "max_drawdown_pct": round(dd * 100, 2),
        "final_equity": round(eq.iloc[-1], 2),
        "return_pct": round((eq.iloc[-1] / cfg["backtest"]["initial_equity"] - 1) * 100, 2),
    }

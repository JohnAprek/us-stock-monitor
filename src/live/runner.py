"""Live/demo runner: jalankan strategi di MetaTrader 5.

Default dry_run=true di config — hanya log sinyal, TIDAK kirim order.
Set dry_run: false hanya setelah yakin, dan SELALU mulai di akun demo.
"""
import time
from datetime import datetime, timezone

import pandas as pd

from src.data.loader import fetch_mt5
from src.features.indicators import FEATURE_COLS, add_features
from src.risk.manager import DailyGuard, lots_for_risk
from src.strategy import get_signals, ml_filter


def run_live(cfg: dict):
    import MetaTrader5 as mt5

    symbol = cfg["symbol"]
    tf = cfg["timeframe"]
    dry = cfg["live"]["dry_run"]
    magic = cfg["live"]["magic_number"]
    threshold = cfg["ml"]["threshold"]
    model = ml_filter.load(cfg["ml"]["model_path"]) if cfg["ml"]["enabled"] else None

    if not mt5.initialize():
        raise RuntimeError(f"Gagal konek MT5: {mt5.last_error()}")
    acc = mt5.account_info()
    print(f"[live] akun {acc.login} | balance {acc.balance} {acc.currency} "
          f"| {'DEMO' if acc.trade_mode == 0 else 'REAL'} | dry_run={dry}")
    if acc.trade_mode != 0 and not dry:
        print("[live] PERINGATAN: ini akun REAL dengan dry_run=false!")

    guard = DailyGuard(cfg["risk"]["max_daily_loss"])
    last_bar_time = None

    try:
        while True:
            df = fetch_mt5_inline(mt5, symbol, tf, 600)
            bar_time = df.index[-2]  # bar terakhir yang sudah close
            if bar_time == last_bar_time:
                time.sleep(cfg["live"]["poll_seconds"])
                continue
            last_bar_time = bar_time

            feat = add_features(df, cfg)
            sig = get_signals(feat, cfg).iloc[-2]
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")

            if sig == 0:
                print(f"[{now}] bar {bar_time} | tidak ada sinyal")
                continue

            row = feat.iloc[[-2]][FEATURE_COLS]
            prob = None
            if model is not None:
                prob = float(model.predict_proba(row)[0, 1])
                if prob < threshold:
                    print(f"[{now}] sinyal {'LONG' if sig==1 else 'SHORT'} "
                          f"DITOLAK ML (prob={prob:.2f} < {threshold})")
                    continue

            acc = mt5.account_info()
            if not guard.allow(datetime.now(timezone.utc).date(), acc.equity):
                print(f"[{now}] batas rugi harian tercapai — skip")
                continue
            positions = mt5.positions_get(symbol=symbol) or []
            if len(positions) >= cfg["risk"]["max_positions"]:
                print(f"[{now}] posisi maksimal sudah terbuka — skip")
                continue

            atr_val = feat["atr"].iloc[-2]
            s = cfg["strategy"]
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if sig == 1:
                price = tick.ask
                sl = price - s["sl_atr"] * atr_val
                tp = price + s["tp_atr"] * atr_val
                order_type = mt5.ORDER_TYPE_BUY
            else:
                price = tick.bid
                sl = price + s["sl_atr"] * atr_val
                tp = price - s["tp_atr"] * atr_val
                order_type = mt5.ORDER_TYPE_SELL

            lots = lots_for_risk(acc.equity, cfg["risk"]["risk_per_trade"],
                                 s["sl_atr"] * atr_val, info)
            tag = f"{'LONG' if sig==1 else 'SHORT'} {lots} lot @ {price:.2f} " \
                  f"SL {sl:.2f} TP {tp:.2f}" + (f" prob={prob:.2f}" if prob else "")

            if dry:
                print(f"[{now}] DRY-RUN: {tag}")
                continue

            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol, "volume": lots, "type": order_type,
                "price": price, "sl": sl, "tp": tp,
                "deviation": 20, "magic": magic,
                "comment": "ai-ea", "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            res = mt5.order_send(req)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"[{now}] ORDER TEREKSEKUSI: {tag}")
            else:
                print(f"[{now}] ORDER GAGAL ({res.retcode}): {res.comment} | {tag}")
    finally:
        mt5.shutdown()


def fetch_mt5_inline(mt5, symbol: str, timeframe: str, n: int) -> pd.DataFrame:
    """Ambil bar terbaru tanpa shutdown koneksi (untuk loop live)."""
    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, n)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"Tidak dapat data live: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.set_index("time")[["open", "high", "low", "close", "tick_volume"]]
    return df.rename(columns={"tick_volume": "volume"})

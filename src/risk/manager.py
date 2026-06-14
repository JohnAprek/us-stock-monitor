"""Manajemen risiko: ukuran lot, batas rugi harian, batas posisi."""


def lots_for_risk(equity: float, risk_frac: float, sl_distance: float,
                  symbol_info) -> float:
    """Hitung lot dari risiko uang dan jarak SL.

    symbol_info: hasil mt5.symbol_info(symbol) — punya trade_tick_value,
    trade_tick_size, volume_min, volume_max, volume_step.
    """
    risk_money = equity * risk_frac
    ticks = sl_distance / symbol_info.trade_tick_size
    loss_per_lot = ticks * symbol_info.trade_tick_value
    if loss_per_lot <= 0:
        return 0.0
    lots = risk_money / loss_per_lot
    step = symbol_info.volume_step
    lots = max(symbol_info.volume_min, min(symbol_info.volume_max,
                                           round(lots / step) * step))
    return round(lots, 2)


class DailyGuard:
    """Stop trading jika rugi harian melewati batas."""

    def __init__(self, max_daily_loss: float):
        self.max_daily_loss = max_daily_loss
        self.day = None
        self.start_equity = None

    def allow(self, today, equity: float) -> bool:
        if self.day != today:
            self.day = today
            self.start_equity = equity
        if self.start_equity and equity <= self.start_equity * (1 - self.max_daily_loss):
            return False
        return True

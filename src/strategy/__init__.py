"""Dispatcher strategi: pilih lewat config.yaml -> strategy.type."""


def get_signals(df, cfg):
    stype = cfg["strategy"].get("type", "rsi_pullback")
    if stype == "breakout":
        from src.strategy import breakout
        b = cfg["strategy"].get("breakout", {}) or {}
        return breakout.generate_signals(
            df, cfg,
            asia=(b.get("asia_start", 1), b.get("asia_end", 9)),
            entry=(b.get("entry_start", 10), b.get("entry_end", 18)),
            trend_filter=b.get("trend_filter", True),
            max_range_atr=b.get("max_range_atr"),
            trend_min=b.get("trend_min", 0.0),
        )
    if stype == "rsi_pullback":
        from src.strategy import baseline
        return baseline.generate_signals(df, cfg)
    raise ValueError(f"strategy.type tidak dikenal: {stype}")

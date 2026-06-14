"""Universe pasar untuk portofolio trend-following D1.

Kriteria: likuid, makro (bukan saham individual), riwayat panjang,
dan saling melengkapi antar kelas aset.
"""

SYMBOLS = [
    # Forex majors
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
    # Forex cross (perilaku berbeda dari majors)
    "EURGBP", "AUDNZD", "EURJPY",
    # Forex exotic (tren & carry kuat, biaya lebih tinggi — diukur jujur)
    "USDMXN", "USDZAR", "USDSEK", "USDNOK",
    # Logam
    "XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD",
    # Energi spot
    "XTIUSD", "XBRUSD", "XNGUSD",
    # Indeks saham dunia
    "US500", "USTEC", "US30", "US2000",
    "DE40", "UK100", "STOXX50", "JP225", "AUS200", "HK50",
    # Crypto (tren historis kuat; spread lebar — diukur jujur)
    "BTCUSD", "ETHUSD",
]

# Universe inti untuk trading: disaring dengan kriteria OBJEKTIF ex-ante
# (biaya <= 5 bps round-trip DAN riwayat >= 8 tahun) — bukan berdasarkan
# performa backtest, supaya tidak data-snooping.
CORE_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "NZDUSD",
    "EURGBP", "EURJPY",
    "XAUUSD",
    "XTIUSD", "XBRUSD",
    "US500", "USTEC", "US30", "US2000",
    "DE40", "UK100", "STOXX50", "JP225", "HK50",
    "BTCUSD",
]

# Simbol dengan komisi $7/lot round-trip di akun raw (forex & spot metal).
# Lainnya (indeks, energi, crypto) hanya spread.
COMMISSION_SYMBOLS = {
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
    "EURGBP", "AUDNZD", "EURJPY", "USDMXN", "USDZAR", "USDSEK", "USDNOK",
    "XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD",
}


def est_cost_frac(mt5, sym: str) -> float:
    """Estimasi biaya round-trip per unit notional (fraksi harga).

    Komisi USD dikonversi kasar ke mata uang quote via harga simbol —
    cukup akurat untuk screening (deviasi <~20% pada cross/exotic).
    """
    info = mt5.symbol_info(sym)
    tick = mt5.symbol_info_tick(sym)
    price = tick.bid or tick.last
    if not price or not info:
        return 0.0
    spread_price = info.spread * info.point
    comm = 0.0
    if sym in COMMISSION_SYMBOLS:
        comm_quote = 7.0 if sym.endswith("USD") else 7.0 * price
        comm = comm_quote / info.trade_contract_size
    return (spread_price + comm) / price

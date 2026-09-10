from src.config import PARAM_META
from src.features import attach_lot_relative, lot_stats, pat_limits, robust_center_scale
from src.generate_data import textbook_maverick_lot
from src.module_a import _pat_flags


def test_pat_flags_maverick_inside_datasheet():
    """Lot mean ~10 µA, part at 45 µA, datasheet 50 µA — must be a PAT fail."""
    lot = [9.5, 10.0, 10.2, 9.8, 10.4, 9.7, 10.1, 9.9, 10.3, 10.0] * 8
    median, sigma = robust_center_scale(lot, floor=0.15)
    _, hi = pat_limits(median, sigma, sided="upper", k=6.0)
    assert hi is not None
    assert hi < 45.0
    assert 45.0 < PARAM_META["ileak"]["datasheet_max"]
    assert 45.0 > hi


def test_textbook_lot_is_static_pass_dynamic_fail():
    raw = textbook_maverick_lot()
    part = raw.loc[raw["sih_example"]].iloc[0]
    assert 44.0 < part["ileak_0h"] < 46.0
    assert part["ileak_24h"] < PARAM_META["ileak"]["datasheet_max"]
    assert not part["static_fail"]

    enriched = attach_lot_relative(raw, lot_stats(raw))
    flags = _pat_flags(enriched)
    hit = flags.loc[enriched["sih_example"], "pat_hit"]
    assert bool(hit.iloc[0])
    z = float(enriched.loc[enriched["sih_example"], "ileak_24h_z"].iloc[0])
    assert z > 6.0

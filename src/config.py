"""Domain constants for space-grade burn-in screening.

Parametric limits and PAT multipliers follow the spirit of AEC-Q001
(Part Average Testing) and MIL-STD-883 Method 1015 burn-in intervals.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"

TIMES_H = (0, 24, 96, 168)
EARLY_TIMES_H = (0, 24)
PARAMS = ("iddq", "ileak", "tpd")

PARAM_META = {
    "iddq": {
        "label": "Standby current (IDDQ)",
        "unit": "µA",
        "datasheet_max": 50.0,
        "sided": "upper",
        "color": "#4FC3F7",
    },
    "ileak": {
        "label": "Leakage current",
        "unit": "µA",
        "datasheet_max": 50.0,
        "sided": "upper",
        "color": "#FFB74D",
    },
    "tpd": {
        "label": "Propagation delay",
        "unit": "ns",
        "datasheet_max": 10.0,
        "sided": "both",
        "color": "#81C784",
    },
}

# AEC-Q001-style robust PAT: median ± k * 1.4826 * MAD
PAT_K = 6.0
MAD_TO_SIGMA = 1.4826
MIN_SIGMA_FLOOR = {
    "iddq": 0.15,
    "ileak": 0.08,
    "tpd": 0.03,
}

# Decision costs: a missed latent defect in a flight payload is catastrophic.
FN_COST = 1000.0
FP_COST = 12.0
HOLD_HEALTHY_COST = 2.0
HOLD_DEFECT_COST = 40.0

RANDOM_STATE = 42
IFOREST_CONTAMINATION = 0.06
MIN_RECALL = 0.97

N_LOTS = 24
PARTS_PER_LOT = (170, 230)

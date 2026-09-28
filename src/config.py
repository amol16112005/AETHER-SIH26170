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

# SIH26170 names these three. Live CSV and Isolation Forest stay on this set.
REQUIRED_PARAMS = ("iddq", "ileak", "tpd")
# Optional ATE columns: PAT + drift when present, skipped when the lot omits them.
OPTIONAL_PARAMS = ("vth", "idsat", "irev")
PARAMS = REQUIRED_PARAMS + OPTIONAL_PARAMS

# Room-temp IDDQ checkpoint. Temperature coefficient = (IDDQ_125C − IDDQ_25C) / DT.
TCOEFF_COLD_C = 25.0
TCOEFF_HOT_C = 125.0
TCOEFF_DT = TCOEFF_HOT_C - TCOEFF_COLD_C
TCOEFF_COLD_COL = "iddq_25c"

PARAM_META = {
    "iddq": {
        "label": "Standby current (IDDQ)",
        "unit": "µA",
        "datasheet_max": 50.0,
        "sided": "upper",
        "aging": "up",
        "required": True,
        "color": "#4FC3F7",
    },
    "ileak": {
        "label": "Leakage current",
        "unit": "µA",
        "datasheet_max": 50.0,
        "sided": "upper",
        "aging": "up",
        "required": True,
        "color": "#FFB74D",
    },
    "tpd": {
        "label": "Propagation delay",
        "unit": "ns",
        "datasheet_max": 10.0,
        "sided": "both",
        "aging": "up",
        "required": True,
        "color": "#81C784",
    },
    "vth": {
        "label": "Threshold voltage (VTH)",
        "unit": "V",
        "datasheet_max": 0.90,
        "datasheet_min": 0.28,
        "sided": "both",
        "aging": "up",
        "required": False,
        "color": "#CE93D8",
    },
    "idsat": {
        "label": "On-state saturation current (IDSAT)",
        "unit": "mA",
        "datasheet_max": 25.0,
        "datasheet_min": 4.0,
        "sided": "both",
        "aging": "down",
        "required": False,
        "color": "#F48FB1",
    },
    "irev": {
        "label": "Reverse leakage (per-junction)",
        "unit": "µA",
        "datasheet_max": 12.0,
        "sided": "upper",
        "aging": "up",
        "required": False,
        "color": "#FF8A65",
    },
}

# AEC-Q001-style robust PAT: median ± k * 1.4826 * MAD
PAT_K = 6.0
MAD_TO_SIGMA = 1.4826
MIN_SIGMA_FLOOR = {
    "iddq": 0.15,
    "ileak": 0.08,
    "tpd": 0.03,
    "vth": 0.004,
    "idsat": 0.08,
    "irev": 0.03,
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

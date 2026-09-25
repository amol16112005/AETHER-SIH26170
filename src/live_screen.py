"""Live screening of user-supplied 0 h / 24 h ATE readings."""

from __future__ import annotations

from io import BytesIO, StringIO
from typing import Any

import pandas as pd

from src.config import DATA_DIR, PARAM_META, PARAMS
from src.features import attach_lot_relative, lot_stats
from src.pipeline import ScreeningBundle, apply_models, drop_model_outputs, enrich

MEASURE_TIMES = (0, 24)
REQUIRED_MEASURES = [f"{param}_{t}h" for param in PARAMS for t in MEASURE_TIMES]
OPTIONAL_LATER = [f"{param}_{t}h" for param in PARAMS for t in (96, 168)]
IDENTITY_COLS = ("part_id", "lot_id")
INPUT_COLS = list(IDENTITY_COLS) + REQUIRED_MEASURES + OPTIONAL_LATER
_CANON_COLS = INPUT_COLS + ["process_corner", *[f"datasheet_{param}_max" for param in PARAMS]]
MIN_LOT_FOR_STABLE_PAT = 8
_BLANK_TOKENS = {"", "nan", "None"}

NOMINAL_HEALTHY = {
    "iddq_0h": 11.00,
    "iddq_24h": 11.12,
    "ileak_0h": 10.00,
    "ileak_24h": 10.12,
    "tpd_0h": 4.70,
    "tpd_24h": 4.72,
}
TEXTBOOK_MAVERICK = {
    "iddq_0h": 13.10,
    "iddq_24h": 13.40,
    "ileak_0h": 45.00,
    "ileak_24h": 45.32,
    "tpd_0h": 4.70,
    "tpd_24h": 4.73,
}


class LiveScreenError(ValueError):
    """User-facing validation error for live input."""


def _is_blank(value: object) -> bool:
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() in _BLANK_TOKENS


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    buf = StringIO()
    frame.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def template_frame() -> pd.DataFrame:
    """A small lot the inspector can download, edit, and re-upload."""
    rows = [
        {"part_id": "LIVE-0001", "lot_id": "LIVELOT", "iddq_0h": 11.05, "iddq_24h": 11.18, "ileak_0h": 10.10, "ileak_24h": 10.22, "tpd_0h": 4.70, "tpd_24h": 4.72},
        {"part_id": "LIVE-0002", "lot_id": "LIVELOT", "iddq_0h": 10.82, "iddq_24h": 10.91, "ileak_0h": 9.88, "ileak_24h": 9.97, "tpd_0h": 4.65, "tpd_24h": 4.67},
        {"part_id": "LIVE-0003", "lot_id": "LIVELOT", "iddq_0h": 11.40, "iddq_24h": 11.55, "ileak_0h": 10.35, "ileak_24h": 10.48, "tpd_0h": 4.58, "tpd_24h": 4.60},
        {"part_id": "LIVE-0004", "lot_id": "LIVELOT", "iddq_0h": 10.95, "iddq_24h": 11.04, "ileak_0h": 9.72, "ileak_24h": 9.80, "tpd_0h": 4.81, "tpd_24h": 4.83},
        {"part_id": "LIVE-0005", "lot_id": "LIVELOT", "iddq_0h": 11.22, "iddq_24h": 11.30, "ileak_0h": 10.05, "ileak_24h": 10.14, "tpd_0h": 4.69, "tpd_24h": 4.71},
        {"part_id": "LIVE-0006", "lot_id": "LIVELOT", "iddq_0h": 10.70, "iddq_24h": 10.78, "ileak_0h": 9.95, "ileak_24h": 10.03, "tpd_0h": 4.74, "tpd_24h": 4.76},
        {"part_id": "LIVE-0007", "lot_id": "LIVELOT", "iddq_0h": 11.15, "iddq_24h": 11.27, "ileak_0h": 10.28, "ileak_24h": 10.40, "tpd_0h": 4.62, "tpd_24h": 4.64},
        {"part_id": "LIVE-0008", "lot_id": "LIVELOT", "iddq_0h": 10.88, "iddq_24h": 10.96, "ileak_0h": 10.12, "ileak_24h": 10.20, "tpd_0h": 4.77, "tpd_24h": 4.79},
        {"part_id": "LIVE-0009", "lot_id": "LIVELOT", "iddq_0h": 11.08, "iddq_24h": 11.19, "ileak_0h": 9.84, "ileak_24h": 9.93, "tpd_0h": 4.66, "tpd_24h": 4.68},
        # In-spec maverick: ~45 µA leakage vs lot ~10 µA, datasheet 50 µA.
        {"part_id": "LIVE-0010", "lot_id": "LIVELOT", "iddq_0h": 13.10, "iddq_24h": 13.40, "ileak_0h": 45.00, "ileak_24h": 45.32, "tpd_0h": 4.70, "tpd_24h": 4.73},
    ]
    for i in range(11, 26):
        wobble = ((i * 3) % 9) - 4
        rows.append(
            {
                "part_id": f"LIVE-{i:04d}",
                "lot_id": "LIVELOT",
                "iddq_0h": round(11.00 + wobble * 0.08, 2),
                "iddq_24h": round(11.12 + wobble * 0.08, 2),
                "ileak_0h": round(10.00 + wobble * 0.07, 2),
                "ileak_24h": round(10.12 + wobble * 0.07, 2),
                "tpd_0h": round(4.70 + wobble * 0.02, 2),
                "tpd_24h": round(4.72 + wobble * 0.02, 2),
            }
        )
    return pd.DataFrame(rows)


def blank_frame(n: int = 6) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "part_id": [f"LIVE-{i + 1:04d}" for i in range(n)],
            "lot_id": ["LIVELOT"] * n,
            **{col: [None] * n for col in REQUIRED_MEASURES},
        }
    )


def template_csv_bytes() -> bytes:
    return _csv_bytes(template_frame())


def lotsih_demo_frame() -> pd.DataFrame:
    """0 h / 24 h export of canned lot LOTSIH, including LOTSIH-0045.

    96 h and 168 h are omitted on purpose: they are not inference inputs.
    """
    columns = ["part_id", "lot_id", *REQUIRED_MEASURES]
    lot = pd.read_csv(DATA_DIR / "burnin_parts.csv")
    lot = lot.loc[lot["lot_id"] == "LOTSIH", columns].copy()
    for col in REQUIRED_MEASURES:
        lot[col] = lot[col].astype(float).round(3)
    return lot.reset_index(drop=True)


def lotsih_demo_csv_bytes() -> bytes:
    path = DATA_DIR / "demo_lotsih_24h.csv"
    if path.exists():
        return path.read_bytes()
    return _csv_bytes(lotsih_demo_frame())


def _canon_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def _rename_to_canonical(df: pd.DataFrame) -> pd.DataFrame:
    wanted = {_canon_name(c): c for c in _CANON_COLS}
    mapping: dict[str, str] = {}
    for col in df.columns:
        key = _canon_name(col)
        if key in wanted and col != wanted[key]:
            mapping[col] = wanted[key]
    return df.rename(columns=mapping)


def _read_csv_table(data: bytes | str) -> pd.DataFrame:
    if isinstance(data, bytes):
        buf: Any = BytesIO(data)
    else:
        buf = StringIO(data)
    try:
        return pd.read_csv(buf)
    except Exception as exc:
        raise LiveScreenError(f"Could not read CSV: {exc}") from exc


def complete_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=list(IDENTITY_COLS) + REQUIRED_MEASURES + OPTIONAL_LATER)
    work = _rename_to_canonical(df)
    missing = [c for c in REQUIRED_MEASURES if c not in work.columns]
    if missing:
        raise LiveScreenError(
            "Missing required columns: "
            + ", ".join(missing)
            + ". Need part_id, lot_id (optional) and 0 h / 24 h for IDDQ, leakage, and tpd."
        )
    for col in OPTIONAL_LATER:
        if col not in work.columns:
            work[col] = float("nan")
    for col in REQUIRED_MEASURES + OPTIONAL_LATER:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    mask = work[REQUIRED_MEASURES].notna().all(axis=1)
    out = work.loc[mask].copy()
    if "part_id" not in out.columns:
        out["part_id"] = [f"LIVE-{i + 1:04d}" for i in range(len(out))]
    else:
        out["part_id"] = out["part_id"].map(lambda v: "" if _is_blank(v) else str(v).strip())
        blank = out["part_id"].eq("")
        existing = set(out.loc[~blank, "part_id"])
        n = 1
        for idx in out.index[blank]:
            while f"LIVE-{n:04d}" in existing:
                n += 1
            label = f"LIVE-{n:04d}"
            out.at[idx, "part_id"] = label
            existing.add(label)
            n += 1
    if "lot_id" not in out.columns:
        out["lot_id"] = "LIVELOT"
    else:
        out["lot_id"] = out["lot_id"].map(lambda v: "LIVELOT" if _is_blank(v) else str(v).strip())
    for param in PARAMS:
        cap = f"datasheet_{param}_max"
        if cap not in out.columns:
            out[cap] = PARAM_META[param]["datasheet_max"]
        else:
            out[cap] = pd.to_numeric(out[cap], errors="coerce").fillna(PARAM_META[param]["datasheet_max"])
    if "process_corner" not in out.columns:
        out["process_corner"] = "unknown"
    else:
        out["process_corner"] = out["process_corner"].map(
            lambda v: "unknown" if _is_blank(v) else str(v).strip()
        )
    keep = [
        "part_id",
        "lot_id",
        "process_corner",
        *REQUIRED_MEASURES,
        *OPTIONAL_LATER,
        *[f"datasheet_{param}_max" for param in PARAMS],
    ]
    return out.loc[:, keep].reset_index(drop=True)


def parse_live_upload(data: bytes | str) -> pd.DataFrame:
    """Editable grid for Screen my data. Empty 96 h / 168 h columns stay hidden.

    Scoring still goes through complete_rows, which fills those hours with NaN
    and applies datasheet / process_corner defaults.
    """
    raw = _read_csv_table(data)
    raw_cols = set(_rename_to_canonical(raw).columns)
    live = complete_rows(raw)
    drop = [col for col in OPTIONAL_LATER if col not in raw_cols]
    if "process_corner" not in raw_cols:
        drop.append("process_corner")
    drop.extend(f"datasheet_{param}_max" for param in PARAMS if f"datasheet_{param}_max" not in raw_cols)
    return live.drop(columns=drop)


def ingest_ate_lot(data: bytes | str) -> pd.DataFrame:
    """Turn an ATE CSV into the inference table. Does not train or touch the bundle.

    Required: part_id, lot_id, and 0 h / 24 h for IDDQ, leakage, and tpd.
    96 h and 168 h may be absent; they are filled with NaN and are not used
    at the 24 h gate. Datasheet caps and process_corner default when omitted.
    Labels (is_defective, defect_type) are ignored.
    """
    raw = _read_csv_table(data)
    if raw.empty:
        raise LiveScreenError("The CSV has no rows.")
    work = _rename_to_canonical(raw)
    required = list(IDENTITY_COLS) + REQUIRED_MEASURES
    missing = [col for col in required if col not in work.columns]
    if missing:
        raise LiveScreenError(
            "Missing required columns: "
            + ", ".join(missing)
            + ". At the 24 h gate the model needs part_id, lot_id, and 0 h / 24 h "
            "for IDDQ, leakage, and tpd. 96 h and 168 h can be empty. "
            "is_defective, defect_type, and later-hour labels are not required."
        )
    blank_lot = work["lot_id"].map(_is_blank)
    if bool(blank_lot.any()):
        raise LiveScreenError(
            f"lot_id is blank on {int(blank_lot.sum())} row(s). "
            "PAT is lot-relative, so every part needs the lot it belongs to. "
            "Upload the whole lot, not one row alone."
        )
    live = complete_rows(work)
    if live.empty:
        raise LiveScreenError("No complete rows. Fill 0 h and 24 h for IDDQ, leakage, and tpd.")
    return live


def lot_size_warnings(raw: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    for lot_id, n in raw.groupby("lot_id").size().items():
        if n < MIN_LOT_FOR_STABLE_PAT:
            warnings.append(
                f"Lot {lot_id} has only {n} complete part(s). "
                f"PAT median/MAD is jumpy below ~{MIN_LOT_FOR_STABLE_PAT} mates — "
                "use a larger lot, or screen one part against a reference lot."
            )
        if n == 1:
            warnings.append(
                f"Lot {lot_id} is a single part, so it *is* the lot median (z ≈ 0). "
                "Module A cannot see mavericks without lot mates. Module B drift still runs."
            )
    return warnings


def score_incoming_lot(
    raw: pd.DataFrame,
    bundle: ScreeningBundle,
    iforest_range: tuple[float, float] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Score one ingested lot with the saved bundle. Does not train.

    Screen my data and POST /screen-lot both call this.
    """
    if raw is None or raw.empty:
        raise LiveScreenError("No complete rows. Fill 0 h and 24 h for IDDQ, leakage, and tpd.")
    warnings = lot_size_warnings(raw)
    live = enrich(drop_model_outputs(raw))
    scored = apply_models(live, bundle, iforest_range=iforest_range)
    return scored, warnings


def screen_lot(
    df: pd.DataFrame,
    bundle: ScreeningBundle,
    iforest_range: tuple[float, float] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Validate rows, then score. PAT is computed inside the uploaded lot(s)."""
    return score_incoming_lot(complete_rows(df), bundle, iforest_range=iforest_range)


def screen_one_part(
    measurements: dict[str, Any],
    reference_lot: pd.DataFrame,
    bundle: ScreeningBundle,
    iforest_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Score one part against a frozen reference lot's median / MAD."""
    ref = reference_lot.copy()
    if ref.empty:
        raise LiveScreenError("Reference lot is empty.")
    needed = [f"{param}_{t}h" for param in PARAMS for t in MEASURE_TIMES]
    missing_ref = [c for c in needed if c not in ref.columns]
    if missing_ref:
        raise LiveScreenError("Reference lot is missing " + ", ".join(missing_ref))
    stats = lot_stats(ref, times=MEASURE_TIMES)
    row = {
        "part_id": str(measurements.get("part_id") or "LIVE-PART"),
        "lot_id": str(measurements.get("lot_id") or stats["lot_id"].iloc[0]),
    }
    for col in REQUIRED_MEASURES:
        if measurements.get(col) is None or pd.isna(measurements.get(col)):
            raise LiveScreenError(f"Enter a value for {col}.")
        row[col] = float(measurements[col])
    for param in PARAMS:
        row[f"datasheet_{param}_max"] = PARAM_META[param]["datasheet_max"]
    part = pd.DataFrame([row])
    stats = stats.copy()
    stats["lot_id"] = part["lot_id"].iloc[0]
    attached = attach_lot_relative(part, stats, times=MEASURE_TIMES)
    return apply_models(attached, bundle, iforest_range=iforest_range)

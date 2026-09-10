"""Physics-informed synthetic burn-in lots.

Real ISRO screening data is ITAR/export-controlled. This generator produces
lot-structured time series that reproduce the failure modes the problem
statement cares about:

* Mavericks — far from the lot centroid, still inside the datasheet box.
* Latent drift — normal at 0 h, anomalous slope, often still in-spec at 168 h.
* Runaway — accelerating degradation that static limits only catch late.

Healthy parts follow a slow, nearly linear aging law at 125 °C. Measurement
noise is calibrated to typical parametric-analyzer repeatability.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import DATA_DIR, N_LOTS, PARAM_META, PARTS_PER_LOT, RANDOM_STATE, TIMES_H


def _clip_positive(values: np.ndarray, floor: float) -> np.ndarray:
    return np.maximum(values, floor)


def _series(v0: np.ndarray, lin: np.ndarray, quad: np.ndarray, noise: float, rng: np.random.Generator) -> dict[int, np.ndarray]:
    out: dict[int, np.ndarray] = {}
    for t in TIMES_H:
        mean = v0 * (1.0 + lin * t + quad * (t**2))
        measured = mean + rng.normal(0.0, noise, size=v0.shape)
        out[t] = _clip_positive(measured, 0.02)
    return out


def generate_burnin_dataset(
    n_lots: int = N_LOTS,
    parts_per_lot: tuple[int, int] = PARTS_PER_LOT,
    seed: int = RANDOM_STATE,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict] = []

    dirty_lots = set(rng.choice(np.arange(n_lots), size=max(2, n_lots // 8), replace=False))

    for lot_i in range(n_lots):
        n = int(rng.integers(parts_per_lot[0], parts_per_lot[1] + 1))
        corner = str(rng.choice(["slow", "nominal", "fast"]))
        dirty = lot_i in dirty_lots

        # Process corner shifts the lot centroid. Fast silicon leaks more and switches sooner.
        if corner == "fast":
            iddq_mean, ileak_mean, tpd_mean = 14.5, 13.2, 3.6
        elif corner == "slow":
            iddq_mean, ileak_mean, tpd_mean = 8.4, 7.4, 6.1
        else:
            iddq_mean, ileak_mean, tpd_mean = 11.0, 10.0, 4.7

        iddq_mean *= float(rng.uniform(0.92, 1.08))
        ileak_mean *= float(rng.uniform(0.92, 1.08))
        tpd_mean *= float(rng.uniform(0.95, 1.05))

        defect_p = 0.18 if dirty else 0.07
        kinds = rng.choice(
            ["healthy", "maverick", "latent_drift", "runaway"],
            size=n,
            p=[1 - defect_p, 0.40 * defect_p, 0.35 * defect_p, 0.25 * defect_p],
        )

        iddq_v0 = rng.normal(iddq_mean, 0.12 * iddq_mean, size=n)
        ileak_v0 = rng.normal(ileak_mean, 0.14 * ileak_mean, size=n)
        tpd_v0 = rng.normal(tpd_mean, 0.07 * tpd_mean, size=n)

        iddq_lin = rng.normal(0.00028, 0.00007, size=n)
        ileak_lin = rng.normal(0.00032, 0.00008, size=n)
        tpd_lin = rng.normal(0.00012, 0.00003, size=n)
        iddq_quad = rng.normal(0.0, 4e-8, size=n)
        ileak_quad = rng.normal(0.0, 5e-8, size=n)
        tpd_quad = rng.normal(0.0, 1.5e-8, size=n)

        for i, kind in enumerate(kinds):
            if kind == "maverick":
                # Offset 4–7 robust-σ equivalent, still below datasheet at t=0.
                iddq_v0[i] = min(PARAM_META["iddq"]["datasheet_max"] * 0.88, iddq_mean * rng.uniform(2.6, 4.2))
                ileak_v0[i] = min(PARAM_META["ileak"]["datasheet_max"] * 0.92, ileak_mean * rng.uniform(3.2, 4.6))
                if rng.random() < 0.5:
                    tpd_v0[i] = min(PARAM_META["tpd"]["datasheet_max"] * 0.85, tpd_mean * rng.uniform(1.45, 1.85))
            elif kind == "latent_drift":
                iddq_lin[i] = rng.uniform(0.0018, 0.0036)
                ileak_lin[i] = rng.uniform(0.0020, 0.0040)
                tpd_lin[i] = rng.uniform(0.0007, 0.0014)
            elif kind == "runaway":
                iddq_lin[i] = rng.uniform(0.0012, 0.0024)
                ileak_lin[i] = rng.uniform(0.0014, 0.0028)
                tpd_lin[i] = rng.uniform(0.0005, 0.0011)
                iddq_quad[i] = rng.uniform(1.2e-5, 2.4e-5)
                ileak_quad[i] = rng.uniform(8e-6, 1.8e-5)
                tpd_quad[i] = rng.uniform(2.5e-6, 6e-6)

        iddq = _series(iddq_v0, iddq_lin, iddq_quad, 0.16, rng)
        ileak = _series(ileak_v0, ileak_lin, ileak_quad, 0.09, rng)
        tpd = _series(tpd_v0, tpd_lin, tpd_quad, 0.025, rng)

        lot_id = f"LOT{lot_i + 1:02d}"
        for i in range(n):
            row: dict = {
                "part_id": f"{lot_id}-{i + 1:04d}",
                "lot_id": lot_id,
                "process_corner": corner,
                "lot_quality": "dirty" if dirty else "clean",
                "defect_type": kinds[i],
                "is_defective": kinds[i] != "healthy",
                "sih_example": False,
                "datasheet_iddq_max": PARAM_META["iddq"]["datasheet_max"],
                "datasheet_ileak_max": PARAM_META["ileak"]["datasheet_max"],
                "datasheet_tpd_max": PARAM_META["tpd"]["datasheet_max"],
            }
            for t in TIMES_H:
                row[f"iddq_{t}h"] = float(iddq[t][i])
                row[f"ileak_{t}h"] = float(ileak[t][i])
                row[f"tpd_{t}h"] = float(tpd[t][i])

            static_fail = False
            for t in TIMES_H:
                if row[f"iddq_{t}h"] > PARAM_META["iddq"]["datasheet_max"]:
                    static_fail = True
                if row[f"ileak_{t}h"] > PARAM_META["ileak"]["datasheet_max"]:
                    static_fail = True
                if row[f"tpd_{t}h"] > PARAM_META["tpd"]["datasheet_max"]:
                    static_fail = True
            row["static_fail"] = static_fail
            rows.append(row)

    df = pd.DataFrame(rows)
    df = pd.concat([df, textbook_maverick_lot(seed=seed + 17)], ignore_index=True)
    df["latent_escape"] = df["is_defective"] & ~df["static_fail"]
    return df


def textbook_maverick_lot(seed: int = 17) -> pd.DataFrame:
    """The problem-statement lot: mean leakage 10 µA, one part at 45 µA, datasheet 50 µA."""
    rng = np.random.default_rng(seed)
    n = 200
    iddq_mean, ileak_mean, tpd_mean = 11.0, 10.0, 4.7
    kinds = np.array(["healthy"] * n, dtype=object)
    kinds[44] = "maverick"

    iddq_v0 = rng.normal(iddq_mean, 0.12 * iddq_mean, size=n)
    ileak_v0 = rng.normal(ileak_mean, 0.12 * ileak_mean, size=n)
    tpd_v0 = rng.normal(tpd_mean, 0.07 * tpd_mean, size=n)
    iddq_lin = rng.normal(0.00028, 0.00007, size=n)
    ileak_lin = rng.normal(0.00032, 0.00008, size=n)
    tpd_lin = rng.normal(0.00012, 0.00003, size=n)
    zeros = np.zeros(n)

    ileak_v0[44] = 45.0
    ileak_lin[44] = 0.00030

    iddq = _series(iddq_v0, iddq_lin, zeros, 0.16, rng)
    ileak = _series(ileak_v0, ileak_lin, zeros, 0.09, rng)
    tpd = _series(tpd_v0, tpd_lin, zeros, 0.025, rng)
    ileak[0][44] = 45.00
    ileak[24][44] = 45.32
    ileak[96][44] = 45.90
    ileak[168][44] = 46.55

    rows: list[dict] = []
    for i in range(n):
        row: dict = {
            "part_id": f"LOTSIH-{i + 1:04d}",
            "lot_id": "LOTSIH",
            "process_corner": "nominal",
            "lot_quality": "clean",
            "defect_type": kinds[i],
            "is_defective": kinds[i] != "healthy",
            "sih_example": i == 44,
            "datasheet_iddq_max": PARAM_META["iddq"]["datasheet_max"],
            "datasheet_ileak_max": PARAM_META["ileak"]["datasheet_max"],
            "datasheet_tpd_max": PARAM_META["tpd"]["datasheet_max"],
        }
        for t in TIMES_H:
            row[f"iddq_{t}h"] = float(iddq[t][i])
            row[f"ileak_{t}h"] = float(ileak[t][i])
            row[f"tpd_{t}h"] = float(tpd[t][i])
        row["static_fail"] = (
            row["iddq_168h"] > PARAM_META["iddq"]["datasheet_max"]
            or row["ileak_168h"] > PARAM_META["ileak"]["datasheet_max"]
            or row["tpd_168h"] > PARAM_META["tpd"]["datasheet_max"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


def save_dataset(path: Path | None = None, **kwargs) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = path or (DATA_DIR / "burnin_parts.csv")
    df = generate_burnin_dataset(**kwargs)
    df.to_csv(path, index=False)
    return path


if __name__ == "__main__":
    out = save_dataset()
    df = pd.read_csv(out)
    print(f"Wrote {out} ({len(df)} parts, {df['lot_id'].nunique()} lots)")
    print(df["defect_type"].value_counts().to_string())
    print(f"Latent escapes (defective + static-pass): {int(df['latent_escape'].sum())}")

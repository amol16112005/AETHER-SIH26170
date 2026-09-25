"""Print-ready figures that match the AETHER Streamlit workstation charts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import PARAM_META, PARAMS, TIMES_H
from src.explain import explain_part
from src.pipeline import load_bundle

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#1B365D"
GOLD = "#C45C26"
MUTED = "#5B6B7C"
PASS_C = "#2ecc71"
HOLD_C = "#d4a017"
REJ_C = "#e74c3c"
DECISION_COLOR = {"PASS": PASS_C, "HOLD": HOLD_C, "REJECT": REJ_C}

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlecolor": NAVY,
        "axes.labelcolor": NAVY,
        "axes.edgecolor": "#C5D0DC",
        "axes.facecolor": "#F7F9FC",
        "figure.facecolor": "white",
        "xtick.color": NAVY,
        "ytick.color": NAVY,
        "grid.color": "#E3EAF2",
        "grid.linewidth": 0.8,
        "axes.grid": True,
        "legend.frameon": False,
    }
)


def _save(fig: plt.Figure, name: str, dpi: int = 180) -> dict:
    path = OUT / name
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    with Image.open(path) as im:
        w, h = im.size
    return {"file": name, "width": w, "height": h, "path": str(path)}


def fig_pipeline() -> dict:
    fig, ax = plt.subplots(figsize=(11.2, 4.6))
    ax.set_xlim(0, 11.2)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    boxes = [
        (0.25, 1.5, 2.15, 1.8, "ATE lot\n0 h + 24 h", "#EEF3F8"),
        (2.85, 2.55, 2.35, 1.55, "Module A\nPAT + iForest\n+ Mahalanobis", "#D9E8F6"),
        (2.85, 0.5, 2.35, 1.55, "Module B\nRidge + HGB\n168 h forecast", "#F8E4D4"),
        (5.7, 1.5, 2.4, 1.8, "Fusion\nPASS / HOLD\n/ REJECT", "#E8F6EC"),
        (8.55, 1.5, 2.35, 1.8, "Inspector\nbrief + charts", "#F4ECF8"),
    ]
    for x, y, w, h, text, fill in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                linewidth=1.4, edgecolor=NAVY, facecolor=fill,
            )
        )
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=10, color=NAVY, fontweight="bold")

    arrows = [
        ((2.4, 2.4), (2.85, 3.3)),
        ((2.4, 2.4), (2.85, 1.3)),
        ((5.2, 3.3), (5.7, 2.55)),
        ((5.2, 1.3), (5.7, 2.25)),
        ((8.1, 2.4), (8.55, 2.4)),
    ]
    for (x1, y1), (x2, y2) in arrows:
        ax.add_patch(
            FancyArrowPatch(
                (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
                linewidth=1.5, color=NAVY, shrinkA=0, shrinkB=2,
            )
        )
    ax.set_title("AETHER screening pipeline (as implemented on the desktop)", loc="left", pad=8)
    return _save(fig, "pipeline.png")


def fig_decision_donut(view: pd.DataFrame) -> dict:
    counts = view["decision"].value_counts()
    order = [d for d in ("PASS", "HOLD", "REJECT") if d in counts.index]
    values = [int(counts[d]) for d in order]
    colors = [DECISION_COLOR[d] for d in order]
    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    wedges, texts, autotexts = ax.pie(
        values,
        labels=order,
        colors=colors,
        autopct=lambda p: f"{p:.1f}%",
        startangle=90,
        pctdistance=0.75,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
    )
    for t in texts:
        t.set_color(NAVY)
        t.set_fontweight("bold")
    for t in autotexts:
        t.set_color(NAVY)
        t.set_fontsize(9)
    ax.text(0, 0, "24 h\ngate", ha="center", va="center", color=NAVY, fontsize=12, fontweight="bold")
    ax.set_title("Lot board — decision mix (held-out lots)")
    return _save(fig, "decision_donut.png")


def fig_lot_scatter(view: pd.DataFrame, param: str) -> dict:
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    for decision in ("PASS", "HOLD", "REJECT"):
        sub = view[view["decision"] == decision]
        ax.scatter(
            sub[f"{param}_0h"],
            sub[f"{param}_24h"],
            c=DECISION_COLOR[decision],
            s=22,
            alpha=0.78,
            label=decision,
            edgecolors="none",
        )
    unit = PARAM_META[param]["unit"]
    label = PARAM_META[param]["label"]
    ax.set_xlabel(f"{label} @ 0 h ({unit})")
    ax.set_ylabel(f"{label} @ 24 h ({unit})")
    ax.legend(loc="upper left", ncol=3)
    ax.set_title("Lot board — 0 h vs 24 h scatter, coloured by decision")
    fig.tight_layout()
    return _save(fig, "lot_scatter.png")


def fig_series(row: pd.Series, param: str) -> dict:
    meta = PARAM_META[param]
    measured_t = list(TIMES_H)
    measured_v = [float(row[f"{param}_{t}h"]) for t in TIMES_H]
    pred = float(row[f"pred_{param}_168h"])
    extrap = float(row[f"extrap_{param}_168h"])
    safety_168 = float(row[f"{param}_0h"]) + float(row[f"{param}_safety_slope"]) * 168.0

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(measured_t, measured_v, "o-", color=meta["color"], lw=2.4, ms=7, label="Measured")
    ax.plot([0, 168], [float(row[f"{param}_0h"]), pred], "--o", color="#8E24AA", lw=1.8, label="Model 168 h")
    ax.plot([0, 168], [float(row[f"{param}_0h"]), extrap], ":", color="#607D8B", lw=1.8, label="Linear extrap")
    ax.axhline(meta["datasheet_max"], color=REJ_C, ls="--", lw=1.2, label="Datasheet max")
    ax.axhline(safety_168, color=HOLD_C, ls=":", lw=1.4, label="Safety envelope @ 168 h")
    ax.set_xlabel("Burn-in time (h)")
    ax.set_ylabel(meta["unit"])
    ax.set_title(f"QA inspector — {meta['label']} time series")
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    return _save(fig, f"series_{param}.png")


def fig_waterfall(pcard: dict) -> dict:
    items = pcard["ridge_all"]
    labels = ["intercept"] + [it["feature"] for it in items] + ["predicted 168 h"]
    values = [pcard["ridge_intercept"]] + [it["contribution"] for it in items] + [pcard["ridge_prediction"]]
    measures = ["absolute"] + ["relative"] * len(items) + ["total"]

    running = 0.0
    lefts, heights, colors, y_texts = [], [], [], []
    for val, meas in zip(values, measures):
        if meas == "absolute":
            running = val
            lefts.append(0.0)
            heights.append(val)
            colors.append("#5C6BC0")
            y_texts.append(val)
        elif meas == "total":
            lefts.append(0.0)
            heights.append(val)
            colors.append("#8E24AA")
            y_texts.append(val)
            running = val
        else:
            base = running
            running = running + val
            if val >= 0:
                lefts.append(base)
                heights.append(val)
                colors.append(REJ_C)
            else:
                lefts.append(running)
                heights.append(-val)
                colors.append("#039BE5")
            y_texts.append(running)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(range(len(labels)), heights, bottom=lefts, color=colors, width=0.72, edgecolor="white")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel(pcard["unit"])
    ax.set_title(f"QA inspector — Ridge waterfall, {pcard['label']}")
    fig.tight_layout()
    return _save(fig, f"waterfall_{pcard['param']}.png")


def fig_pat_hist(df: pd.DataFrame) -> dict:
    lot = df[df["lot_id"] == "LOTSIH"]
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    ax.hist(lot["ileak_24h"], bins=28, color="#90CAF9", edgecolor="white", label="LOTSIH @ 24 h")
    example = lot.loc[lot["sih_example"].astype(bool)].iloc[0]
    ax.axvline(float(example["ileak_24h"]), color=REJ_C, lw=2.2, label=f"LOTSIH-0045 = {example['ileak_24h']:.2f} µA")
    ax.axvline(float(example["ileak_24h_median"]), color=NAVY, lw=2.0, ls="--",
               label=f"Lot median = {example['ileak_24h_median']:.2f} µA")
    ax.axvline(50.0, color=GOLD, lw=2.0, ls=":", label="Datasheet max = 50 µA")
    ax.set_xlabel("Leakage current @ 24 h (µA)")
    ax.set_ylabel("Parts in lot")
    ax.set_title("Why a static screen misses the SIH textbook maverick")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, "pat_histogram.png")


def fig_aging() -> dict:
    t = np.linspace(0, 168, 80)
    v0 = 10.0
    healthy = v0 * (1 + 0.00032 * t)
    latent = v0 * (1 + 0.0030 * t)
    runaway = v0 * (1 + 0.0018 * t + 1.2e-5 * t ** 2)
    maverick = np.full_like(t, 45.0) * (1 + 0.00030 * t) / (1 + 0.00030 * 0)

    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    ax.plot(t, healthy, color=PASS_C, lw=2.4, label="Healthy (slow linear aging)")
    ax.plot(t, latent, color=HOLD_C, lw=2.4, label="Latent drift (steep linear)")
    ax.plot(t, runaway, color=REJ_C, lw=2.4, label="Runaway (quadratic)")
    ax.plot(t, maverick, color="#8E24AA", lw=2.4, label="Maverick (offset, in-spec)")
    ax.axhline(50, color=GOLD, ls="--", lw=1.3, label="Datasheet 50 µA")
    ax.set_xlabel("Burn-in time (h)")
    ax.set_ylabel("Leakage (µA)")
    ax.set_title("Generative aging modes used to train and test the models")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, "aging_modes.png")


def main() -> None:
    screened = pd.read_csv(ROOT / "data" / "screening_results.csv")
    report = json.loads((ROOT / "models" / "metrics.json").read_text(encoding="utf-8"))
    bundle = load_bundle()
    test = screened[screened["split"] == "test"].copy()
    demo = screened.loc[screened["sih_example"].astype(bool)].iloc[0]
    card = explain_part(demo, bundle.drift)

    meta = {
        "pipeline": fig_pipeline(),
        "decision_donut": fig_decision_donut(test),
        "lot_scatter": fig_lot_scatter(test, "ileak"),
        "pat_histogram": fig_pat_hist(screened),
        "aging_modes": fig_aging(),
        "report": report,
        "test_counts": test["decision"].value_counts().to_dict(),
        "demo": {
            "part_id": str(demo["part_id"]),
            "lot_id": str(demo["lot_id"]),
            "decision": card["decision"],
            "fused_score": card["fused_score"],
            "outlier_score": card["outlier_score"],
            "iforest_score": card["iforest_score"],
            "mahalanobis_score": card["mahalanobis_score"],
            "hours_saved": card["hours_saved"],
            "headline": card["headline"],
            "inspector_brief": card["inspector_brief"],
            "bullets": card["bullets"],
            "static_vs_dynamic": card["static_vs_dynamic"],
            "ileak_0h": float(demo["ileak_0h"]),
            "ileak_24h": float(demo["ileak_24h"]),
            "ileak_96h": float(demo["ileak_96h"]),
            "ileak_168h": float(demo["ileak_168h"]),
            "ileak_24h_z": float(demo["ileak_24h_z"]),
            "ileak_24h_median": float(demo["ileak_24h_median"]),
            "pred_ileak_168h": float(demo["pred_ileak_168h"]),
        },
        "series": {},
        "waterfall": {},
    }
    for param in PARAMS:
        meta["series"][param] = fig_series(demo, param)
    for pcard in card["param_cards"]:
        meta["waterfall"][pcard["param"]] = fig_waterfall(pcard)
        meta["waterfall"][pcard["param"]]["caption"] = (
            f"0 h {pcard['v0']:.3f} {pcard['unit']} (z={pcard['z0']:.2f}) → "
            f"24 h {pcard['v24']:.3f} (z={pcard['z24']:.2f}) → "
            f"pred 168 h {pcard['pred_168']:.3f}"
            + (f" (actual {pcard['actual_168']:.3f})" if pcard["actual_168"] is not None else "")
        )
        meta["waterfall"][pcard["param"]]["ridge_top"] = pcard["ridge_top"]
        meta["waterfall"][pcard["param"]]["ridge_intercept"] = pcard["ridge_intercept"]
        meta["waterfall"][pcard["param"]]["ridge_prediction"] = pcard["ridge_prediction"]

    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    print(f"Wrote figures to {OUT}")
    print(json.dumps({k: v.get("file") if isinstance(v, dict) else "…" for k, v in meta.items()}, indent=2))


if __name__ == "__main__":
    main()

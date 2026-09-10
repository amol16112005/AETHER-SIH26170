"""QA workstation for ISRO-style burn-in screening (SIH26170)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_DIR, MODELS_DIR, PARAM_META, PARAMS, TIMES_H
from src.explain import explain_part
from src.generate_data import save_dataset
from src.pipeline import apply_models, load_bundle, save_bundle, train_bundle

st.set_page_config(page_title="AETHER · Burn-In Screening", page_icon="🛰", layout="wide")

DECISION_COLOR = {"PASS": "#2ecc71", "HOLD": "#f1c40f", "REJECT": "#e74c3c"}


def _ensure_artifacts() -> tuple[pd.DataFrame, object, dict]:
    csv_path = DATA_DIR / "burnin_parts.csv"
    bundle_path = MODELS_DIR / "screening_bundle.joblib"
    metrics_path = MODELS_DIR / "metrics.json"
    results_path = DATA_DIR / "screening_results.csv"

    if not csv_path.exists():
        save_dataset(csv_path)
    df = pd.read_csv(csv_path)

    if not bundle_path.exists() or not results_path.exists():
        with st.spinner("Training lot-aware screening models (first run)…"):
            bundle, report, train_out, val_out, test_out = train_bundle(df)
            save_bundle(bundle)
            screened = pd.concat(
                [
                    train_out.assign(split="train"),
                    val_out.assign(split="val"),
                    test_out.assign(split="test"),
                ],
                ignore_index=True,
            )
            screened["pat_reasons"] = screened["pat_reasons"].apply(
                lambda xs: " | ".join(xs) if isinstance(xs, list) else xs
            )
            screened.to_csv(results_path, index=False)
            metrics_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        bundle = load_bundle(bundle_path)
        report = json.loads(metrics_path.read_text(encoding="utf-8"))
        screened = pd.read_csv(results_path)
    return screened, bundle, report


def _kpi(label: str, value: str, help_text: str) -> None:
    st.metric(label, value, help=help_text)


def _waterfall(pcard: dict) -> go.Figure:
    items = pcard["ridge_all"]
    measures = ["absolute"] + ["relative"] * len(items) + ["total"]
    x = ["intercept"] + [item["feature"] for item in items] + ["predicted 168 h"]
    y = [pcard["ridge_intercept"]] + [item["contribution"] for item in items] + [pcard["ridge_prediction"]]
    fig = go.Figure(
        go.Waterfall(
            x=x,
            y=y,
            measure=measures,
            connector={"line": {"color": "rgba(255,255,255,0.2)"}},
            increasing={"marker": {"color": "#E74C3C"}},
            decreasing={"marker": {"color": "#4FC3F7"}},
            totals={"marker": {"color": "#E040FB"}},
        )
    )
    fig.update_layout(
        title=f"{pcard['label']}  ({pcard['unit']})",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(21,27,46,0.6)",
        font_color="#E8EEF9",
        margin=dict(t=50, b=80, l=40, r=20),
        height=320,
        showlegend=False,
    )
    fig.update_xaxes(tickangle=-35, gridcolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)")
    return fig


def _decision_pie(df: pd.DataFrame) -> go.Figure:
    counts = df["decision"].value_counts()
    fig = go.Figure(
        go.Pie(
            labels=counts.index.tolist(),
            values=counts.values.tolist(),
            hole=0.62,
            marker={"colors": [DECISION_COLOR.get(k, "#888") for k in counts.index]},
            textinfo="label+percent",
        )
    )
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E8EEF9",
        showlegend=False,
        annotations=[dict(text="24 h", x=0.5, y=0.5, font_size=16, showarrow=False)],
    )
    return fig


def _lot_scatter(df: pd.DataFrame, param: str) -> go.Figure:
    fig = go.Figure()
    for decision, color in DECISION_COLOR.items():
        sub = df[df["decision"] == decision]
        fig.add_trace(
            go.Scatter(
                x=sub[f"{param}_0h"],
                y=sub[f"{param}_24h"],
                mode="markers",
                name=decision,
                marker=dict(color=color, size=8, opacity=0.75),
                text=sub["part_id"],
                hovertemplate="%{text}<br>0 h: %{x:.3f}<br>24 h: %{y:.3f}<extra>" + decision + "</extra>",
            )
        )
    unit = PARAM_META[param]["unit"]
    fig.update_layout(
        xaxis_title=f"{PARAM_META[param]['label']} @ 0 h ({unit})",
        yaxis_title=f"{PARAM_META[param]['label']} @ 24 h ({unit})",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(21,27,46,0.6)",
        font_color="#E8EEF9",
        margin=dict(t=30, b=40, l=50, r=20),
        legend=dict(orientation="h", y=1.08),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)")
    return fig


def _series_figure(row: pd.Series, param: str) -> go.Figure:
    meta = PARAM_META[param]
    measured_t = list(TIMES_H)
    measured_v = [float(row[f"{param}_{t}h"]) for t in TIMES_H]
    pred = float(row[f"pred_{param}_168h"])
    extrap = float(row[f"extrap_{param}_168h"])
    safety_168 = float(row[f"{param}_0h"]) + float(row[f"{param}_safety_slope"]) * 168.0

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=measured_t, y=measured_v, mode="lines+markers", name="Measured", line=dict(color=meta["color"], width=3)))
    fig.add_trace(go.Scatter(x=[0, 168], y=[float(row[f"{param}_0h"]), pred], mode="lines+markers", name="Model 168 h", line=dict(color="#E040FB", dash="dash")))
    fig.add_trace(go.Scatter(x=[0, 168], y=[float(row[f"{param}_0h"]), extrap], mode="lines", name="Linear extrap", line=dict(color="#90A4AE", dash="dot")))
    fig.add_hline(y=meta["datasheet_max"], line_color="#e74c3c", line_dash="dash", annotation_text="Datasheet max", annotation_position="top left")
    fig.add_hline(y=safety_168, line_color="#f1c40f", line_dash="dot", annotation_text="Safety envelope @ 168 h")
    fig.update_layout(
        title=meta["label"],
        xaxis_title="Burn-in time (h)",
        yaxis_title=meta["unit"],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(21,27,46,0.6)",
        font_color="#E8EEF9",
        margin=dict(t=50, b=40, l=50, r=20),
        legend=dict(orientation="h", y=1.15),
        height=320,
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)")
    return fig


def _style_header() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; }
        .aether-hero {
            background: linear-gradient(90deg, #151B2E 0%, #1b2744 55%, #12324a 100%);
            border: 1px solid rgba(79,195,247,0.25);
            border-radius: 16px;
            padding: 1.1rem 1.4rem 0.9rem 1.4rem;
            margin-bottom: 1rem;
        }
        .aether-kicker { color: #4FC3F7; letter-spacing: 0.18em; font-size: 0.72rem; font-weight: 700; }
        .aether-title { font-size: 1.7rem; font-weight: 700; margin: 0.15rem 0 0.2rem 0; }
        .aether-sub { color: #9BB0C9; margin: 0; }
        .decision-PASS { color: #2ecc71; font-weight: 800; }
        .decision-HOLD { color: #f1c40f; font-weight: 800; }
        .decision-REJECT { color: #e74c3c; font-weight: 800; }
        </style>
        <div class="aether-hero">
          <div class="aether-kicker">SIH26170 · ISRO / DEPARTMENT OF SPACE</div>
          <div class="aether-title">AETHER — Adaptive ESS Thermal Health &amp; Early Reject</div>
          <p class="aether-sub">Lot-aware PAT outlier detection + 24 h → 168 h drift prediction, with inspector-grade explanations.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _style_header()
    screened, bundle, report = _ensure_artifacts()

    lots = ["All lots"] + sorted(screened["lot_id"].unique().tolist())
    splits = ["All splits", "train", "val", "test"]
    left, mid, right = st.columns([1.3, 1, 1])
    with left:
        lot_sel = st.selectbox("Lot", lots)
    with mid:
        split_sel = st.selectbox("Split", splits, index=3 if "test" in screened["split"].values else 0)
    with right:
        param_sel = st.selectbox("Parameter", list(PARAMS), index=1, format_func=lambda p: PARAM_META[p]["label"])

    view = screened.copy()
    if lot_sel != "All lots":
        view = view[view["lot_id"] == lot_sel]
    if split_sel != "All splits":
        view = view[view["split"] == split_sel]

    test_m = report["test"]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        _kpi("Held-out recall", f"{test_m['recall']:.1%}", "False negatives are catastrophic; this is the primary score.")
    with c2:
        _kpi("False negatives", f"{test_m['fn']} / {test_m['defectives']}", "Defective parts that received PASS.")
    with c3:
        _kpi("Latent catch rate", f"{test_m['latent_catch_rate']:.1%}", "Defectives that still pass datasheet limits.")
    with c4:
        _kpi("Reject precision", f"{test_m['reject_precision']:.1%}", "Of 24 h REJECT calls, how many were truly defective.")
    with c5:
        _kpi("IDDQ 168 h MAE", f"{report['drift_test']['iddq_mae']:.2f} µA", "Module B prediction vs hidden ground truth.")
    with c6:
        _kpi("Chamber hours saved", f"{test_m['hours_saved_total']:,}", "Only from 24 h REJECT — healthy flight parts still finish burn-in.")

    tab_dash, tab_inspect, tab_rubric, tab_method = st.tabs(
        ["Lot board", "QA inspector", "Judging rubric", "Methodology"]
    )

    with tab_dash:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.plotly_chart(_decision_pie(view), use_container_width=True)
            st.caption("PASS = no anomaly, finish 168 h · HOLD = extra 96 h readout · REJECT = pull from the chamber now.")
        with col_b:
            st.plotly_chart(_lot_scatter(view, param_sel), use_container_width=True)

        show_cols = [
            "part_id",
            "lot_id",
            "split",
            "decision",
            "fused_score",
            "outlier_score",
            f"{param_sel}_0h",
            f"{param_sel}_24h",
            f"pred_{param_sel}_168h",
            f"{param_sel}_168h",
            "defect_type",
            "latent_escape",
            "hours_saved",
        ]
        st.dataframe(
            view[show_cols].sort_values("fused_score", ascending=False),
            use_container_width=True,
            hide_index=True,
            height=360,
        )

    with tab_inspect:
        focus_pool = view.sort_values("fused_score", ascending=False)
        if focus_pool.empty:
            st.warning("No parts in this filter.")
            return
        default_idx = 0
        ids = focus_pool["part_id"].tolist()
        if "sih_example" in focus_pool.columns and focus_pool["sih_example"].astype(bool).any():
            example_id = focus_pool.loc[focus_pool["sih_example"].astype(bool), "part_id"].iloc[0]
            default_idx = ids.index(example_id)
        else:
            latent_hits = focus_pool.index[focus_pool["latent_escape"].astype(bool)]
            if len(latent_hits):
                loc = focus_pool.index.get_loc(latent_hits[0])
                default_idx = int(loc) if isinstance(loc, int) else int(list(loc)[0])

        part_id = st.selectbox("Component", focus_pool["part_id"].tolist(), index=min(default_idx, len(focus_pool) - 1))
        row = focus_pool.loc[focus_pool["part_id"] == part_id].iloc[0]
        card = explain_part(row, bundle.drift)

        dcol, scol, hcol = st.columns(3)
        dcol.markdown(f"### Decision: <span class='decision-{card['decision']}'>{card['decision']}</span>", unsafe_allow_html=True)
        scol.metric("Fused score", f"{card['fused_score']:.2f}")
        hcol.metric("Chamber hours saved", card["hours_saved"])
        st.info(card["headline"])

        contrast = card["static_vs_dynamic"]
        left_s, right_s = st.columns(2)
        left_s.markdown(
            f"**Static datasheet screen:** <span class='decision-{'PASS' if contrast['static']=='PASS' else 'REJECT'}'>{contrast['static']}</span>",
            unsafe_allow_html=True,
        )
        right_s.markdown(
            f"**Dynamic lot-relative screen:** <span class='decision-{contrast['dynamic']}'>{contrast['dynamic']}</span>",
            unsafe_allow_html=True,
        )
        if contrast["is_textbook"]:
            st.success(
                "Pinned SIH26170 example: lot leakage ≈ 10 µA, this part is 45 µA, datasheet max is 50 µA. "
                "Static PASS, dynamic REJECT."
            )
        for line in contrast["lines"]:
            st.markdown(f"- {line}")

        st.markdown("#### Why this call")
        for bullet in card["bullets"]:
            st.markdown(f"- {bullet}")

        st.markdown("#### Time series vs predicted 168 h")
        g1, g2, g3 = st.columns(3)
        for col, param in zip((g1, g2, g3), PARAMS):
            with col:
                st.plotly_chart(_series_figure(row, param), use_container_width=True)

        st.markdown("#### Why the 168 h forecast looks like this (Ridge waterfall — not a black box)")
        pcols = st.columns(3)
        for col, pcard in zip(pcols, card["param_cards"]):
            with col:
                st.caption(
                    f"0 h {pcard['v0']:.3f} {pcard['unit']} (z={pcard['z0']:.2f}) → "
                    f"24 h {pcard['v24']:.3f} (z={pcard['z24']:.2f}) → "
                    f"pred 168 h {pcard['pred_168']:.3f}"
                    + (f"  (actual {pcard['actual_168']:.3f})" if pcard["actual_168"] is not None else "")
                )
                st.plotly_chart(_waterfall(pcard), use_container_width=True)

        st.markdown("#### Inspector brief (copy into the lot traveller)")
        st.code(card["inspector_brief"], language=None)

        st.markdown("#### What-if: 24 h reading")
        wcol, _ = st.columns([1.2, 1.8])
        with wcol:
            tweaked = float(st.slider(
                f"{PARAM_META[param_sel]['label']} @ 24 h",
                min_value=float(row[f"{param_sel}_24h"]) * 0.4,
                max_value=float(PARAM_META[param_sel]["datasheet_max"]),
                value=float(row[f"{param_sel}_24h"]),
            ))
        if abs(tweaked - float(row[f"{param_sel}_24h"])) > 1e-9:
            probe = row.copy()
            probe[f"{param_sel}_24h"] = tweaked
            # Recompute slope/z quickly against existing lot stats.
            probe[f"{param_sel}_slope24"] = (tweaked - float(probe[f"{param_sel}_0h"])) / 24.0
            probe[f"{param_sel}_rel24"] = (tweaked - float(probe[f"{param_sel}_0h"])) / max(float(probe[f"{param_sel}_0h"]), 0.05)
            probe[f"{param_sel}_24h_z"] = (tweaked - float(probe[f"{param_sel}_24h_median"])) / float(probe[f"{param_sel}_24h_sigma"])
            probe[f"{param_sel}_slope24_z"] = (
                float(probe[f"{param_sel}_slope24"]) - float(probe[f"{param_sel}_slope24_median"])
            ) / float(probe[f"{param_sel}_slope24_sigma"])
            one = pd.DataFrame([probe])
            # Isolation Forest needs the original feature set; reuse apply_models on a 1-row frame
            # after reconstructing a minimal enrich. The row already has lot columns.
            replay = apply_models(one, bundle).iloc[0]
            st.warning(
                f"If 24 h {param_sel} were {tweaked:.3f} {PARAM_META[param_sel]['unit']}, "
                f"decision would be **{replay['decision']}** (score {replay['fused_score']:.2f})."
            )

    with tab_rubric:
        st.markdown("### SIH26170 evaluation metrics (held-out lots)")
        st.markdown(
            "These are the three scores the problem statement names. "
            "Numbers below are computed on lots the model never trained on."
        )
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown("#### 1. Anomaly detection")
            st.metric("Recall (catch rate)", f"{test_m['recall']:.1%}")
            st.metric("False negatives", f"{test_m['fn']} / {test_m['defectives']}")
            st.caption(
                f"A false negative is catastrophic. Static 24 h datasheet limits would miss "
                f"**{test_m['static_24h_missed_defectives']}** of these defectives. "
                f"AETHER misses **{test_m['fn']}**."
            )
        with r2:
            st.markdown("#### 2. Drift prediction accuracy")
            d = report["drift_test"]
            st.metric("IDDQ MAE @ 168 h", f"{d['iddq_mae']:.3f} µA")
            st.metric("Leakage MAE @ 168 h", f"{d['ileak_mae']:.3f} µA")
            st.metric("tpd MAE @ 168 h", f"{d['tpd_mae']:.3f} ns")
            st.caption(
                f"Hidden ground truth. Linear extrapolation MAE is "
                f"{d['iddq_extrap_mae']:.2f} / {d['ileak_extrap_mae']:.2f} / {d['tpd_extrap_mae']:.2f}."
            )
        with r3:
            st.markdown("#### 3. Explainability")
            st.markdown(
                """
                Every call is justified in inspector English:

                * robust z vs **this lot's** median (Module A)
                * predicted 168 h slope vs healthy safety slope (Module B)
                * Ridge waterfall — which 0 h / 24 h feature moved the forecast
                * static datasheet verdict vs dynamic lot-relative verdict, side by side
                """
            )
            st.caption("Open QA inspector → LOTSIH-0045 for the 10 µA vs 45 µA vs 50 µA worked example.")

        if "sih_example" in screened.columns and screened["sih_example"].astype(bool).any():
            demo = screened.loc[screened["sih_example"].astype(bool)].iloc[0]
            demo_card = explain_part(demo, bundle.drift)
            st.markdown("#### Worked example from the problem statement")
            st.code(demo_card["inspector_brief"], language=None)
            for line in demo_card["static_vs_dynamic"]["lines"]:
                st.markdown(f"- {line}")

    with tab_method:
        st.markdown(
            """
            ### The gap static limits cannot close

            A lot whose leakage centroid sits at 10 µA can still have a 45 µA maverick
            that is *legal* against a 50 µA datasheet. That part is a process outlier.
            In a flight payload it is an infant-mortality risk. Module A is **dynamic
            Part Average Testing** (robust median + MAD, Isolation Forest, Mahalanobis)
            computed **inside the lot**, not against the data book.

            ### Early reject at 24 h

            Module B never waits for 168 h. It takes `Value_0h` and `Value_24h`,
            predicts `Value_168h`, and compares the implied slope to the healthy
            95th-percentile safety slope learned on training lots. A Ridge model
            stays in the loop so a QA inspector can see *which feature* pushed the
            forecast over the line.

            ### Why three decisions, not two

            Space-grade parts are expensive. A binary classifier that scraps too
            aggressively is also a failure. **HOLD** means: this is not a clean pass;
            keep it in the chamber until 96 h rather than releasing it or killing it.

            ### Evaluation bias

            False negatives are costed 80× higher than false positives during
            threshold calibration. Lots are held out entirely during training so PAT
            statistics and the drift model are not leaking the test process corner.

            Held-out lots used for the numbers on this dashboard:
            """
        )
        st.code(", ".join(report["splits"]["test_lots"]), language=None)
        st.json(
            {
                "thresholds": report["thresholds"],
                "test_detection": report["test"],
                "test_drift_mae": report["drift_test"],
                "drift_model_blend": report["drift_models"],
            }
        )


if __name__ == "__main__":
    main()

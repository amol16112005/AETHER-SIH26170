"""QA workstation for ISRO-style burn-in screening (SIH26170).

Includes a live 'Screen my data' tab for user-supplied 0 h / 24 h readings.
"""

from __future__ import annotations

import json
import sys
import textwrap
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
from src.live_screen import (
    NOMINAL_HEALTHY,
    REQUIRED_MEASURES,
    TEXTBOOK_MAVERICK,
    LiveScreenError,
    blank_frame,
    complete_rows,
    for_editor,
    parse_live_upload,
    screen_lot,
    screen_one_part,
    template_csv_bytes,
    template_frame,
)
from src.module_a import iforest_raw_range
from src.pipeline import apply_models, load_bundle, save_bundle, train_bundle

st.set_page_config(page_title="AETHER · Burn-In Screening", page_icon="🛰", layout="wide")

DECISION_COLOR = {"PASS": "#2ecc71", "HOLD": "#f1c40f", "REJECT": "#e74c3c"}


def _wide(**extra) -> dict:
    """Layout kwargs that work on Streamlit 1.38 (Render) and 1.50+."""
    try:
        import inspect
        if "width" in inspect.signature(st.dataframe).parameters:
            return {"width": "stretch", **extra}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True, **extra}


def _chart(fig, **kwargs):
    try:
        return st.plotly_chart(fig, width="stretch", **kwargs)
    except TypeError:
        return st.plotly_chart(fig, use_container_width=True, **kwargs)
_PLOT_STYLE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(21,27,46,0.6)",
    font=dict(color="#E8EEF9", size=16),
)


def _style_chart(fig: go.Figure, **kwargs) -> go.Figure:
    fig.update_layout(**_PLOT_STYLE, **kwargs)
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)")
    return fig


@st.cache_resource(show_spinner="Loading screening models…")
def _ensure_artifacts() -> tuple[pd.DataFrame, object, dict, tuple[float, float]]:
    csv_path = DATA_DIR / "burnin_parts.csv"
    bundle_path = MODELS_DIR / "screening_bundle.joblib"
    metrics_path = MODELS_DIR / "metrics.json"
    results_path = DATA_DIR / "screening_results.csv"

    if bundle_path.exists():
        missing_side = [path.name for path in (metrics_path, results_path) if not path.exists()]
        if missing_side:
            raise RuntimeError(
                "Kept models/screening_bundle.joblib unchanged. Missing "
                + ", ".join(missing_side)
                + ". Retrain only from a historical corpus: python scripts/train.py."
            )
        bundle = load_bundle(bundle_path)
        report = json.loads(metrics_path.read_text(encoding="utf-8"))
        screened = pd.read_csv(results_path)
    else:
        if not csv_path.exists():
            save_dataset(csv_path)
        df = pd.read_csv(csv_path)
        with st.spinner("Training lot-aware screening models (no saved bundle yet)…"):
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
            # Historical corpus only. An existing file is never replaced from the app.
            if not results_path.exists():
                screened.to_csv(results_path, index=False)
            if not metrics_path.exists():
                metrics_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ctx = screened[screened["split"] == "train"] if "split" in screened.columns else screened
    if ctx.empty:
        ctx = screened
    if_range = iforest_raw_range(ctx, bundle.outlier)
    return screened, bundle, report, if_range


def _kpi(label: str, value: str, help_text: str) -> None:
    st.metric(label, value, help=help_text)


def _dedent_md(text: str) -> str:
    """Strip the indent of a triple-quoted block nested inside a function.

    Streamlit's markdown follows CommonMark: four leading spaces make a code
    fence, so an indented string would otherwise show as source instead of
    headings and paragraphs.
    """
    return textwrap.dedent(text).strip()


def _md(text: str) -> None:
    st.markdown(_dedent_md(text))


def _render_method_results(report: dict) -> None:
    """Show the evaluation *results* the methodology produced — not the JSON blob."""
    splits = report["splits"]
    test_m = report["test"]
    drift = report["drift_test"]
    models = report["drift_models"]
    th = report["thresholds"]

    st.markdown("#### Lot hold-out")
    c1, c2, c3 = st.columns(3)
    c1.metric("Train lots", len(splits["train_lots"]))
    c2.metric("Validation lots", len(splits["val_lots"]))
    c3.metric("Held-out test lots", len(splits["test_lots"]))
    st.caption("Test lots (never used for PAT stats or the drift fit): " + ", ".join(splits["test_lots"]))
    st.caption("Train: " + ", ".join(splits["train_lots"]))
    st.caption("Validation: " + ", ".join(splits["val_lots"]))

    st.markdown("#### Calibrated decision thresholds")
    t1, t2 = st.columns(2)
    t1.metric("HOLD threshold", f"≥ {th['hold']:.2f}")
    t2.metric("REJECT threshold", f"≥ {th['reject']:.2f}")
    st.caption("Fused score cutoffs from FN-heavy calibration. Below HOLD is a clean PASS.")

    st.markdown("#### Held-out decisions")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Parts", f"{test_m['n']:,}")
    d2.metric("PASS", f"{test_m['passes']:,}")
    d3.metric("HOLD", f"{test_m['holds']:,}")
    d4.metric("REJECT", f"{test_m['early_rejects']:,}")
    st.caption(
        f"Recall {test_m['recall']:.0%} "
        f"({test_m['fn']} miss / {test_m['defectives']} defectives). "
        f"Static datasheet limits at 24 h would miss {test_m['static_24h_missed_defectives']} of them."
    )

    st.markdown("#### Module B — 168 h forecast vs linear extrapolation")
    rows = []
    for param in PARAMS:
        meta = PARAM_META[param]
        unit = meta["unit"]
        m = models[param]
        w = float(m["blend_weight"])
        rows.append(
            {
                "Parameter": meta["label"],
                "AETHER MAE": f"{drift[f'{param}_mae']:.3f} {unit}",
                "Linear extrap MAE": f"{drift[f'{param}_extrap_mae']:.3f} {unit}",
                "Blend": f"{(1.0 - w):.0%} Ridge + {w:.0%} booster",
                "Healthy 95th slope": f"{m['safety_slope']:.4f} {unit}/h",
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, **_wide())
    st.caption(
        "MAE is against the 168 h reading the model is not allowed to see at 24 h. "
        "The booster is blended in only when it beats Ridge on validation lots. "
        "A predicted slope above 1.5× the healthy 95th-percentile slope is an unsafe-drift flag."
    )


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
    _style_chart(
        fig,
        title=f"{pcard['label']}  ({pcard['unit']})",
        margin=dict(t=50, b=80, l=40, r=20),
        height=320,
        showlegend=False,
    )
    fig.update_xaxes(tickangle=-35)
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
        **_PLOT_STYLE,
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=False,
        annotations=[dict(text="24 h", x=0.5, y=0.5, font_size=20, showarrow=False)],
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
    return _style_chart(
        fig,
        xaxis_title=f"{PARAM_META[param]['label']} @ 0 h ({unit})",
        yaxis_title=f"{PARAM_META[param]['label']} @ 24 h ({unit})",
        margin=dict(t=30, b=40, l=50, r=20),
        legend=dict(orientation="h", y=1.08),
    )


def _forecast_at_hour(df: pd.DataFrame, param: str, hour: float) -> pd.Series:
    """Value of the 0 h → predicted-168 h line at `hour`. Not a separate model."""
    v0 = df[f"{param}_0h"].astype(float)
    pred = df[f"pred_{param}_168h"].astype(float)
    return v0 + (pred - v0) * (hour / 168.0)


def _measured_vs_predicted(df: pd.DataFrame, param: str, hour: int) -> go.Figure | None:
    """Measured later-hour readings against the 0 h + 24 h forecast. None if absent."""
    measured_col = f"{param}_{hour}h"
    pred_col = f"pred_{param}_168h"
    if measured_col not in df.columns or pred_col not in df.columns:
        return None
    predicted = df[pred_col].astype(float) if hour == 168 else _forecast_at_hour(df, param, hour)
    both = df.loc[df[measured_col].notna() & predicted.notna()].copy()
    if both.empty:
        return None
    pred_vals = predicted.loc[both.index]
    meta = PARAM_META[param]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=pred_vals,
            y=both[measured_col].astype(float),
            mode="markers",
            name=f"Measured {hour} h",
            marker=dict(color=meta["color"], size=9),
            text=both["part_id"] if "part_id" in both.columns else None,
            hovertemplate="%{text}<br>forecast %{x:.3f}<br>measured %{y:.3f}<extra></extra>",
        )
    )
    lo = float(min(pred_vals.min(), both[measured_col].min()))
    hi = float(max(pred_vals.max(), both[measured_col].max()))
    pad = (hi - lo) * 0.05 or 0.1
    fig.add_trace(
        go.Scatter(
            x=[lo - pad, hi + pad],
            y=[lo - pad, hi + pad],
            mode="lines",
            name="Measured = forecast",
            line=dict(color="#90A4AE", dash="dot"),
        )
    )
    x_title = (
        f"Predicted {hour} h ({meta['unit']})"
        if hour == 168
        else f"Forecast line at {hour} h ({meta['unit']})"
    )
    return _style_chart(
        fig,
        title=f"{meta['label']}: measured {hour} h vs forecast",
        xaxis_title=x_title,
        yaxis_title=f"Measured {hour} h ({meta['unit']})",
        margin=dict(t=50, b=40, l=50, r=20),
        legend=dict(orientation="h", y=1.12),
        height=360,
    )


def _series_figure(row: pd.Series, param: str) -> go.Figure:
    meta = PARAM_META[param]
    measured_t: list[int] = []
    measured_v: list[float] = []
    for t in TIMES_H:
        col = f"{param}_{t}h"
        if col in row.index and pd.notna(row[col]):
            measured_t.append(t)
            measured_v.append(float(row[col]))
    pred = float(row[f"pred_{param}_168h"])
    extrap = float(row[f"extrap_{param}_168h"])
    safety_168 = float(row[f"{param}_0h"]) + float(row[f"{param}_safety_slope"]) * 168.0

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=measured_t, y=measured_v, mode="lines+markers", name="Measured", line=dict(color=meta["color"], width=3)))
    fig.add_trace(go.Scatter(x=[0, 168], y=[float(row[f"{param}_0h"]), pred], mode="lines+markers", name="Model 168 h", line=dict(color="#E040FB", dash="dash")))
    fig.add_trace(go.Scatter(x=[0, 168], y=[float(row[f"{param}_0h"]), extrap], mode="lines", name="Linear extrap", line=dict(color="#90A4AE", dash="dot")))
    fig.add_hline(y=meta["datasheet_max"], line_color="#e74c3c", line_dash="dash", annotation_text="Datasheet max", annotation_position="top left")
    fig.add_hline(y=safety_168, line_color="#f1c40f", line_dash="dot", annotation_text="Safety envelope @ 168 h")
    return _style_chart(
        fig,
        title=meta["label"],
        xaxis_title="Burn-in time (h)",
        yaxis_title=meta["unit"],
        margin=dict(t=50, b=40, l=50, r=20),
        legend=dict(orientation="h", y=1.15),
        height=320,
    )


def _style_header() -> None:
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"], .stApp { font-size: 18px !important; }
        .block-container { padding-top: 1.2rem; }
        .stMarkdown, .stMarkdown p, .stCaption, label, .stSelectbox, .stRadio {
            font-size: 1.05rem !important;
        }
        [data-testid="stMetricValue"] { font-size: 1.85rem !important; }
        [data-testid="stMetricLabel"] { font-size: 1.05rem !important; }
        [data-testid="stMetricDelta"] { font-size: 0.95rem !important; }
        button, [data-baseweb="tab"], [data-testid="stBaseButton-secondary"] {
            font-size: 1.05rem !important;
        }
        [data-testid="stDataFrame"] { font-size: 1rem !important; }
        h1 { font-size: 2rem !important; }
        h2 { font-size: 1.55rem !important; }
        h3 { font-size: 1.35rem !important; }
        .aether-hero {
            background: linear-gradient(90deg, #151B2E 0%, #1b2744 55%, #12324a 100%);
            border: 1px solid rgba(79,195,247,0.25);
            border-radius: 16px;
            padding: 1.1rem 1.4rem 0.9rem 1.4rem;
            margin-bottom: 1rem;
        }
        .aether-kicker { color: #4FC3F7; letter-spacing: 0.18em; font-size: 0.95rem; font-weight: 700; }
        .aether-title { font-size: 2.15rem; font-weight: 700; margin: 0.15rem 0 0.2rem 0; }
        .aether-sub { color: #9BB0C9; margin: 0; font-size: 1.1rem; }
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


def _part_card(
    row: pd.Series,
    bundle: object,
    param_sel: str,
    iforest_range: tuple[float, float] | None,
    slider_key: str,
) -> None:
    card = explain_part(row, bundle.drift)
    dcol, scol, hcol = st.columns(3)
    dcol.markdown(
        f"### Decision: <span class='decision-{card['decision']}'>{card['decision']}</span>",
        unsafe_allow_html=True,
    )
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
            _chart(_series_figure(row, param))

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
            _chart(_waterfall(pcard))

    st.markdown("#### Inspector brief (copy into the lot traveller)")
    st.code(card["inspector_brief"], language=None)

    st.markdown("#### What-if: 24 h reading")
    current = float(row[f"{param_sel}_24h"])
    vmax = max(float(PARAM_META[param_sel]["datasheet_max"]), current * 1.15)
    vmin = min(current * 0.4, current) if current > 0 else 0.0
    if vmin >= vmax:
        vmin = 0.0
    wcol, _ = st.columns([1.2, 1.8])
    with wcol:
        tweaked = float(st.slider(
            f"{PARAM_META[param_sel]['label']} @ 24 h",
            min_value=float(vmin),
            max_value=float(vmax),
            value=current,
            key=slider_key,
        ))
    if abs(tweaked - current) > 1e-9:
        probe = row.copy()
        probe[f"{param_sel}_24h"] = tweaked
        probe[f"{param_sel}_slope24"] = (tweaked - float(probe[f"{param_sel}_0h"])) / 24.0
        probe[f"{param_sel}_rel24"] = (tweaked - float(probe[f"{param_sel}_0h"])) / max(float(probe[f"{param_sel}_0h"]), 0.05)
        probe[f"{param_sel}_24h_z"] = (tweaked - float(probe[f"{param_sel}_24h_median"])) / float(probe[f"{param_sel}_24h_sigma"])
        probe[f"{param_sel}_slope24_z"] = (
            float(probe[f"{param_sel}_slope24"]) - float(probe[f"{param_sel}_slope24_median"])
        ) / float(probe[f"{param_sel}_slope24_sigma"])
        replay = apply_models(pd.DataFrame([probe]), bundle, iforest_range=iforest_range).iloc[0]
        st.warning(
            f"If 24 h {param_sel} were {tweaked:.3f} {PARAM_META[param_sel]['unit']}, "
            f"decision would be **{replay['decision']}** (score {replay['fused_score']:.2f})."
        )


def _render_live_results(result: pd.DataFrame, bundle: object, param_sel: str, iforest_range: tuple[float, float], key_prefix: str) -> None:
    param_sel = st.selectbox(
        "Parameter",
        list(PARAMS),
        index=list(PARAMS).index(param_sel) if param_sel in PARAMS else 1,
        format_func=lambda p: PARAM_META[p]["label"],
        key=f"{key_prefix}_param",
    )
    st.markdown("#### Decision counts (PASS / HOLD / REJECT)")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("PASS", int(result["decision"].eq("PASS").sum()))
    k2.metric("HOLD", int(result["decision"].eq("HOLD").sum()))
    k3.metric("REJECT", int(result["decision"].eq("REJECT").sum()))
    k4.metric("Parts screened", f"{len(result):,}")
    k5.metric("Chamber hours saved", int(result["hours_saved"].sum()))

    col_a, col_b = st.columns([1, 2])
    with col_a:
        _chart(_decision_pie(result))
        st.caption("PASS = finish 168 h · HOLD = extra 96 h readout · REJECT = pull now.")
    with col_b:
        st.markdown("#### Lot scatter (0 h vs 24 h)")
        _chart(_lot_scatter(result, param_sel))
        st.caption(
            f"Each point is one part. X is {PARAM_META[param_sel]['label']} at 0 h, "
            f"Y is the same parameter at 24 h, colored by the decision."
        )

    later_plots = [(hour, _measured_vs_predicted(result, param_sel, hour)) for hour in (96, 168)]
    later_plots = [(hour, fig) for hour, fig in later_plots if fig is not None]
    if later_plots:
        st.markdown("#### Measured vs forecast")
        cols = st.columns(len(later_plots))
        for col, (hour, fig) in zip(cols, later_plots):
            with col:
                _chart(fig)
        st.caption(
            "These points are only a comparison. PASS / HOLD / REJECT was decided from 0 h and 24 h."
        )

    ranked = result.sort_values("fused_score", ascending=False)
    st.dataframe(
        ranked[["part_id", "lot_id", "decision", "decision_reason"]],
        hide_index=True,
        height=320,
        **_wide(),
    )
    st.download_button(
        "Download the scored CSV",
        result.to_csv(index=False).encode("utf-8"),
        file_name="aether_scored_lot.csv",
        mime="text/csv",
        key=f"{key_prefix}_download",
    )

    st.markdown("#### Part picker")
    pick = st.selectbox("Part", ranked["part_id"].tolist(), key=f"{key_prefix}_part")
    row = ranked.loc[ranked["part_id"] == pick].iloc[0]
    with st.expander("Inspect this part", expanded=False):
        _part_card(row, bundle, param_sel, iforest_range, slider_key=f"{key_prefix}_whatif")


def _apply_live_preset(wanted: dict[str, float], preset: str) -> None:
    for key, val in wanted.items():
        if f"live_n_{key}" not in st.session_state:
            st.session_state[f"live_n_{key}"] = val
    if st.session_state.get("live_preset_applied") != preset:
        st.session_state.live_preset_applied = preset
        for key, val in wanted.items():
            st.session_state[f"live_n_{key}"] = val


def _live_lot_editor(bundle: object, param_sel: str, iforest_range: tuple[float, float]) -> None:
    top = st.columns([1.4, 1, 1.3])
    with top[0]:
        uploaded = st.file_uploader("Upload a CSV lot", type=["csv"], key="live_csv")
    with top[1]:
        st.download_button(
            "Download CSV template",
            template_csv_bytes(),
            file_name="aether_live_template.csv",
            mime="text/csv",
            key="live_template_dl",
        )
    with top[2]:
        if st.button("Load example lot (25 parts, one maverick)", key="live_load_example"):
            st.session_state.live_lot_df = for_editor(template_frame())
            st.session_state.live_editor_n = int(st.session_state.get("live_editor_n", 0)) + 1
            st.session_state.live_score_now = True

    if "live_lot_df" not in st.session_state:
        st.session_state.live_lot_df = for_editor(blank_frame(6))

    if uploaded is not None:
        file_id = f"{uploaded.name}-{uploaded.size}"
        if st.session_state.get("live_csv_id") != file_id:
            try:
                st.session_state.live_lot_df = for_editor(parse_live_upload(uploaded.getvalue()))
                st.session_state.live_csv_id = file_id
                st.session_state.live_editor_n = int(st.session_state.get("live_editor_n", 0)) + 1
                st.session_state.live_score_now = True
            except LiveScreenError as exc:
                st.error(str(exc))

    st.markdown("Edit cells directly. Required: 0 h and 24 h for IDDQ, leakage, and tpd.")
    number_cols = {
        col: st.column_config.NumberColumn(col, format="%.3f") for col in REQUIRED_MEASURES
    }
    try:
        edited = st.data_editor(
            for_editor(st.session_state.live_lot_df),
            num_rows="dynamic",
            hide_index=True,
            column_config=number_cols,
            key=f"live_editor_{st.session_state.get('live_editor_n', 0)}",
            **_wide(),
        )
    except TypeError:
        edited = st.data_editor(
            for_editor(st.session_state.live_lot_df),
            num_rows="dynamic",
            hide_index=True,
            key=f"live_editor_{st.session_state.get('live_editor_n', 0)}",
            use_container_width=True,
        )
    except Exception as exc:
        st.error(f"The editor could not draw this table: {exc}")
        return
    st.session_state.live_lot_df = for_editor(edited)

    score_clicked = st.button("Score this lot", type="primary", key="live_score_btn")
    if score_clicked:
        st.session_state.live_score_now = True
    if not st.session_state.get("live_score_now"):
        st.info("Load the example lot, upload a CSV, or fill the table, then click **Score this lot**.")
        return
    try:
        live_rows = complete_rows(st.session_state.live_lot_df)
        if live_rows.empty:
            st.info("Fill 0 h and 24 h for at least two parts in the same lot.")
            return
        result, warnings = screen_lot(live_rows, bundle, iforest_range=iforest_range)
    except LiveScreenError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Scoring failed: {exc}")
        return
    for msg in warnings:
        st.warning(msg)
    st.success(f"Screened {len(result)} part(s) with the frozen bundle. screening_results.csv was not written.")
    _render_live_results(result, bundle, param_sel, iforest_range, key_prefix="live_lot")


def _live_one_part(
    screened: pd.DataFrame,
    bundle: object,
    param_sel: str,
    iforest_range: tuple[float, float],
) -> None:
    lots = sorted(screened["lot_id"].unique().tolist())
    default_lot = lots.index("LOTSIH") if "LOTSIH" in lots else 0
    ref_id = st.selectbox(
        "Reference lot (PAT is relative to this lot's median / MAD)",
        lots,
        index=default_lot,
        key="live_ref_lot",
    )
    ref = screened[screened["lot_id"] == ref_id]
    st.caption(
        f"{len(ref)} parts in {ref_id}. Your component is compared to this lot, not to the datasheet box. "
        "Use this when you have one new reading and already know the lot it belongs with."
    )
    preset = st.radio(
        "Preset",
        ["Nominal healthy", "SIH textbook maverick (45 µA leakage)"],
        horizontal=True,
        key="live_preset",
    )
    wanted = TEXTBOOK_MAVERICK if "maverick" in preset.lower() else NOMINAL_HEALTHY
    _apply_live_preset(wanted, preset)

    id_col, _ = st.columns([1, 2])
    with id_col:
        part_id = st.text_input("Part id", value="MY-PART", key="live_part_id")

    grid = st.columns(3)
    values: dict[str, float] = {}
    for i, param in enumerate(PARAMS):
        with grid[i]:
            st.markdown(f"**{PARAM_META[param]['label']}** ({PARAM_META[param]['unit']})")
            for t in (0, 24):
                key = f"{param}_{t}h"
                values[key] = float(st.number_input(
                    f"{t} h",
                    min_value=0.0,
                    max_value=float(PARAM_META[param]["datasheet_max"]) * 1.5,
                    step=0.01,
                    format="%.3f",
                    key=f"live_n_{key}",
                ))
    try:
        result = screen_one_part(
            {"part_id": part_id, "lot_id": ref_id, **values},
            ref,
            bundle,
            iforest_range=iforest_range,
        )
    except LiveScreenError as exc:
        st.error(str(exc))
        return
    st.success("Scored in real time — change any reading and the decision updates on the next rerun.")
    _part_card(result.iloc[0], bundle, param_sel, iforest_range, slider_key="live_one_whatif")


def _live_tab(screened: pd.DataFrame, bundle: object, param_sel: str, iforest_range: tuple[float, float]) -> None:
    st.markdown("### Screen my data")
    st.caption("Inference only. 168 h is never an input.")
    st.caption(
        "Upload or edit a lot CSV, or enter one part against a canned lot. "
        "The loaded models score 0 h and 24 h immediately."
    )
    mode = st.radio(
        "How do you want to enter readings?",
        ["Upload or edit a lot", "Enter one component"],
        horizontal=True,
        key="live_mode",
    )
    if mode == "Upload or edit a lot":
        _live_lot_editor(bundle, param_sel, iforest_range)
        return
    _live_one_part(screened, bundle, param_sel, iforest_range)


def _filter_row(screened: pd.DataFrame, key_prefix: str) -> tuple[str, pd.DataFrame]:
    lots = ["All lots"] + sorted(screened["lot_id"].unique().tolist())
    splits = ["All splits", "train", "val", "test"]
    left, mid, right = st.columns([1.3, 1, 1])
    with left:
        lot_sel = st.selectbox("Lot", lots, key=f"{key_prefix}_lot")
    with mid:
        split_sel = st.selectbox(
            "Split",
            splits,
            index=3 if "test" in screened["split"].values else 0,
            key=f"{key_prefix}_split",
        )
    with right:
        param_sel = st.selectbox(
            "Parameter",
            list(PARAMS),
            index=1,
            format_func=lambda p: PARAM_META[p]["label"],
            key=f"{key_prefix}_param",
        )
    view = screened.copy()
    if lot_sel != "All lots":
        view = view[view["lot_id"] == lot_sel]
    if split_sel != "All splits":
        view = view[view["split"] == split_sel]
    return param_sel, view


def _kpi_row(report: dict) -> None:
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


def main() -> None:
    _style_header()
    try:
        screened, bundle, report, iforest_range = _ensure_artifacts()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    test_m = report["test"]
    tab_dash, tab_inspect, tab_live, tab_rubric, tab_method = st.tabs(
        [
            "Lot board",
            "QA inspector",
            "Screen my data",
            "Judging rubric",
            "Methodology",
        ]
    )

    with tab_dash:
        param_sel, view = _filter_row(screened, "dash")
        _kpi_row(report)
        col_a, col_b = st.columns([1, 2])
        with col_a:
            _chart(_decision_pie(view))
            st.caption("PASS = no anomaly, finish 168 h · HOLD = extra 96 h readout · REJECT = pull from the chamber now.")
        with col_b:
            _chart(_lot_scatter(view, param_sel))

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
            hide_index=True,
            height=360,
            **_wide(),
        )

    with tab_inspect:
        param_sel, view = _filter_row(screened, "insp")
        focus_pool = view.sort_values("fused_score", ascending=False)
        if focus_pool.empty:
            st.warning("No parts in this filter.")
        else:
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

            part_id = st.selectbox(
                "Component",
                focus_pool["part_id"].tolist(),
                index=min(default_idx, len(focus_pool) - 1),
            )
            row = focus_pool.loc[focus_pool["part_id"] == part_id].iloc[0]
            _part_card(row, bundle, param_sel, iforest_range, slider_key="inspect_whatif")

    with tab_live:
        _live_tab(screened, bundle, "ileak", iforest_range)

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
            _md(
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
        _md(
            """
            ### The gap static limits cannot close

            A lot whose leakage centroid sits at 10 µA can still have a 45 µA maverick
            that is *legal* against a 50 µA datasheet. That part is a process outlier.
            In a flight payload it is an infant-mortality risk. Module A is **dynamic
            Part Average Testing** (robust median + MAD, Isolation Forest, Mahalanobis)
            computed **inside the lot**, not against the data book.

            ### Early reject at 24 h

            Module B never waits for 168 h. It takes 0 h and 24 h readings,
            predicts the 168 h value, and compares the implied slope to the healthy
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

            ### Screen my data

            Models are trained offline on historical lots. At the 24 h gate a new lot CSV
            is scored with the frozen bundle: lot-relative PAT + 168 h drift forecast.
            No 168 h reading is used at inference. **Screen my data** is that path: upload
            or edit a lot, or enter one part against a reference lot. `POST /screen-lot`
            calls the same scoring function. The upload does not retrain
            `screening_bundle.joblib`.
            """
        )
        _render_method_results(report)


if __name__ == "__main__":
    main()

# AETHER — Adaptive ESS Thermal Health & Early Reject

**SIH26170 · AI-Driven Anomaly Detection in Component Burn-In & Screening**
Organization: ISRO / Department of Space · Theme: Smart Automation

Traditional burn-in screening at 125 °C uses **static datasheet limits**. That misses
*latent defects*: parts that stay inside the data-book box but sit far from their
lot, or that drift on a slope no healthy part in the lot would take. Those parts
escape into payloads.

AETHER adds two modules the problem statement asks for, then fuses them into a
three-way QA decision a human inspector can read.

```
                 ┌─────────────────────────────────────────────┐
  Lot of parts   │  Module A  Dynamic outlier (PAT / DPAT)     │
  0 h, 24 h  ──► │   robust median+MAD · Isolation Forest      │
  (96, 168 hidden│   robust Mahalanobis                        │
   at early gate)│                                             │
                 │  Module B  Drift predictor                  │
                 │   0 h + 24 h  →  predicted 168 h            │
                 │   vs safety slope + 90% datasheet           │
                 └──────────────────┬──────────────────────────┘
                                    ▼
                      PASS  |  HOLD (to 96 h)  |  REJECT now
                      + inspector brief in engineering English
```

## Why this matches the evaluation rubric

| Metric | How AETHER treats it |
| --- | --- |
| **Anomaly detection / FN cost** | Thresholds are calibrated on held-out lots with FN cost 1000 vs FP cost 12. A missed defective is the thing we refuse to optimize away. |
| **Drift prediction MAE** | Ridge + optional HGB blend, reported against a linear-extrapolation baseline. 168 h is never an input at inference. |
| **Explainability** | Robust z vs lot median, PAT hits, predicted slope vs healthy 95th percentile, and Ridge feature contributions — not a black-box score. |

## Quick start

```powershell
cd C:\Users\amolw\OneDrive\Desktop\pioneers
python -m pip install -r requirements-dev.txt
python scripts\train.py
python scripts\evaluate.py
python -m streamlit run app.py
```

First run synthesizes lot-structured burn-in data (ISRO flight data is not public),
trains on some lots, and scores **unseen lots**. Artifacts from `scripts/train.py`
are already in `data/` and `models/` so the dashboard opens immediately.

## Public deploy (Streamlit Community Cloud)

The GitHub repo is public: [amol16112005/AETHER-SIH26170](https://github.com/amol16112005/AETHER-SIH26170).

1. Open [share.streamlit.io/deploy](https://share.streamlit.io/deploy) and sign in with GitHub.
2. Repository: `amol16112005/AETHER-SIH26170`
3. Branch: `main`
4. Main file path: `app.py`
5. Optional App URL: `aether-sih26170` → `https://aether-sih26170.streamlit.app`
6. Advanced settings: Python **3.12**
7. Click **Deploy**. Apps default to public once they are live; use **Share → Make this app public** if asked.

## Held-out lot results

24 lots, 4,945 parts. Train / val / test are **split by lot**, not by part.
Every defective in the test lots still passes the datasheet at 24 h — a static
screen would miss all of them.

| | Value |
| --- | --- |
| Detection recall (FN is the thing ISRO penalizes) | **100%** (0 miss / 102 latent defects) |
| Latent-escape catch rate | **100%** |
| 24 h REJECT precision | **98.7%** (two-signal rule: PAT or unsafe drift) |
| Decisions | 1,172 PASS · 202 HOLD · 75 REJECT |
| IDDQ 168 h MAE | **0.51 µA** vs 1.26 µA linear extrapolation |
| Leakage 168 h MAE | **0.31 µA** vs 0.72 µA |
| tpd 168 h MAE | **0.07 ns** vs 0.19 ns |
| Chamber hours recovered from early REJECT | 10,800 h on the test lots |
| Textbook example LOTSIH-0045 | Static **PASS** (45.3 < 50) · Dynamic **REJECT** (z = 35 vs lot 10.1 µA) |

## What the models actually do

### Module A — dynamic outliers

Static example from the problem: lot leakage 10 µA, part 45 µA, datasheet 50 µA.
A datasheet check passes. Robust PAT (`median + 6 × 1.4826 × MAD`, AEC-Q001 style)
does not. Isolation Forest and MinCovDet Mahalanobis run on **lot-normalized**
features so a fast process corner does not get the whole lot scrapped.

### Module B — 24 h → 168 h

Inputs: `Value_0h`, `Value_24h` (plus slope, relative change, log, linear
extrapolation). Target: hidden `Value_168h` for IDDQ, leakage, and tpd.
If the predicted slope exceeds the healthy 95th-percentile safety slope, or the
forecast crosses 90% of the datasheet cap, the part is flagged for early reject.

### Decision policy

| Decision | Meaning | Chamber time |
| --- | --- | --- |
| **PASS** | Lot-relative and predicted drift are inside the envelope | Finish the remaining 168 h burn-in |
| **HOLD** | Borderline — do not treat as clean, do not scrap yet | Extra readout at 96 h |
| **REJECT** | Maverick and/or unsafe predicted drift | Pull at 24 h (144 h of chamber time recovered) |

Flight parts that look healthy still complete burn-in. The only hours we claim
back are slots freed by early REJECT. HOLD exists because space-grade silicon
is expensive: a two-class scrap/release policy is the wrong shape.

The problem-statement worked example is pinned as **LOTSIH-0045**: lot leakage
≈ 10 µA, part at 45 µA, datasheet 50 µA. Static screen: PASS. Dynamic PAT: REJECT.
Open *QA inspector* or *Judging rubric* to see the inspector brief.

Full write-up (electronics, software, ML, results):
`docs/AETHER_SIH26170_Technical_Report.docx`

## Project layout

```
app.py                 Streamlit QA workstation
scripts/train.py       Generate data, train, write metrics
src/generate_data.py   Physics-informed latent-defect lots
src/module_a.py        PAT + Isolation Forest + Mahalanobis
src/module_b.py        Ridge / HGB 168 h forecast
src/decisions.py       Cost-sensitive PASS/HOLD/REJECT
src/explain.py         Inspector-grade natural language
tests/                 PAT unit test + held-out recall smoke
```

## Notes for judges

- Splits are **by lot**, not by part. A model that memorizes one process corner
  does not get credit on another.
- The synthetic generator injects the three modes that matter: **mavericks**
  (in-spec, off-lot), **latent drift** (normal 0 h, bad slope), and **runaway**
  (quadratic aging that static limits only catch late).
- Replace `data/burnin_parts.csv` with a real ATE export (same column names) and
  re-run `python scripts/train.py`. No other code changes.

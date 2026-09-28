"""Fill the official SIH 2026 idea-submission template with AETHER content."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "unpacked_aether"
SLIDES = ROOT / "ppt" / "slides"
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

import defusedxml.minidom as minidom


def set_t(el, text: str) -> None:
    # Keep a single text node
    while el.firstChild:
        el.removeChild(el.firstChild)
    el.appendChild(el.ownerDocument.createTextNode(text))
    if text[:1] in " " or text[-1:] in " ":
        el.setAttribute("xml:space", "preserve")


def replace_exact(doc, old: str, new: str, count: int = 1) -> int:
    n = 0
    for t in doc.getElementsByTagName("a:t"):
        if (t.firstChild and t.firstChild.data == old) or (
            "".join(c.data for c in t.childNodes if c.nodeType == t.TEXT_NODE) == old
        ):
            set_t(t, new)
            n += 1
            if n >= count:
                break
    return n


def clone_para(sample_p, text: str, *, bold: bool | None = None, size: str | None = None):
    p = sample_p.cloneNode(True)
    runs = p.getElementsByTagName("a:r")
    if not runs:
        return p
    first = runs[0]
    # drop extra runs
    for r in list(runs)[1:]:
        r.parentNode.removeChild(r)
    t_el = first.getElementsByTagName("a:t")[0]
    set_t(t_el, text)
    rPr = first.getElementsByTagName("a:rPr")
    if rPr:
        if bold is True:
            rPr[0].setAttribute("b", "1")
        elif bold is False and rPr[0].hasAttribute("b"):
            rPr[0].removeAttribute("b")
        if size:
            rPr[0].setAttribute("sz", size)
    # drop endParaRPr leftover from clone is fine
    return p


def fill_body(slide_path: Path, bullets: list[tuple[str, bool]], size: str = "1800") -> None:
    """Replace all content paragraphs in the first large text box (TextBox 8)."""
    raw = slide_path.read_text(encoding="utf-8")
    doc = minidom.parseString(raw)
    boxes = [
        sp
        for sp in doc.getElementsByTagName("p:sp")
        if any(
            nv.getAttribute("name").startswith("TextBox")
            for nv in sp.getElementsByTagName("p:cNvPr")
        )
    ]
    if not boxes:
        raise SystemExit(f"no text box in {slide_path}")
    # pick the content box: largest / named TextBox 8
    target = None
    for sp in boxes:
        name = sp.getElementsByTagName("p:cNvPr")[0].getAttribute("name")
        if name == "TextBox 8":
            target = sp
            break
    if target is None:
        target = boxes[0]
    tx = target.getElementsByTagName("p:txBody")[0]
    paras = [c for c in tx.childNodes if getattr(c, "tagName", "") == "a:p"]
    if not paras:
        raise SystemExit(f"no paragraphs in {slide_path}")
    sample = paras[0]
    # remove existing paragraphs
    for p in paras:
        tx.removeChild(p)
    for text, is_header in bullets:
        tx.appendChild(clone_para(sample, text, bold=is_header, size="2000" if is_header else size))
    # enlarge the box so extra bullets fit between title and footer
    xfrm = None
    for spPr in target.getElementsByTagName("p:spPr"):
        xs = spPr.getElementsByTagName("a:xfrm")
        if xs:
            xfrm = xs[0]
            break
    if xfrm:
        off = xfrm.getElementsByTagName("a:off")[0]
        ext = xfrm.getElementsByTagName("a:ext")[0]
        # keep x; start just under the title (~1.35 in) and go down to footer (~6.85 in)
        off.setAttribute("y", "1220000")
        ext.setAttribute("cy", "5000000")
        # full-ish width
        off.setAttribute("x", "400000")
        ext.setAttribute("cx", "11300000")
    slide_path.write_text(doc.toxml(), encoding="utf-8")


def save(doc, path: Path) -> None:
    path.write_text(doc.toxml(), encoding="utf-8")


def fill_slide1() -> None:
    path = SLIDES / "slide1.xml"
    doc = minidom.parseString(path.read_text(encoding="utf-8"))
    mapping = {
        "Problem Statement ID –": "Problem Statement ID – SIH26170",
        "Problem Statement Title-": "Problem Statement Title- AI-Driven Anomaly Detection in Component Burn-In & Screening",
        "Theme-": "Theme- Smart Automation",
        "PS Category- Software/Hardware": "PS Category- Software",
        "Team ID-": "Team ID- (enter SIH portal Team ID)",
        "Team Name (Registered on portal)": "Team Name – Pioneers",
    }
    for old, new in mapping.items():
        n = replace_exact(doc, old, new)
        if n != 1:
            print(f"WARN slide1 '{old}' replaced {n} times")
    # tighten line spacing so the long title wraps cleanly
    for pPr in doc.getElementsByTagName("a:pPr"):
        for ln in pPr.getElementsByTagName("a:spcPct"):
            ln.setAttribute("val", "130000")
    save(doc, path)


def fill_slide2() -> None:
    path = SLIDES / "slide2.xml"
    doc = minidom.parseString(path.read_text(encoding="utf-8"))
    n = replace_exact(doc, "IDEA TITLE", "AETHER — Adaptive ESS Thermal Health & Early Reject")
    print("slide2 title", n)
    n = replace_exact(doc, "Your Team Name", "Pioneers")
    print("slide2 team", n)
    save(doc, path)
    fill_body(
        path,
        [
            ("Proposed Solution (Describe your Idea/Solution/Prototype)", True),
            ("AETHER: lot-aware PAT outlier screen + 24 h → 168 h drift predictor. After 24 h of 125 °C burn-in it returns PASS / HOLD / REJECT plus an inspector brief in engineering English.", False),
            ("Working prototype: Streamlit QA workstation with Lot board, QA inspector, Screen-my-data, judging rubric. Public demo on Render / Streamlit Cloud.", False),
            ("Detailed explanation of the proposed solution", True),
            ("Module A — dynamic outliers: robust PAT (median + 6 × 1.4826 × MAD, AEC-Q001), Isolation Forest, robust Mahalanobis. Scores are lot-normalised so a fast process corner is not scrapped.", False),
            ("Module B — drift: Ridge (inspectable) + optional HGB blend forecasts 168 h from 0 h and 24 h only. Flags if predicted slope > healthy 95th percentile or forecast crosses 90% of the datasheet cap.", False),
            ("How it addresses the problem", True),
            ("Static 50 µA datasheet PASS on a 45 µA part in a 10 µA lot (SIH example LOTSIH-0045). Dynamic PAT REJECTS it. Latent drift is pulled at 24 h instead of escaping into a payload.", False),
            ("Innovation and uniqueness of the solution", True),
            ("Two-signal REJECT (PAT or unsafe drift) — a lone Isolation Forest twitch cannot kill a flight part. HOLD band (not scrap/release). FN cost 1000 vs FP 12. Ridge waterfalls a QA inspector can argue with.", False),
            ("Held-out lots (25 lots, 5,145 parts, split by lot): 0 escapes — 75 rejected at 24 h, 27 sent to the 96 h check, 12.7% of healthy parts held. 100% is the catch rate (HOLD or REJECT); REJECT-only recall is 75/102. 24 h REJECT precision 98.7%. IDDQ 168 h MAE 0.51 µA vs 1.26 µA linear extrapolation. Optional extras: VTH, IDSAT, reverse leakage, IDDQ/T.", False),
        ],
        size="1500",
    )


def fill_slide3() -> None:
    path = SLIDES / "slide3.xml"
    doc = minidom.parseString(path.read_text(encoding="utf-8"))
    replace_exact(doc, "Your Team Name", "Pioneers")
    save(doc, path)
    fill_body(
        path,
        [
            ("Technologies to be used (programming languages, frameworks, hardware)", True),
            ("Python 3.12 · scikit-learn (IsolationForest, MinCovDet, RidgeCV, HistGradientBoosting) · pandas / NumPy · joblib frozen bundle", False),
            ("Streamlit + Plotly QA workstation · pytest · GitHub Actions-ready scripts (train.py, evaluate.py, predict_realtime_iddq.py)", False),
            ("No extra hardware: laptop / 512 MB web instance. Optional ATE CSV ingest. Deploy: Render Blueprint + Streamlit Community Cloud", False),
            ("Methodology and process for implementation (flow / working prototype)", True),
            ("1. Physics-informed lots (0 / 24 / 96 / 168 h IDDQ, leakage, tpd) — ISRO flight data is not public", False),
            ("2. Split by LOT (not by part) → train Module A + Module B on train lots, freeze on val, score unseen test lots", False),
            ("3. Inference uses only 0 h and 24 h. 96 h / 168 h stay hidden at the early gate", False),
            ("4. Fusion: outlier_score = 0.40 PAT + 0.35 Isolation Forest + 0.25 Mahalanobis → PASS | HOLD | REJECT", False),
            ("Flow: Lot CSV → PAT / IF / Mahalanobis + 168 h forecast → decision + traveller brief → QA override", False),
            ("Prototype live: Screen-my-data tab (upload lot or one part vs a reference lot). Pinned example LOTSIH-0045.", False),
        ],
        size="1500",
    )


def fill_slide4() -> None:
    path = SLIDES / "slide4.xml"
    doc = minidom.parseString(path.read_text(encoding="utf-8"))
    replace_exact(doc, "Your Team Name", "Pioneers")
    save(doc, path)
    fill_body(
        path,
        [
            ("Analysis of the feasibility of the idea", True),
            ("Software-only. Models already trained; artifacts in data/ and models/. Dashboard opens without a GPU.", False),
            ("Fits SIH 36-hour finale: train.py / evaluate.py / Streamlit. Tests encode the official 10 µA / 45 µA / 50 µA example.", False),
            ("No ITAR data needed. Production path: ATE CSV / STDF → freeze PAT k and safety slope on a qualification lot.", False),
            ("Potential challenges and risks", True),
            ("False REJECT if the “lot” mixes process corners (fast + slow wafers labelled as one lot).", False),
            ("Isolation Forest contamination and PAT k = 6 are policy knobs — a cleaner line may want them tighter or looser.", False),
            ("Unit mix-up (nA vs µA) or swapped 0 h / 24 h columns looks like a lot excursion.", False),
            ("Strategies for overcoming these challenges", True),
            ("Lot identity must be real. Two-signal REJECT. QA lead can force HOLD — software is not the last word on a Class-1 part.", False),
            ("Unit / serial checks before scoring. Retrain on a known-good historical set when labels are absent.", False),
            ("HOLD at 96 h instead of scrap/release so expensive space-grade silicon is not thrown away on a borderline score.", False),
        ],
        size="1500",
    )


def fill_slide5() -> None:
    path = SLIDES / "slide5.xml"
    doc = minidom.parseString(path.read_text(encoding="utf-8"))
    replace_exact(doc, "Your Team Name", "Pioneers")
    save(doc, path)
    fill_body(
        path,
        [
            ("Potential impact on the target audience", True),
            ("ISRO / Department of Space screening houses, ATE operators, and QA inspectors who today apply static datasheet limits.", False),
            ("Catches latent escapes a 50 µA cap misses (textbook: 45 µA in a 10 µA lot → static PASS, dynamic REJECT).", False),
            ("Held-out: 0 false negatives / 102 latent defects; 1,172 PASS · 202 HOLD · 75 REJECT; 10,800 chamber-hours recovered from early REJECT.", False),
            ("Benefits of the solution (social, economic, environmental)", True),
            ("Mission / social: fewer infant-mortality failures in flight payloads — the FN the problem statement penalises.", False),
            ("Economic: 144 h of 125 °C soak freed per early REJECT; HOLD protects costly space-grade parts from a two-class scrap policy.", False),
            ("Environmental: less wasted high-temperature chamber energy on parts that will fail by 168 h anyway.", False),
            ("Explainability (SIH rubric): robust z vs lot, PAT hits, predicted slope vs healthy 95th percentile, Ridge feature waterfalls.", False),
        ],
        size="1500",
    )


def fill_slide6() -> None:
    path = SLIDES / "slide6.xml"
    doc = minidom.parseString(path.read_text(encoding="utf-8"))
    replace_exact(doc, "Your Team Name", "Pioneers")
    save(doc, path)
    fill_body(
        path,
        [
            ("Details / Links of the reference and research work", True),
            ("[1] SIH26170 — AI-Driven Anomaly Detection in Component Burn-In & Screening, ISRO / DoS. https://sih2026.vuce.in/ps/SIH26170", False),
            ("[2] AEC-Q001 Rev-D, Guidelines for Part Average Testing (robust mean ± 6 robust sigma / DPAT).", False),
            ("[3] MIL-STD-883 Test Method 1015, Burn-in Test · [4] MIL-PRF-38535 Class Q / V screening (160–240 h at 125 °C).", False),
            ("[5][6] Hawkins, Soden et al. — IDDQ testing of CMOS defects (IEEE Trans. Ind. Electron. 1989; IDDQ Testing of VLSI Circuits, 1992).", False),
            ("[7] Nigh et al., Failure analysis of timing and IDDq-only failures, SEMATECH, ITC 1998 (12 confirmed-defect ICs used as a real check).", False),
            ("[8] Liu, Ting, Zhou — Isolation Forest, IEEE ICDM 2008.  [9] Rousseeuw & van Driessen — MinCovDet, Technometrics 1999.", False),
            ("[12] Hoerl & Kennard — Ridge Regression, Technometrics 1970.  [13] Friedman — Gradient boosting, Ann. Statist. 2001.", False),
            ("[14] Pedregosa et al. — scikit-learn, JMLR 2011.  [15] Elkan — Foundations of Cost-Sensitive Learning, IJCAI 2001.", False),
            ("Full IEEE list: docs/AETHER_SIH26170_References_and_Sources.docx  ·  Repo: github.com/amol16112005/AETHER-SIH26170", False),
        ],
        size="1400",
    )


def main() -> None:
    fill_slide1()
    fill_slide2()
    fill_slide3()
    fill_slide4()
    fill_slide5()
    fill_slide6()
    print("filled slides 1-6")


if __name__ == "__main__":
    main()

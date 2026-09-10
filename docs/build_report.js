/**
 * AETHER technical report generator — SIH26170
 */
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
        ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
        TableOfContents } = require("docx");
const fs = require("fs");
const path = require("path");

const NAVY = "1B365D";
const GOLD = "C45C26";
const LIGHT = "EEF3F8";
const ROW = "F7F9FC";
const WHITE = "FFFFFF";
const MUTED = "5B6B7C";
const RULE = "C5D0DC";
const TW = 9026; // A4, 1" margins

const thin = { style: BorderStyle.SINGLE, size: 4, color: RULE };
const borders = { top: thin, bottom: thin, left: thin, right: thin };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

const r = (text, o = {}) => new TextRun({
  text, font: "Arial", size: o.size || 22, bold: o.bold, italics: o.italics,
  color: o.color || "222222",
});

const p = (text, o = {}) => new Paragraph({
  spacing: { after: o.after ?? 160, before: o.before ?? 0, line: 276 },
  alignment: o.align,
  children: [r(text, o)],
});

const rich = (runs, o = {}) => new Paragraph({
  spacing: { after: o.after ?? 160, before: o.before ?? 0, line: 276 },
  alignment: o.align,
  children: runs.map((x) => (typeof x === "string" ? r(x) : r(x.text, x))),
});

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  pageBreakBefore: true,
  children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: NAVY })],
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: NAVY })],
});

const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  children: [new TextRun({ text, font: "Arial", size: 24, bold: true, color: GOLD })],
});

function cell(text, width, opts = {}) {
  const fill = opts.fill || WHITE;
  const color = opts.color || (opts.header ? WHITE : "222222");
  const bold = opts.header || opts.bold || false;
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 70, bottom: 70, left: 100, right: 100 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      children: [r(String(text), { size: opts.size || 20, bold, color, italics: opts.italics })],
    })],
  });
}

function table(headers, rows, widths) {
  const head = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => cell(h, widths[i], { header: true, fill: NAVY })),
  });
  const body = rows.map((row, ri) => new TableRow({
    children: row.map((c, i) => cell(c, widths[i], { fill: ri % 2 === 0 ? ROW : WHITE })),
  }));
  return new Table({
    width: { size: TW, type: WidthType.DXA },
    columnWidths: widths,
    rows: [head, ...body],
  });
}

const gap = () => new Paragraph({ spacing: { after: 120 }, children: [] });

const bullet = (text, ref = "bullets") => new Paragraph({
  numbering: { reference: ref, level: 0 },
  spacing: { after: 80, line: 276 },
  children: [r(text, { size: 21 })],
});

const bullet2 = (text) => new Paragraph({
  numbering: { reference: "bullets2", level: 0 },
  spacing: { after: 80, line: 276 },
  children: [r(text, { size: 21 })],
});

const num = (text, ref = "numbers") => new Paragraph({
  numbering: { reference: ref, level: 0 },
  spacing: { after: 80, line: 276 },
  children: [r(text, { size: 21 })],
});

const caption = (text) => p(text, { size: 18, italics: true, color: MUTED, after: 240 });

const kvTable = (pairs) => table(
  ["Item", "Detail"],
  pairs,
  [2800, 6226],
);

async function main() {
  const doc = new Document({
    styles: {
      default: { document: { run: { font: "Arial", size: 22 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 32, bold: true, font: "Arial", color: NAVY },
          paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 26, bold: true, font: "Arial", color: NAVY },
          paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1 } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 24, bold: true, font: "Arial", color: GOLD },
          paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
      ],
    },
    numbering: {
      config: [
        { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "bullets2", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "numbers2", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "runsteps", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      ],
    },
    sections: [{
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: NAVY, space: 8 } },
            spacing: { after: 120 },
            children: [
              r("AETHER  ·  SIH26170  ·  ISRO / Department of Space", { size: 16, color: NAVY, bold: true }),
            ],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            border: { top: { style: BorderStyle.SINGLE, size: 6, color: RULE, space: 8 } },
            spacing: { before: 80 },
            children: [
              r("Technical Design & Implementation Report", { size: 16, color: MUTED }),
              r("    |    Page ", { size: 16, color: MUTED }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: MUTED }),
            ],
          })],
        }),
      },
      children: [
        // COVER
        new Paragraph({ spacing: { before: 400 }, children: [r("SMART INDIA HACKATHON 2026", { size: 20, bold: true, color: GOLD })] }),
        new Paragraph({ spacing: { before: 80, after: 80 }, children: [r("Problem SIH26170  ·  Theme: Smart Automation  ·  Category: Software", { size: 20, color: MUTED })] }),
        new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 20, color: NAVY, space: 4 } },
          spacing: { before: 400, after: 280 },
          children: [r("AETHER", { size: 64, bold: true, color: NAVY })],
        }),
        p("Adaptive ESS Thermal Health & Early Reject", { size: 32, color: NAVY, after: 80 }),
        p("A complete technical account of the electronics, software, and machine-learning work behind an AI-driven burn-in screening system for high-reliability (space-grade) electronic components.", { size: 22, color: MUTED, after: 400 }),
        kvTable([
          ["Full title", "AI-Driven Anomaly Detection in Component Burn-In & Screening"],
          ["Organisation", "Indian Space Research Organisation (ISRO) / Department of Space"],
          ["System name", "AETHER — Adaptive ESS Thermal Health & Early Reject"],
          ["Document type", "Technical design and implementation report"],
          ["Date", "7 September 2026"],
          ["Scope", "Electronics reliability · software architecture · ML models · evaluation · QA workstation"],
        ]),
        gap(),
        p("This document explains everything that was built: why burn-in exists in space electronics, why static datasheet limits fail, how Module A (dynamic outliers) and Module B (24 h → 168 h drift prediction) work, how the software is structured, how the models are trained and explained to a QA inspector, and what the held-out results are.", { after: 200 }),

        new Paragraph({ children: [new PageBreak()] }),
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "Contents", font: "Arial", size: 32, bold: true, color: NAVY })] }),
        p("Right-click the field below in Microsoft Word and choose Update Field to refresh page numbers.", { size: 18, italics: true, color: MUTED }),
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),

        // 1
        h1("1.  Executive summary"),
        p("Traditional environmental stress screening (ESS) of space-grade parts uses static parametric pass/fail limits taken from a datasheet. That catches obvious failures. It does not catch latent defects: components that remain inside the data-book box but sit far from their own manufacturing lot, or that drift on a slope no healthy part in the lot would take. Those parts pass screening, fly, and become infant-mortality failures in a payload."),
        p("AETHER is a software system built for SIH26170. After 24 hours of powered burn-in at elevated temperature, it looks at three time-series parameters — standby current (IDDQ), leakage current, and propagation delay — and does two things the problem statement asks for:"),
        bullet("Module A — a dynamic, lot-relative outlier detector. If a lot’s leakage centroid is 10 µA, a part at 45 µA is rejected even when the datasheet maximum is 50 µA."),
        bullet("Module B — a regression model that sees only the 0 h and 24 h readings, forecasts the hidden 168 h value, and flags the part if the implied drift exceeds a safety slope learned from healthy silicon."),
        p("The two modules are fused into a three-way QA decision a human can read: PASS (finish the remaining burn-in), HOLD (extra 96 h readout), or REJECT (pull from the chamber now). Flight parts that look healthy still complete 168 h. Chamber time is recovered only when a doomed part is pulled at 24 h."),
        p("On lots the model never trained on, AETHER caught 102 / 102 latent defects (100% recall, zero false negatives). A static 24 h datasheet screen would have missed all 102. Early REJECT precision was 98.7%. The 168 h forecasts beat linear extrapolation on every parameter. The textbook example from the problem statement — lot ≈ 10 µA, part 45.32 µA, datasheet 50 µA — is static PASS and dynamic REJECT, with an inspector brief in engineering English."),

        h2("1.1 What was delivered"),
        table(
          ["Deliverable", "What it is"],
          [
            ["ML pipeline", "Lot-aware PAT + Isolation Forest + Mahalanobis; Ridge / HGB 168 h forecast"],
            ["Decision engine", "PASS / HOLD / REJECT with two-signal reject rule and recall-first thresholds"],
            ["Explainability", "Static vs dynamic verdict, robust z-scores, safety slope, Ridge waterfall"],
            ["Synthetic lots", "Physics-informed 125 °C ageing with mavericks, latent drift, and runaway"],
            ["QA workstation", "Streamlit dashboard at localhost:8501 (lot board, inspector, judging rubric)"],
            ["Tests & metrics", "PAT unit test, held-out-lot smoke test, scripts/evaluate.py"],
            ["This report", "Electronics, software, and ML written up for judges and engineering faculty"],
          ],
          [2600, 6426],
        ),

        // 2
        h1("2.  Problem statement and how AETHER maps to it"),
        h2("2.1 The official statement"),
        p("Organisation: ISRO / Department of Space. Category: Software. Theme: Smart Automation. Problem code: SIH26170."),
        p("Background. In high-reliability sectors such as space, electronic components undergo rigorous environmental stress screening, including burn-in: operating parts at elevated temperature (for example 125 °C) for extended periods. Traditional screening relies on static parametric pass/fail limits. Latent defects — parts that pass those absolute limits but show subtle, anomalous drift over time — often escape into final payloads and cause catastrophic field failures."),
        p("Required work. A predictive machine-learning model that analyses time-series parametric data (standby current IDDQ, leakage currents, or propagation delays) measured at intervals such as 0 h, 24 h, 96 h, and 168 h, to detect anomalous components."),
        h3("Module A — the outlier detection system"),
        p("Static limits catch obvious failures. Participants must develop a dynamic outlier system. If a lot has an average leakage current of 10 µA, a part showing 45 µA is a massive anomaly even if the datasheet maximum is 50 µA."),
        h3("Module B — time-series drift predictor"),
        p("Build a predictive regression model that takes Value_0h and Value_24h as inputs and forecasts Value_168h. If the predicted 168 h drift rate exceeds a calculated safety slope, the system flags the component for early rejection."),
        h3("Evaluation metrics"),
        table(
          ["Official metric", "How AETHER treats it"],
          [
            ["Anomaly detection score", "False negatives are catastrophic. Thresholds require ≥ 97% recall first, then maximise precision. Detection = anything other than PASS."],
            ["Drift prediction accuracy", "Mean absolute error of predicted Value_168h against hidden ground truth. 168 h is never an input at inference."],
            ["Explainability", "Every call is justified: lot z-score, PAT hit, safety slope, Ridge contributions, static vs dynamic verdict in inspector English."],
          ],
          [2800, 6226],
        ),

        h2("2.2 Requirement-to-implementation traceability"),
        table(
          ["Requirement", "Implementation"],
          [
            ["Time series at 0 / 24 / 96 / 168 h", "All four stored. Early gate uses only 0 h and 24 h. 96 h is the HOLD confirmation point. 168 h is the hidden target."],
            ["IDDQ, leakage, tpd", "Three parameters, each with datasheet caps 50 µA, 50 µA, 10 ns"],
            ["Dynamic outliers vs lot", "Robust PAT: median + 6 × 1.4826 × MAD, AEC-Q001 style, computed inside the lot"],
            ["10 µA vs 45 µA vs 50 µA", "Pinned lot LOTSIH, part LOTSIH-0045. Static PASS, dynamic REJECT, z ≈ 35"],
            ["0 h + 24 h → 168 h", "Module B Ridge + histogram gradient boosting blend; linear extrapolation is the baseline"],
            ["Safety slope early reject", "Healthy 95th-percentile 0→168 h slope from training lots, with 1.5× margin"],
            ["QA inspector, not a black box", "src/explain.py + Streamlit inspector + Ridge waterfall"],
          ],
          [2800, 6226],
        ),

        // 3 EC
        h1("3.  Electronics and reliability engineering considerations"),
        p("This section is the EC (electronics) rationale. The machine-learning choices only make sense if the device physics and the screening standards are stated first."),

        h2("3.1 Why space electronics cannot use commercial screening"),
        p("A consumer gadget can be warrantied and replaced. A satellite cannot. Once a launch vehicle has put a payload on orbit, a latent defect in a regulator, a memory, or a gate array is a mission failure. High-reliability programmes therefore spend chamber time before integration to force infant-mortality failures on the ground rather than on orbit."),
        p("The relevant industrial language is environmental stress screening (ESS) and burn-in. ESS is a production screen. It is not a design-qualification test such as HALT, and it is not a life test such as HTOL. Its job is to precipitate latent manufacturing and process defects in a specific lot of parts, then remove those parts, without consuming a meaningful fraction of the useful life of the good ones."),

        h2("3.2 The bathtub curve and what burn-in is for"),
        p("Electronic failure rate versus time is classically drawn as a bathtub: a falling infant-mortality region, a low random-failure floor, and a rising wear-out region. Burn-in is aimed at the left side of that curve. Weak die, contaminated interfaces, poorly formed contacts, and gate-oxide defects fail early when they are biased and hot. After those parts are removed, the remaining population is closer to the useful-life floor."),
        p("If screening is too mild, defectives escape (false negatives — catastrophic for ISRO). If screening is too harsh or too long, good parts are damaged or useful life is consumed. AETHER does not change the thermal profile of the chamber. It changes who occupies a slot after 24 h, and it changes which parts a QA inspector is asked to look at."),

        h2("3.3 Temperature, time, and the 125 °C / 168 h cadence"),
        p("MIL-STD-883 Test Method 1015 (burn-in) and the Class Q / Class V flows in MIL-PRF-38535 typically specify 160 hours at 125 °C, with time-temperature regression allowed when activation energy is known. The problem statement’s 0 h, 24 h, 96 h, and 168 h readouts are the practical measurement cadence of that flow: initial electricals, an early in-process readout, a mid-screen readout, and the end-of-burn-in electricals."),
        p("Acceleration with temperature is Arrhenius in spirit. For many silicon failure mechanisms,"),
        p("AF = exp[(Ea / k) × (1/Tuse − 1/Tstress)]", { italics: true, align: AlignmentType.CENTER }),
        p("where Ea is activation energy, k is Boltzmann’s constant, and T is absolute temperature. Raising junction temperature from a 55 °C use condition to a 125 °C chamber is a large acceleration. AETHER does not estimate Ea. It treats the chamber as given and asks a narrower question: given two early readouts on this part, in this lot, is the trajectory already unlike healthy silicon?"),

        h2("3.4 Why these three parameters"),
        p("The problem names three families of measurement. Each is a different window into silicon health."),
        table(
          ["Parameter", "What it physically is", "Why it moves in burn-in"],
          [
            ["IDDQ (standby current)", "Quiescent VDD current with the part in a defined idle / sleep vector. Measured in µA.", "Bridging, subthreshold leakage, and some gate-oxide defects raise IDDQ. Ageing (NBTI / HCI) slowly increases it even in healthy CMOS."],
            ["Leakage current", "Reverse or pin leakage of a junction, ESD structure, or analog path. Measured in µA.", "Surface contamination, junction damage, and ionic drift show up as excess leakage. Lot centroids sit far below the datasheet cap."],
            ["Propagation delay (tpd)", "Input-to-output delay of a timing path. Measured in ns.", "Hot-carrier and NBTI slow MOSFETs. Delay creeps up. A part whose delay walks much faster than the lot is ageing abnormally."],
          ],
          [2200, 3413, 3413],
        ),
        caption("Table. Parameters used by AETHER, mapped to device physics."),
        p("Datasheet caps in the current build are 50 µA (IDDQ), 50 µA (leakage — aligned to the problem’s 50 µA example), and 10 ns (tpd). Leakage and IDDQ are one-sided (only high is bad). Delay is two-sided in PAT because both unusually fast and unusually slow parts can be process mavericks, though ageing itself is a positive drift."),

        h2("3.5 Static datasheet limits versus lot-relative PAT"),
        p("A datasheet maximum is a guarantee the manufacturer is willing to print for every lot, every process corner, over the full temperature range. It is deliberately loose. Fast silicon in a given wafer lot can have a leakage centroid of 14 µA; slow silicon in the next lot can sit at 7 µA. Both lots are legal against a 50 µA cap. Inside one lot, a 45 µA part is not “a bit leaky”. It is a statistical alien."),
        p("Automotive and space screening already have a name for this idea: Part Average Testing (PAT), documented in AEC-Q001 and used in dynamic PAT (DPAT) on testers. Robust PAT replaces mean and standard deviation with median and MAD (median absolute deviation), because the outliers you are trying to find would otherwise inflate sigma and hide themselves:"),
        p("σrobust = 1.4826 × median(|xi − median(x)|)", { italics: true, align: AlignmentType.CENTER }),
        p("PAThi = median + k × σrobust,   k = 6 in AETHER (AEC-style six-sigma PAT)", { italics: true, align: AlignmentType.CENTER }),
        p("For leakage and IDDQ the test is one-sided (upper only). A part with z = (x − median) / σrobust greater than 6 is a PAT fail even if x is still below the datasheet."),
        p("This is exactly Module A as the problem describes it. The 10 µA / 45 µA / 50 µA sentence is not a metaphor. It is PAT."),

        h2("3.6 Worked example — LOTSIH-0045"),
        p("A dedicated lot, LOTSIH, was injected so the problem’s numbers exist as a real row in the system, not only as a slide."),
        table(
          ["Quantity", "Value"],
          [
            ["Lot", "LOTSIH (200 parts, nominal process corner)"],
            ["Lot leakage median", "10.14 µA"],
            ["Part", "LOTSIH-0045"],
            ["Leakage at 24 h", "45.32 µA"],
            ["Datasheet maximum", "50.00 µA"],
            ["Static screen", "PASS (45.32 < 50)"],
            ["Robust z versus lot", "35.0 σ"],
            ["Dynamic screen", "REJECT"],
          ],
          [3600, 5426],
        ),
        caption("Table. The SIH26170 textbook maverick, as measured in AETHER."),
        p("A QA inspector reading the brief sees: “Leakage current at 24 h is 45.32 µA — 35.0 robust σ above the lot median (10.14 µA). Datasheet max is 50.00 µA, so a static screen would miss this maverick.” That sentence is the entire point of Module A."),

        h2("3.7 Failure modes the generator and the models must see"),
        p("Not every latent defect looks like a maverick sitting at 45 µA. Three modes were built into the synthetic lots because they are the modes a 24 h readout can actually reveal."),
        table(
          ["Mode", "0 h appearance", "24 h appearance", "168 h fate"],
          [
            ["Maverick", "Offset 3–6 σ from the lot, still inside the datasheet", "Still offset; slope may be healthy", "Often still in-spec. Static screen never sees it. PAT does."],
            ["Latent drift (walker)", "Looks like the lot", "Small excess slope, easy to miss by eye", "High versus lot; may still be under the datasheet. Module B’s job."],
            ["Runaway", "Near the lot", "Mild; quadratic term not obvious yet", "Accelerating. Static limits catch it late. Early forecast should catch it."],
          ],
          [1800, 2408, 2409, 2409],
        ),
        p("Healthy ageing at 125 °C is modelled as a slow, nearly linear relative increase plus measurement noise comparable to a parametric analyser. Defective ageing adds a larger linear coefficient and, for runaways, a quadratic term. That is not a full compact model of NBTI. It is a screening-faithful caricature: good parts move together; bad parts leave the pack."),

        h2("3.8 Process corners, dirty lots, and why splits are by lot"),
        p("Fast, nominal, and slow process corners shift the entire lot centroid. A global Isolation Forest trained on raw microamps would call a healthy fast lot “leaky” and a healthy slow lot “quiet”. AETHER therefore computes robust z-scores inside the lot and feeds those z-scores to Isolation Forest and Mahalanobis. A fast lot is allowed to be a fast lot."),
        p("A few lots are generated “dirty” (higher defect rate) to mimic a process excursion. Training, validation, and test are split by lot_id, not by part_id. Scoring a part from a lot whose neighbours were in the training set would leak the process corner and overstate generalisation. PAT itself is always recomputed on the lot under test — that is unsupervised and lot-local, which is how a real tester does DPAT."),

        h2("3.9 What AETHER deliberately does not do"),
        bullet("It does not replace burn-in. PASS means finish the remaining hours. Only REJECT frees the slot."),
        bullet("It does not set chamber temperature, bias vectors, or dwell. Those stay with the ESS procedure."),
        bullet("It does not claim radiation hardness. TID and SEE are a different qualification path."),
        bullet("It does not use flight telemetry. ISRO burn-in ATE logs are not public, so the lots are physics-informed synthetics with the same column contract as a future ATE export."),
        p("Those boundaries matter for an EC viva. The system is a screening intelligence layer on top of an existing 125 °C powered burn-in, not a substitute for the chamber or for QML flow."),

        // 4 overview
        h1("4.  System overview"),
        p("AETHER is a Python pipeline plus a Streamlit QA workstation. The operational sequence after a 24 h readout is:"),
        num("Load the lot’s 0 h and 24 h measurements for IDDQ, leakage, and tpd."),
        num("Compute lot-robust median, MAD, PAT limits, slopes, and z-scores (feature layer)."),
        num("Module A scores the part: PAT hits, Isolation Forest, Mahalanobis. Combined outlier_score."),
        num("Module B, using only 0 h and 24 h, predicts 168 h for each parameter and compares the implied slope with the safety slope."),
        num("Fusion: PASS, HOLD, or REJECT, with a written reason list."),
        num("Explain: static vs dynamic verdict, inspector brief, Ridge waterfall."),
        p("96 h and 168 h exist in the dataset so Module B can be trained and scored, and so HOLD has a defined confirmation readout. They are not inputs at the 24 h gate."),

        h2("4.1 The three decisions"),
        table(
          ["Decision", "Meaning for QA", "Chamber consequence"],
          [
            ["PASS", "Lot-relative parameters and predicted drift are inside the envelope.", "Continue to 168 h as planned. No hours claimed back."],
            ["HOLD", "Not a clean pass, not yet a confident scrap. Borderline score or a single weak signal.", "Stay in the chamber; extra readout at 96 h."],
            ["REJECT", "Two views agree: high fused score and (PAT hit or unsafe predicted drift).", "Pull at 24 h. 144 h of slot time recovered."],
          ],
          [1800, 4213, 3013],
        ),
        p("A two-class scrap/release policy is the wrong shape for space-grade silicon. False negatives are catastrophic; false scraps are also expensive. HOLD exists on purpose."),

        // 5 software
        h1("5.  Software architecture"),
        h2("5.1 Stack"),
        table(
          ["Layer", "Choice", "Why"],
          [
            ["Language", "Python 3.13", "Scientific stack, readable for a hackathon jury"],
            ["Tabular / numeric", "pandas, NumPy", "Lot grouping, feature frames"],
            ["Machine learning", "scikit-learn 1.8", "IsolationForest, MinCovDet, RidgeCV, HistGradientBoostingRegressor — all inspectable"],
            ["Persistence", "joblib", "Save the trained ScreeningBundle"],
            ["QA UI", "Streamlit + Plotly", "Dark workstation a judge can drive in a demo"],
            ["Tests", "pytest", "PAT example + held-out recall smoke"],
          ],
          [2000, 2800, 4226],
        ),
        p("No deep-learning framework is required at inference. That is intentional. A burn-in host PC should run this without a GPU, and a QA engineer should be able to audit a Ridge coefficient. Histogram gradient boosting is used only in Module B, and only when it reduces validation MAE; Ridge stays in the loop for the waterfall explanation."),

        h2("5.2 Repository layout"),
        table(
          ["Path", "Role"],
          [
            ["app.py", "Streamlit QA workstation (lot board, inspector, judging rubric, methodology)"],
            ["scripts/train.py", "Generate lots, train, write models/metrics.json and data/screening_results.csv"],
            ["scripts/evaluate.py", "Print the three official SIH metrics plus the LOTSIH-0045 brief"],
            ["src/config.py", "Times, datasheet caps, PAT k, costs, recall floor"],
            ["src/generate_data.py", "Physics-informed lot generator + textbook LOTSIH"],
            ["src/features.py", "Robust centre/scale, PAT limits, lot-relative z, early matrix, drift features"],
            ["src/module_a.py", "PAT flags, Isolation Forest, robust Mahalanobis, fused outlier_score"],
            ["src/module_b.py", "Per-parameter Ridge + HGB blend, safety slope, 168 h prediction"],
            ["src/decisions.py", "Threshold calibration and PASS/HOLD/REJECT fusion"],
            ["src/explain.py", "Inspector English, static vs dynamic, Ridge contributions"],
            ["src/pipeline.py", "Lot-grouped splits, train_bundle, apply_models"],
            ["src/metrics.py", "Recall/FN, latent catch rate, MAE vs hidden 168 h"],
            ["tests/", "Textbook 10 vs 45 vs 50 PAT test; end-to-end held-out recall"],
            ["data/", "burnin_parts.csv, screening_results.csv"],
            ["models/", "screening_bundle.joblib, metrics.json"],
          ],
          [2800, 6226],
        ),

        h2("5.3 End-to-end training pipeline"),
        num("Generate (or load) lot-structured CSV with 0/24/96/168 h for three parameters, defect labels, datasheet caps.", "numbers2"),
        num("Split lots with GroupShuffleSplit: ~50% train lots, ~20% val lots, ~25% test lots. No part from a test lot is seen in training.", "numbers2"),
        num("On each split, compute lot statistics from that split’s own parts (PAT must not peek at another lot).", "numbers2"),
        num("Fit Isolation Forest and MinCovDet on training lots’ early feature matrix.", "numbers2"),
        num("Fit three drift models (IDDQ, leakage, tpd) on training lots; pick Ridge/HGB blend on validation MAE.", "numbers2"),
        num("Learn safety slopes as the 95th percentile of healthy 0→168 h slopes on training lots.", "numbers2"),
        num("Calibrate t_hold as the highest score cut that still meets 97% recall on validation; t_rej sits above it.", "numbers2"),
        num("Apply the frozen bundle to validation and test lots. Write metrics and per-part decisions.", "numbers2"),
        p("apply_models() is the same function the dashboard uses for the what-if slider. Training and live scoring cannot drift apart."),

        h2("5.4 Data contract (ATE-shaped columns)"),
        p("A future ISRO ATE export can replace data/burnin_parts.csv if it uses the same names. No other code has to change."),
        table(
          ["Column family", "Examples"],
          [
            ["Identity", "part_id, lot_id, process_corner, lot_quality"],
            ["Parameters × time", "iddq_0h, iddq_24h, iddq_96h, iddq_168h (same for ileak, tpd)"],
            ["Datasheet", "datasheet_iddq_max, datasheet_ileak_max, datasheet_tpd_max"],
            ["Labels (training / scoring)", "defect_type, is_defective, static_fail, latent_escape, sih_example"],
          ],
          [2800, 6226],
        ),
        p("Labels are for training and for scoring the synthetic world. In production the model would run unsupervised / weakly supervised on the current lot’s PAT plus a drift model frozen from historical lots. The code path is the same; only the label columns go unused."),

        h2("5.5 QA workstation"),
        p("app.py is a four-tab Streamlit app with a dark ISRO-style theme (.streamlit/config.toml)."),
        bullet2("Lot board — pie of PASS/HOLD/REJECT, 0 h vs 24 h scatter coloured by decision, sortable part table."),
        bullet2("QA inspector — defaults to LOTSIH-0045. Static vs dynamic banners, reason bullets, three time-series with predicted 168 h and safety envelope, Ridge waterfalls, copy-paste inspector brief, what-if slider on the 24 h reading."),
        bullet2("Judging rubric — the three official metrics on held-out lots, plus the textbook brief."),
        bullet2("Methodology — PAT, early reject, three-way decisions, lot-out splits."),
        p("The dashboard loads precomputed screening_results.csv so a demo starts in seconds. If artefacts are missing it trains on first run."),

        // 6 data
        h1("6.  Physics-informed synthetic lots"),
        p("Real ISRO screening logs are not a public dataset. Inventing unstructured random numbers would not stress Module A or Module B the way a lot does. src/generate_data.py therefore builds lots the way a wafer probe would: a process corner, a centroid, a within-lot spread, measurement noise, and a small injected defective subpopulation."),

        h2("6.1 Healthy ageing law"),
        p("For a parameter value v at time t hours in the 125 °C chamber:"),
        p("v(t) = v0 × (1 + a·t + b·t²) + ε", { italics: true, align: AlignmentType.CENTER }),
        p("Healthy parts: a is small (order 3×10⁻⁴ per hour, a few percent over 168 h), b ≈ 0, ε is Gaussian analyser noise (0.16 µA IDDQ, 0.09 µA leakage, 0.025 ns tpd). Values are clipped positive. This produces a tight lot cloud that slowly walks together — which is what PAT needs, and what a drift model should treat as the safety envelope."),

        h2("6.2 How defectives are injected"),
        table(
          ["Mode", "How v0, a, b are changed"],
          [
            ["Maverick", "v0 multiplied into the 3–4.6× range, then capped under 92% of the datasheet so the part remains a static pass"],
            ["Latent drift", "v0 stays with the lot; a is raised to ~0.002–0.004 / h so 168 h is a lot outlier but often still in-spec"],
            ["Runaway", "a moderately raised and b set to ~10⁻⁵ so curvature appears late; 24 h still looks almost healthy"],
          ],
          [2400, 6626],
        ),
        p("Clean lots inject about 7% defectives; dirty lots about 18%. Across 24 generated lots plus LOTSIH, the current CSV holds 5,145 parts. Every defective in the held-out test lots still passes the datasheet at 24 h by construction of the interesting cases — that is the population static screening cannot save."),

        h2("6.3 Textbook lot"),
        p("textbook_maverick_lot() appends LOTSIH: 199 healthy parts centred at 10 µA leakage, and index 44 forced to 45.00 / 45.32 / 45.90 / 46.55 µA at 0/24/96/168 h. IDDQ and tpd of that part stay with the lot, so the story is a pure leakage maverick — the sentence ISRO wrote."),

        // 7 Module A
        h1("7.  Module A — dynamic outlier detection (ML)"),
        p("Module A answers: is this part strange relative to its lot, using only 0 h and 24 h? It fuses three views so no single brittle rule owns the call."),

        h2("7.1 Features"),
        p("For each of IDDQ, leakage, and tpd the early matrix contains:"),
        bullet2("Raw 0 h and 24 h values (absolute scale, useful for Isolation Forest once robust-scaled)."),
        bullet2("Lot-relative z at 0 h and 24 h: z = (x − lot median) / lot σrobust."),
        bullet2("Early slope (v24 − v0) / 24, relative change (v24 − v0) / v0, and the z of that slope versus the lot’s slope distribution."),
        p("Twenty-one columns. Isolation Forest sees all of them after a RobustScaler. Mahalanobis sees only the z columns, which are already lot-normalised and much better conditioned than a mix of microamps and nanoseconds."),

        h2("7.2 Robust PAT"),
        p("PAT is the interpretable backbone. For each parameter and time, and for the 24 h slope, a hit is z > 6 (upper) or |z| > 6 (two-sided delay). Hits are listed as reasons (“PAT ileak@24h z=35.02”). pat_score is the sum of clipped z/6 contributions so a part that is 20 σ on one pin outranks a part that is 6.1 σ on one pin. This is the component a QA engineer can recompute with a spreadsheet."),

        h2("7.3 Isolation Forest"),
        p("Isolation Forest (400 trees, contamination 0.06, fixed seed) is unsupervised. It isolates points that need few random splits — multivariate mavericks that may not trip any single PAT limit but are jointly odd (high leakage and high delay together, for example). Scores are min-max normalised so they can be blended with PAT and Mahalanobis. The forest is trained on training lots only; a new lot is scored, not refit, except that its z-features were computed from its own median/MAD."),

        h2("7.4 Robust Mahalanobis"),
        p("MinCovDet (Minimum Covariance Determinant) estimates a robust covariance of the z-vector, then Mahalanobis distance flags parts outside the lot ellipsoid. If MinCovDet fails to converge (singular covariance on a tiny lot), the code falls back to EmpiricalCovariance. Distances are scaled by 4p and clipped so they sit on a 0–1-ish scale with the other two scores."),

        h2("7.5 Fusion inside Module A"),
        p("outlier_score = 0.40 × PAT_norm + 0.35 × IsolationForest + 0.25 × Mahalanobis", { italics: true, align: AlignmentType.CENTER }),
        p("PAT is weighted highest because it is the method a screening engineer already trusts and because it is the method that implements the problem’s 10 vs 45 example with no training at all. The two multivariate detectors catch shape anomalies PAT would miss. None of the three is a deep black box."),

        // 8 Module B
        h1("8.  Module B — 24 h → 168 h drift predictor (ML)"),
        p("Module B answers: if this part stays in the oven, where will it be at 168 h, and is that trajectory safe? Inputs are strictly Value_0h and Value_24h (plus features derived only from those two numbers). The 96 h and 168 h columns are labels, never features, at inference."),

        h2("8.1 Drift features"),
        table(
          ["Feature", "Definition"],
          [
            ["v0, v24", "The two allowed measurements"],
            ["delta24", "v24 − v0"],
            ["slope24", "(v24 − v0) / 24"],
            ["rel24", "(v24 − v0) / max(v0, ε)"],
            ["log v0, log v24", "Log scale; leakage is roughly log-normal across lots"],
            ["extrap_168", "v0 + (v24 − v0) × (168/24) — the physics baseline, also a feature"],
          ],
          [2400, 6626],
        ),

        h2("8.2 Models"),
        p("A linear extrapolation (constant ageing rate at fixed temperature) is the honest baseline. If Module B cannot beat it, it has no right to reject a part early."),
        p("RidgeCV (standardised features, alphas log-spaced 10⁻³ to 10³) is the primary model because every coefficient is a number in original units after inversion of the scaler. That is what the waterfall plots."),
        p("HistGradientBoostingRegressor (depth 4, learning rate 0.06, 250 iterations, L2 = 0.1) is fitted as a challenger. On validation, a blend weight w ∈ {0, 0.25, 0.4, 0.55, 0.7} is chosen to minimise MAE. In the current fit w = 0.7 for all three parameters: boosting wins on accuracy, Ridge remains available for explanation. The reported prediction is (1 − w)·Ridge + w·HGB."),
        p("One model is fitted per parameter. Leakage physics is not delay physics; sharing weights would be theatre."),

        h2("8.3 Safety slope and early-reject flags"),
        p("From healthy training parts, the 0→168 h slope distribution is taken and the 95th percentile becomes safety_slope. At inference:"),
        p("predicted_slope = (pred_168 − v0) / 168", { italics: true, align: AlignmentType.CENTER }),
        p("exceeds_safety if predicted_slope > 1.5 × safety_slope", { italics: true, align: AlignmentType.CENTER }),
        p("exceeds_datasheet if pred_168 > 0.90 × datasheet_max", { italics: true, align: AlignmentType.CENTER }),
        p("The 1.5× margin avoids rejecting every part that is merely in the healthy tail. The 90% datasheet trip is a conservative early warning: if the forecast is already near the cap at 24 h of evidence, waiting 144 more hours only occupies a slot."),

        h2("8.4 Held-out MAE versus the baseline"),
        table(
          ["Parameter", "Module B MAE", "Linear-extrap MAE", "Ratio"],
          [
            ["IDDQ", "0.51 µA", "1.26 µA", "2.5× better"],
            ["Leakage", "0.31 µA", "0.72 µA", "2.4× better"],
            ["Propagation delay", "0.066 ns", "0.193 ns", "2.9× better"],
          ],
          [2400, 2208, 2209, 2209],
        ),
        caption("Table. Held-out lots. 168 h values were hidden from the model."),

        // 9 decisions
        h1("9.  Decision fusion — PASS, HOLD, REJECT"),
        p("A high Module A score or a Module B safety-slope flag is not yet a scrap ticket. Fusion implements a two-signal reject rule so a lone Isolation Forest twitch cannot kill a flight part."),

        h2("9.1 Score and rule"),
        p("fused_score = outlier_score + 0.18 × 1{any safety or datasheet forecast flag}", { italics: true, align: AlignmentType.CENTER }),
        p("Then:"),
        bullet2("REJECT if fused_score ≥ t_rej AND (PAT hit OR drift flag). Two views must agree."),
        bullet2("HOLD if fused_score ≥ t_hold, or there is a drift flag, or there is a PAT hit, but the reject conjunction is not met."),
        bullet2("PASS otherwise: continue 168 h."),
        p("Hours saved = 144 only on REJECT; 0 on PASS and HOLD. That is an honest chamber metric. We do not pretend that a PASS skips burn-in."),

        h2("9.2 Threshold calibration"),
        p("On the validation lots, t_hold is chosen as the highest score cut that still achieves at least 97% recall (MIN_RECALL). Among cuts that meet that floor, precision of “flagged versus PASS” is maximised. t_rej is a higher quantile of the scores above t_hold. If 97% is infeasible, the floor relaxes to 93%, 88%, then 80% rather than silently returning a dummy pair."),
        p("This matches the official metric language: missing a defective part is catastrophic, so recall is the constraint; precision is the objective under that constraint. Current frozen thresholds: t_hold ≈ 0.40, t_rej ≈ 0.68."),

        h2("9.3 Cost picture (for EC / QA, not for training the trees)"),
        p("A screening-cost helper still exists in code (FN = 1000, scrap of a good part = 12, HOLD of a good part = 2, HOLD of a defective = 40). It documents the asymmetry even though the live calibrator is the recall-then-precision rule above. The numbers are not rupees; they are a reminder that an escaped defective in a payload is two orders of magnitude worse than a wasted chamber slot."),

        // 10 explain
        h1("10.  Explainability — justifying the call to a QA inspector"),
        p("The third official metric is not optional. A black-box “anomaly = 0.83” is useless at a screening desk. src/explain.py builds a card per part."),

        h2("10.1 Static versus dynamic"),
        p("For each parameter the inspector sees both verdicts in one sentence: the 24 h value versus the datasheet (STATIC PASS/FAIL) and the same value versus the lot median and robust z (lot outlier / elevated / in-lot). For LOTSIH-0045 the banner is static PASS, dynamic REJECT. That screenshot is the demo."),

        h2("10.2 Reason bullets, ordered"),
        p("PAT / lot-relative bullets are listed before predicted-drift bullets, so a maverick is explained as a maverick, not as a secondary forecast footnote. Example: “Leakage current at 24 h is 45.32 µA — 35.0 robust σ above the lot median (10.14 µA). Datasheet max is 50.00 µA, so a static screen would miss this maverick.”"),

        h2("10.3 Ridge waterfall"),
        p("For each parameter, ridge_contributions() multiplies standardised features by Ridge coefficients and reports additive contributions in the original units (µA or ns), plus intercept. Plotly draws a waterfall from intercept through 0 h, 24 h, slope, logs, and linear extrap, ending at the Ridge 168 h prediction. The inspector can see which early reading pushed the forecast. Histogram boosting may dominate the numeric MAE; it is not allowed to be the only story."),

        h2("10.4 Inspector brief"),
        p("A single paragraph is generated for the lot traveller: part id, lot, decision, headline action, and the first two technical reasons. It is copy-pasteable from the dashboard. scripts/evaluate.py prints the LOTSIH-0045 brief so a jury does not even need the UI."),

        h2("10.5 What-if"),
        p("The inspector can drag the 24 h reading. Lot median and sigma stay put (they belong to the lot, not the part). Slope, relative change, and z are recomputed, apply_models() is run on that one row, and the new decision is shown. This is how a QA engineer tests “what if the 24 h leakage had been 12 µA instead of 45 µA?” — the call flips, which is the definition of a lot-relative screen."),

        // 11 eval
        h1("11.  Evaluation protocol and results"),
        h2("11.1 Protocol"),
        bullet2("Unit of split: lot, not part. GroupShuffleSplit, seed 42."),
        bullet2("Positive class for detection: is_defective. Predicted positive: decision ≠ PASS (HOLD and REJECT both count as caught, because HOLD is “do not release”)."),
        bullet2("False negative: defective part that received PASS. This is the catastrophic cell."),
        bullet2("Latent escape: defective AND never crossed a datasheet cap. Catching these is the whole problem."),
        bullet2("Static baseline: flag if any 24 h value exceeds its datasheet max. On the test lots this baseline missed every defective."),
        bullet2("Drift MAE: mean |pred_168 − true_168| on held-out lots, compared with linear extrapolation."),
        bullet2("Reject precision: among REJECT calls, fraction that were truly defective. This is the scrap-quality number."),

        h2("11.2 Held-out lot results (current frozen bundle)"),
        table(
          ["Metric", "Train lots", "Val lots", "Test lots"],
          [
            ["Parts", "2,478", "1,218", "1,449"],
            ["Defectives", "205", "94", "102"],
            ["Recall", "100%", "100%", "100%"],
            ["False negatives", "0", "0", "0"],
            ["Latent catch rate", "100%", "100%", "100%"],
            ["Static 24 h misses", "205", "94", "102"],
            ["PASS / HOLD / REJECT", "2,055 / 297 / 126", "982 / 170 / 66", "1,172 / 202 / 75"],
            ["REJECT precision", "100%", "100%", "98.7%"],
            ["Chamber hours recovered", "18,144", "9,504", "10,800"],
          ],
          [2800, 2075, 2075, 2076],
        ),
        caption("Table. Detection. HOLD counts as caught. Hours recovered are 144 × (number of REJECTs)."),
        p("Detection precision of HOLD+REJECT together is lower than REJECT precision (about 37% on test) because HOLD is a wide review queue. That is acceptable under the official metric: the catastrophic cell is FN, which is empty, and the expensive scrap cell is REJECT, which is 98.7% clean. HOLD parts still finish burn-in with extra attention."),

        h2("11.3 Drift MAE on test lots"),
        table(
          ["Parameter", "Model MAE", "Healthy-only MAE", "Linear extrap MAE"],
          [
            ["IDDQ (µA)", "0.507", "0.339", "1.259"],
            ["Leakage (µA)", "0.306", "0.218", "0.724"],
            ["tpd (ns)", "0.066", "0.049", "0.193"],
          ],
          [2400, 2208, 2209, 2209],
        ),
        p("Healthy-only MAE is tighter, as expected: walkers and runaways are harder to forecast, and they are the parts Module B is supposed to flag rather than fit perfectly."),

        h2("11.4 Automated tests"),
        bullet2("test_pat_flags_maverick_inside_datasheet — a toy lot at 10 µA, part at 45 µA, datasheet 50 µA: PAT high limit is below 45."),
        bullet2("test_textbook_lot_is_static_pass_dynamic_fail — LOTSIH-0045 is under the datasheet and PAT-hits with z > 6."),
        bullet2("test_end_to_end_high_recall_on_held_out_lots — small generated world, recall ≥ 85%, latent catch ≥ 80%, MAE caps."),
        bullet2("test_dataset_contains_latent_escapes — generator produces all three defect modes plus LOTSIH."),
        p("pytest: 4 passed."),

        // 12 how to run
        h1("12.  How to build, train, and run"),
        p("From the project folder (Python 3.13, packages in requirements.txt):"),
        num("python -m pip install -r requirements.txt", "runsteps"),
        num("python scripts\\train.py     (regenerates lots, trains, writes metrics)", "runsteps"),
        num("python scripts\\evaluate.py  (prints the three official scores and the textbook brief)", "runsteps"),
        num("python -m pytest -q", "runsteps"),
        num("python -m streamlit run app.py     (dashboard at http://localhost:8501)", "runsteps"),
        p("The dashboard is already running in the development environment on port 8501. First-run training takes on the order of half a minute on a laptop; subsequent opens are immediate because models/screening_bundle.joblib is on disk."),

        h2("12.1 Replacing synthetics with ATE data"),
        p("Export a CSV with the column contract in §5.4. Put it at data/burnin_parts.csv. If production data has no defect labels, is_defective can be filled false and Module A still runs (PAT + Isolation Forest are unsupervised). Module B’s safety slope then needs a historical “known-good” set, which is how a real line would freeze a golden model after a qualification lot. Retrain with python scripts\\train.py."),

        // 13 limits
        h1("13.  Limitations, risks, and future work"),
        h2("13.1 Limitations"),
        bullet2("Labels in the current numbers come from a generator, not from ISRO travellers. Absolute MAE in µA will change on real silicon; the method (lot-relative z, hidden 168 h, two-signal reject) transfers."),
        bullet2("Activation energies, bias vectors, and package thermal resistance are not modelled. The chamber is treated as a given 125 °C powered soak."),
        bullet2("HOLD is not yet a second trained classifier at 96 h; it is a decision band. A natural extension is to refit PAT at 96 h and only then PASS or REJECT."),
        bullet2("Isolation Forest contamination is a global constant. A line with a very clean process may want it lower; a dirty line, higher. PAT k = 6 is the same kind of policy knob."),
        bullet2("The HGB blend is less inspectable than Ridge. The waterfall always explains Ridge, and the dashboard states that."),

        h2("13.2 Engineering risks if this were deployed"),
        bullet2("False REJECT of a rare but valid high-leakage process corner if PAT is computed on a mixed-corner “lot” that is not actually one wafer lot. Lot identity must be real."),
        bullet2("Operator override: a QA lead must be able to force HOLD. Software should never be the last word on a Class 1 payload part without a human."),
        bullet2("Data integrity: a swapped 0 h/24 h column or a mis-entered unit (nA vs µA) would look like a lot excursion. A production version needs unit checks and duplicate-serial checks before scoring."),

        h2("13.3 Future work"),
        bullet2("Ingest a real ATE STDF or CSV from a screening house and freeze PAT k / safety slope on that product."),
        bullet2("Wafer-map / GDBN (good die in a bad neighbourhood) as an extra Module A view when x-y coordinates exist."),
        bullet2("Per-part remaining-time recommendation (stop at 48 h vs 96 h vs 168 h) using sequential probability ratio tests, still with FN as the hard constraint."),
        bullet2("Digital traveller: write the inspector brief and waterfall into the lot’s quality record automatically."),

        // 14 conclusion
        h1("14.  Conclusion"),
        p("SIH26170 asked for two things a static datasheet screen cannot do: notice that 45 µA is absurd in a 10 µA lot, and predict 168 h from 0 h and 24 h so a bad trajectory can be pulled early. AETHER implements both, in the language of the screening floor (PAT, safety slope, traveller brief), not only in the language of a machine-learning paper."),
        p("Electronics first: burn-in at 125 °C exists to buy infant-mortality failures on the ground; datasheet caps are too wide for lot screening; robust lot-relative limits are already an AEC/space idea; IDDQ, leakage, and delay are the right observables; healthy parts still finish 168 h."),
        p("Software second: a small Python pipeline with a frozen bundle, lot-grouped splits, a Streamlit inspector, and tests that encode the 10 / 45 / 50 example."),
        p("Machine learning third: PAT + Isolation Forest + Mahalanobis for Module A; Ridge + HGB with a linear-extrap baseline for Module B; recall-first thresholds; two-signal REJECT; explanations a QA inspector can argue with."),
        p("On unseen lots the catastrophic cell is empty (0 false negatives / 102 latent defects), REJECT is 98.7% clean, and every 168 h forecast beats extrapolation. The textbook part is static PASS and dynamic REJECT. That is the system."),

        // appendix
        h1("Appendix A  —  Glossary"),
        table(
          ["Term", "Meaning in this project"],
          [
            ["ESS", "Environmental stress screening — production screen, not design qualification"],
            ["Burn-in", "Powered high-temperature soak (here 125 °C) to force infant mortality"],
            ["IDDQ", "Quiescent supply current; a defect-sensitive DC test"],
            ["PAT / DPAT", "Part Average Testing / Dynamic PAT — lot-relative parametric limits"],
            ["MAD", "Median absolute deviation; robust scale, 1.4826 × MAD ≈ σ for a normal"],
            ["Maverick", "In-spec versus datasheet, off-centroid versus lot"],
            ["Latent defect", "Passes static limits, fails lot-relative or drift tests"],
            ["Safety slope", "95th percentile healthy 0→168 h drift, with 1.5× margin at inference"],
            ["HOLD", "Stay in chamber; extra 96 h readout; counts as caught for recall"],
            ["ATE", "Automatic test equipment — the host that would feed AETHER in production"],
          ],
          [2400, 6626],
        ),

        h1("Appendix B  —  Key formulae"),
        p("Robust scale:  σ = max(1.4826 × MAD, σfloor)", { after: 80 }),
        p("Robust z:  z = (x − median) / σ", { after: 80 }),
        p("PAT upper:  median + 6σ    (leakage, IDDQ); two-sided for tpd", { after: 80 }),
        p("Early slope:  (v24 − v0) / 24", { after: 80 }),
        p("Linear 168 h extrap:  v0 + (v24 − v0) × 7", { after: 80 }),
        p("Predicted slope:  (pred168 − v0) / 168", { after: 80 }),
        p("Module A score:  0.40 PAT + 0.35 IF + 0.25 Mahalanobis", { after: 80 }),
        p("Fused score:  outlier_score + 0.18 × drift_flag", { after: 200 }),

        h1("Appendix C  —  File and command cheat-sheet"),
        table(
          ["Action", "Command"],
          [
            ["Install", "python -m pip install -r requirements.txt"],
            ["Train + generate", "python scripts\\train.py"],
            ["Official metrics", "python scripts\\evaluate.py"],
            ["Tests", "python -m pytest -q"],
            ["Dashboard", "python -m streamlit run app.py"],
            ["Dashboard URL", "http://localhost:8501"],
            ["Textbook part", "LOTSIH-0045 (QA inspector tab)"],
          ],
          [2800, 6226],
        ),
        gap(),
        p("End of report. AETHER — Adaptive ESS Thermal Health & Early Reject — SIH26170.", { italics: true, color: MUTED }),
      ],
    }],
  });

  const out = path.join(__dirname, "AETHER_SIH26170_Technical_Report.docx");
  const buf = await Packer.toBuffer(doc);
  fs.writeFileSync(out, buf);
  console.log("Wrote", out);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

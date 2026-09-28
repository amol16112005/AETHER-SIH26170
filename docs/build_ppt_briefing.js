const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, LevelFormat, ImageRun, TableOfContents,
} = require("docx");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(__dirname, "AETHER_SIH26170_PPT_Briefing.docx");
const FIG = path.join(__dirname, "figures");

const PAGE_W = 11906;
const PAGE_H = 16838;
const MARGIN = 1080;
const CONTENT_W = PAGE_W - 2 * MARGIN; // 9746

const navy = "0B1020";
const accent = "0D47A1";
const headerFill = "0D47A1";
const altFill = "E8EEF6";
const thin = { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC" };
const borders = { top: thin, bottom: thin, left: thin, right: thin };

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 160, before: opts.before ?? 0, line: 276 },
    alignment: opts.align,
    children: [
      new TextRun({
        text,
        font: "Arial",
        size: opts.size ?? 22,
        bold: opts.bold,
        italics: opts.italics,
        color: opts.color,
      }),
    ],
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 280, after: 160 },
    children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: navy })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 220, after: 120 },
    children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: accent })],
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 180, after: 80 },
    children: [new TextRun({ text, font: "Arial", size: 24, bold: true, color: "1A237E" })],
  });
}

function bullets(items, ref = "bullets") {
  return items.map(
    (text) =>
      new Paragraph({
        numbering: { reference: ref, level: 0 },
        spacing: { after: 80 },
        children: [new TextRun({ text, font: "Arial", size: 22 })],
      })
  );
}

function cell(text, width, opts = {}) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    children: [
      new Paragraph({
        children: [
          new TextRun({
            text,
            font: "Arial",
            size: opts.size ?? 18,
            bold: opts.bold,
            color: opts.color || (opts.header ? "FFFFFF" : "222222"),
          }),
        ],
      }),
    ],
  });
}

function table(headers, rows, widths) {
  const head = new TableRow({
    children: headers.map((h, i) => cell(h, widths[i], { header: true, fill: headerFill, bold: true })),
  });
  const body = rows.map(
    (row, r) =>
      new TableRow({
        children: row.map((c, i) => cell(String(c), widths[i], { fill: r % 2 === 0 ? "FFFFFF" : altFill })),
      })
  );
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    rows: [head, ...body],
  });
}

function figure(file, caption, maxW = 540) {
  const buf = fs.readFileSync(path.join(FIG, file));
  // Approximate from known sizes; height computed per file below.
  const dims = {
    "pipeline.png": [1598, 716],
    "decision_donut.png": [714, 683],
    "lot_scatter.png": [1528, 913],
    "pat_histogram.png": [1492, 769],
    "aging_modes.png": [1491, 805],
  };
  const [ow, oh] = dims[file] || [1600, 900];
  const w = maxW;
  const h = Math.round(maxW * (oh / ow));
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 80 },
      children: [
        new ImageRun({
          type: "png",
          data: buf,
          transformation: { width: w, height: h },
          altText: { name: caption, description: caption, title: caption },
        }),
      ],
    }),
    p(caption, { size: 18, italics: true, color: "555555", align: AlignmentType.CENTER, after: 200 }),
  ];
}

const children = [];

children.push(
  new Paragraph({
    spacing: { after: 80 },
    children: [new TextRun({ text: "SIH26170  ·  ISRO / Department of Space  ·  Theme: Smart Automation", font: "Arial", size: 20, color: accent, bold: true })],
  }),
  new Paragraph({
    spacing: { after: 80 },
    children: [new TextRun({ text: "AETHER", font: "Arial", size: 56, bold: true, color: navy })],
  }),
  p("Adaptive ESS Thermal Health and Early Reject", { size: 28, bold: true, after: 80 }),
  p("AI-Driven Anomaly Detection in Component Burn-In and Screening", { size: 24, after: 200 }),
  p("Briefing pack for the idea presentation (PPT). Copy these facts onto slides. Do not invent extra numbers.", { italics: true, after: 200 }),
  p("Use this file as the single source of truth while you build the deck. Each section maps to a slide. Speaker notes sit under the facts.", { after: 200 })
);

children.push(h1("1. How to use this document"));
children.push(...bullets([
  "Build 8 to 10 slides. SIH idea decks that try to dump the whole report lose the jury.",
  "Every number in this file is from the held-out test lots in models/metrics.json and the README. Do not round them into something prettier.",
  "The live demo is a CSV score on Screen my data. It is not a chamber plugged into the laptop. Do not say that it is.",
  "Figures live in docs/figures/. Drop them onto the matching slides.",
  "GitHub: https://github.com/amol16112005/AETHER-SIH26170",
]));

children.push(h1("2. Suggested slide map"));
children.push(
  table(
    ["Slide", "Title", "What belongs on it", "Time"],
    [
      ["1", "Title", "AETHER, SIH26170, ISRO / DoS, Smart Automation, one-line claim", "15 s"],
      ["2", "The gap", "Static datasheet vs lot-relative maverick. 45 µA vs 10 µA vs 50 µA", "45 s"],
      ["3", "What AETHER does", "Module A + Module B → PASS / HOLD / REJECT at 24 h", "45 s"],
      ["4", "Pipeline", "0 h + 24 h in. 168 h never an input. Figure: pipeline.png", "40 s"],
      ["5", "Module A — PAT", "Median + 6×1.4826×MAD. Isolation Forest + Mahalanobis on lot z-scores", "40 s"],
      ["6", "Module B — drift", "Ridge + HGB forecast of 168 h. Safety slope. MAE vs linear baseline", "40 s"],
      ["7", "Decision policy", "PASS finish 168 h. HOLD extra 96 h. REJECT pull now. Hours only from REJECT", "30 s"],
      ["8", "Held-out results", "0 escapes. 75 REJECT / 27 HOLD. 12.7% healthy HOLD. 10,944 h saved", "50 s"],
      ["9", "Live demo", "Screen my data. Upload LOTSIH 24 h CSV. LOTSIH-0045 REJECT", "60–90 s"],
      ["10", "Close", "Same pipeline on a new lot. Retrain only on a new historical corpus", "20 s"],
    ],
    [900, 2000, 5246, 1600]
  )
);

children.push(h1("3. Slide 1 — Title"));
children.push(h2("On-slide text"));
children.push(...bullets([
  "AETHER — Adaptive ESS Thermal Health and Early Reject",
  "Problem: SIH26170 — AI-Driven Anomaly Detection in Component Burn-In and Screening",
  "Organization: ISRO / Department of Space",
  "Theme: Smart Automation",
  "One-line claim: Models train offline on historical lots. At the 24 h gate a new lot CSV is scored with the frozen bundle: lot-relative PAT plus a 168 h drift forecast. No 168 h reading is used at inference.",
]));
children.push(h2("Speaker note"));
children.push(p("Open with the claim, not the stack. The jury already knows burn-in exists. They need to hear that you score at 24 hours without waiting for 168 hours."));

children.push(h1("4. Slide 2 — The gap static limits cannot close"));
children.push(h2("Problem in one paragraph"));
children.push(p("Traditional burn-in at 125 °C uses static datasheet limits. That misses latent defects: parts that stay inside the data-book box but sit far from their lot, or that drift on a slope no healthy part in the lot would take. Those parts escape into payloads."));
children.push(h2("Pinned SIH example — put this on the slide as three numbers"));
children.push(
  table(
    ["Quantity", "Value", "What a static screen does"],
    [
      ["Lot leakage (median)", "~10 µA", "Looks healthy"],
      ["Part LOTSIH-0045 leakage", "45.3 µA at 24 h", "Still under the cap"],
      ["Datasheet max", "50 µA", "Static PASS"],
      ["Lot-relative PAT", "z ≈ 35 vs the lot", "Dynamic REJECT"],
    ],
    [2800, 2746, 4200]
  )
);
children.push(h2("Three defect modes the generator injects"));
children.push(
  table(
    ["Mode", "What it looks like at 24 h", "Why static limits fail"],
    [
      ["Maverick", "In-spec, far from lot median", "The part is still under the datasheet cap"],
      ["Latent drift", "Normal 0 h, bad slope 0→24 h", "168 h failure is still in the future"],
      ["Runaway", "Quadratic aging", "Static limits catch it only late"],
    ],
    [2200, 3773, 3773]
  )
);
children.push(...figure("aging_modes.png", "Figure: three aging modes the synthetic lots inject."));
children.push(h2("Speaker note"));
children.push(p("Say the 45 versus 10 versus 50 example out loud. It is the problem statement’s own example. Then say: that is why PAT is lot-relative, and why one row by itself cannot show a maverick."));

children.push(h1("5. Slide 3 — What AETHER does"));
children.push(h2("On-slide text"));
children.push(...bullets([
  "Module A: dynamic outlier detection (PAT / DPAT) — robust median and MAD, Isolation Forest, robust Mahalanobis, all lot-normalized.",
  "Module B: 24 h → 168 h drift forecast for IDDQ, leakage, and propagation delay. 168 h is the target during training and is never an input at inference.",
  "Fused QA decision a human can read: PASS, HOLD, or REJECT, plus an inspector brief in engineering English.",
]));
children.push(h2("Parameters"));
children.push(
  table(
    ["Parameter", "Unit", "Datasheet max"],
    [
      ["Standby current (IDDQ) — required", "µA", "50"],
      ["Leakage current — required", "µA", "50"],
      ["Propagation delay (tpd) — required", "ns", "10"],
      ["VTH — optional extra", "V", "0.90 (min 0.28)"],
      ["IDSAT — optional extra", "mA", "25 (min 4)"],
      ["Reverse leakage — optional extra", "µA", "12"],
    ],
    [4200, 2773, 2773]
  )
);
children.push(h2("Readout times"));
children.push(p("Burn-in hours in the dataset: 0, 24, 96, 168. The 24 h gate uses only 0 h and 24 h. 96 h and 168 h can be empty on a live file. If they are present they can be plotted against the forecast. They do not change PASS / HOLD / REJECT."));

children.push(h1("6. Slide 4 — Pipeline"));
children.push(...figure("pipeline.png", "Figure: AETHER screening pipeline. Drop this on slide 4."));
children.push(h2("Flow to draw if you redraw it"));
children.push(...bullets([
  "Input: a whole lot, part_id, lot_id, IDDQ / leakage / tpd at 0 h and 24 h.",
  "Module A: lot median and MAD → robust z. Isolation Forest and Mahalanobis on those lot-relative features.",
  "Module B: predict 168 h from 0 h + 24 h (value, slope, relative change, log, linear extrapolation).",
  "Fuse: cost-sensitive thresholds. FN cost 1000, FP cost 12.",
  "Output: PASS / HOLD / REJECT + inspector brief. Chamber hours claimed only from 24 h REJECT (144 h per pulled part).",
]));
children.push(h2("Judge line (use this wording)"));
children.push(p("Models are trained offline on historical lots. At the 24 h gate a new lot CSV is scored with the frozen bundle: lot-relative PAT + 168 h drift forecast. No 168 h reading is used at inference.", { bold: true }));

children.push(h1("7. Slide 5 — Module A (dynamic outliers)"));
children.push(h2("PAT formula"));
children.push(p("AEC-Q001 style robust PAT: median ± 6 × 1.4826 × MAD. Isolation Forest contamination 0.06. Features are lot-normalized so a fast process corner does not scrap the whole lot."));
children.push(...figure("pat_histogram.png", "Figure: lot-relative PAT histogram."));
children.push(h2("Speaker note"));
children.push(p("PAT is computed inside the uploaded lot. Upload tens to hundreds of parts. A single part is its own median, so z ≈ 0 and Module A cannot see a maverick. One-part mode in Screen my data compares against a canned reference lot — that is a demo trick, not PAT on a new process corner."));

children.push(h1("8. Slide 6 — Module B (drift forecast)"));
children.push(h2("On-slide text"));
children.push(...bullets([
  "Inputs: value at 0 h, value at 24 h, 24 h slope, relative change, log, linear extrapolation to 168 h.",
  "Target at training time: hidden 168 h IDDQ, leakage, tpd, and optional VTH / IDSAT / reverse leakage.",
  "Models: Ridge (explainable) blended with Histogram Gradient Boosting. Blend weight 0.7 on the booster.",
  "Unsafe if predicted slope exceeds the healthy 95th-percentile safety slope, or the forecast crosses 90% of the datasheet cap.",
]));
children.push(h2("Held-out MAE versus linear extrapolation"));
children.push(
  table(
    ["Parameter", "AETHER MAE", "Linear-extrap MAE"],
    [
      ["IDDQ 168 h", "0.51 µA", "1.26 µA"],
      ["Leakage 168 h", "0.30 µA", "0.72 µA"],
      ["tpd 168 h", "0.07 ns", "0.19 ns"],
      ["VTH 168 h", "0.007 V", "0.019 V"],
      ["IDSAT 168 h", "0.20 mA", "0.46 mA"],
      ["Reverse leakage 168 h", "0.10 µA", "0.29 µA"],
    ],
    [3248, 3249, 3249]
  )
);
children.push(h2("Speaker note"));
children.push(p("If they ask why Ridge is still there: the inspector waterfall shows which feature pushed the 168 h forecast. The booster improves MAE. Ridge stays for the explanation."));

children.push(h1("9. Slide 7 — Three decisions, not two"));
children.push(
  table(
    ["Decision", "Meaning", "Chamber"],
    [
      ["PASS", "Lot-relative and predicted drift inside the envelope", "Finish remaining 168 h burn-in"],
      ["HOLD", "Not a clean pass, do not scrap yet", "Extra readout at 96 h"],
      ["REJECT", "Maverick and/or unsafe predicted drift", "Pull at 24 h; 144 h recovered"],
    ],
    [1800, 4546, 3400]
  )
);
children.push(...figure("decision_donut.png", "Figure: decision mix. Use only if it matches the test-lot counts below."));
children.push(p("Flight parts that look healthy still complete burn-in. Hours claimed back are only slots freed by early REJECT. HOLD exists because space-grade silicon is expensive. A two-class scrap/release policy is the wrong shape."));
children.push(h2("Cost weights used to set thresholds"));
children.push(
  table(
    ["Event", "Relative cost"],
    [
      ["False negative (missed defective)", "1000"],
      ["False positive (healthy REJECT)", "12"],
      ["HOLD on a defective", "40"],
      ["HOLD on a healthy part", "2"],
    ],
    [4873, 4873]
  )
);

children.push(h1("10. Slide 8 — Held-out results (the rubric)"));
children.push(p("25 lots, 5,145 parts. Train / val / test are split by lot, not by part. Every defective in the test lots still passes the datasheet at 24 h — a static screen would miss all of them."));
children.push(h2("Test lots (never seen in training)"));
children.push(
  table(
    ["Metric", "Value"],
    [
      ["Parts", "1,449"],
      ["Defectives / latent escapes", "102 / 102"],
      ["Detection recall (FN is the ISRO penalty)", "100% (0 miss / 102)"],
      ["Latent-escape catch rate", "100%"],
      ["24 h REJECT precision", "98.7%"],
      ["Catch rate (HOLD or REJECT)", "100% — 0 escapes"],
      ["REJECT-only recall", "73.5% (75 / 102)"],
      ["Healthy HOLD rate", "12.7% (171 / 1,347)"],
      ["By defect type REJECT / HOLD / PASS", "Maverick 42/0/0 · Latent 18/15/0 · Runaway 15/12/0"],
      ["Decisions", "1,175 PASS · 198 HOLD · 76 REJECT"],
      ["Chamber hours recovered (REJECT × 144 h)", "10,944 h"],
      ["LOTSIH-0045", "Static PASS (45.3 < 50) · Dynamic REJECT (z ≈ 35 vs lot 10.1 µA)"],
    ],
    [4200, 5546]
  )
);
children.push(h2("Speaker note"));
children.push(p("Lead with recall and the zero false negatives, then REJECT precision, then hours. Precision of the fused score itself is lower because HOLD is not a reject — do not quote the 0.37 fused precision as if it were REJECT precision. The rubric number is 98.7% REJECT precision."));

children.push(h1("11. Slide 9 — Live demo script"));
children.push(h2("What the jury should see"));
children.push(...bullets([
  "Open the Streamlit app. First tab is the canned lot board.",
  "Go to Screen my data.",
  "Caption on the tab: Inference only. 168 h is never an input.",
  "Upload a lot CSV, or Load example lot (25 parts, one maverick). Backup file: data/demo_lotsih_24h.csv (200 parts, includes LOTSIH-0045).",
  "Show decision counts PASS / HOLD / REJECT, then the 0 h vs 24 h scatter, then pick LOTSIH-0045 or LIVE-0010 in the part picker.",
  "Open Inspect this part: static PASS, dynamic REJECT, inspector brief.",
]));
children.push(h2("Expected backup run (demo_lotsih_24h.csv)"));
children.push(p("200 parts. 174 PASS, 25 HOLD, 1 REJECT. The reject is LOTSIH-0045."));
children.push(h2("What they upload (minimum columns)"));
children.push(
  table(
    ["Column", "Meaning"],
    [
      ["part_id", "Part name"],
      ["lot_id", "Lot that part belongs to"],
      ["iddq_0h, iddq_24h", "Quiescent current, µA"],
      ["ileak_0h, ileak_24h", "Leakage current, µA"],
      ["tpd_0h, tpd_24h", "Propagation delay, ns"],
    ],
    [3200, 6546]
  )
);
children.push(p("A lot file, not a single part. 96 h and 168 h can be empty. Labels (is_defective, defect_type) are not required to decide. Datasheet caps default to 50 / 50 / 10 if omitted."));
children.push(h2("Same pipeline, other door"));
children.push(p("POST /screen-lot (python -m uvicorn src.api:app --port 8000) calls the same enrich then apply_models path. Do not demo the API unless they ask. The CSV tab is the live story."));
children.push(h2("Do not say"));
children.push(...bullets([
  "That a burn-in chamber is plugged into the laptop.",
  "That the model retrains on the upload. It does not. screening_bundle.joblib stays frozen. Retrain only with python scripts/train.py on a new historical corpus.",
  "That 168 h is used at inference. It is not.",
]));

children.push(h1("12. Slide 10 — Close and Q&A bank"));
children.push(h2("Close line"));
children.push(p("A new lot at the 24 h gate is scored with the saved model. PAT is that lot’s median and MAD. Drift is a 168 h forecast from 0 h and 24 h. The inspector gets PASS, HOLD, or REJECT in English."));
children.push(h2("If they ask: is the data real ISRO flight data?"));
children.push(p("No. ISRO flight data is not public. The generator builds lot-structured burn-in with the three defect modes above. Replace data/burnin_parts.csv with a real ATE export of the same columns and re-run scripts/train.py. No other code changes."));
children.push(h2("If they ask: why not binary classification?"));
children.push(p("Space-grade parts are expensive. HOLD keeps a borderline part in the chamber to 96 h instead of killing it or releasing it."));
children.push(h2("If they ask: why Isolation Forest range is frozen for one part?"));
children.push(p("A one-part query would otherwise renormalize the IF score to itself. Live one-part mode uses the training-lot min/max so the calibrated HOLD/REJECT thresholds still mean the same thing."));
children.push(h2("If they ask: software stack"));
children.push(
  table(
    ["Layer", "What we use"],
    [
      ["Language", "Python 3.12"],
      ["Models", "scikit-learn 1.8 (Ridge, HGB, Isolation Forest, MinCovDet)"],
      ["QA UI", "Streamlit + Plotly"],
      ["Optional API", "FastAPI POST /screen-lot"],
      ["Repo", "github.com/amol16112005/AETHER-SIH26170"],
    ],
    [2400, 7346]
  )
);

children.push(h1("13. Copy-paste speaker script (about 5 minutes)"));
children.push(p("Burn-in today still uses a datasheet box. A part at 45 microamps in a 10 microamp lot still passes a 50 microamp cap. That is the maverick the problem statement names. AETHER scores the lot at 24 hours. Module A is lot-relative PAT. Module B forecasts 168 hour drift from 0 and 24 hour readings only. The inspector gets PASS, HOLD, or REJECT. On lots the model never trained on we catch all 102 latent defectives with zero PASS escapes: 75 rejected at 24 h, 27 sent to 96 h, 12.7 percent of healthy parts held. REJECT precision is 98.7 percent. 76 early rejects free 10,944 chamber hours. I will score the LOTSIH demo file. LOTSIH-0045 is the only reject. That is a CSV score with a frozen model. It is not a chamber on this laptop."));

children.push(h1("14. File checklist before the pitch"));
children.push(
  table(
    ["Item", "Path"],
    [
      ["This briefing", "docs/AETHER_SIH26170_PPT_Briefing.docx"],
      ["Existing idea PPT", "docs/SIH2026_AETHER_Idea_Presentation.pptx"],
      ["Figures", "docs/figures/"],
      ["Example lot (25 rows)", "data/live_lot_template.csv"],
      ["LOTSIH 24 h demo (200 parts)", "data/demo_lotsih_24h.csv"],
      ["Frozen bundle", "models/screening_bundle.joblib"],
      ["Held-out metrics", "models/metrics.json"],
      ["Technical report", "docs/AETHER_SIH26170_Technical_Report.docx"],
      ["Local app", "python -m streamlit run app.py"],
    ],
    [3600, 6146]
  )
);

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: navy },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: accent },
        paragraph: { spacing: { before: 220, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "1A237E" },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: "•",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          },
        ],
      },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: PAGE_W, height: PAGE_H },
          margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
        },
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: accent, space: 4 } },
              spacing: { after: 120 },
              children: [
                new TextRun({ text: "AETHER  ·  SIH26170 PPT briefing", font: "Arial", size: 18, color: accent, bold: true }),
              ],
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              border: { top: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC", space: 6 } },
              spacing: { before: 80 },
              children: [
                new TextRun({ text: "ISRO / Department of Space  ·  Smart Automation  ·  Page ", font: "Arial", size: 16, color: "666666" }),
                new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "666666" }),
              ],
            }),
          ],
        }),
      },
      children: [
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          children: [new TextRun({ text: "Contents", font: "Arial", size: 32, bold: true, color: navy })],
        }),
        new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
        new Paragraph({ spacing: { after: 200 }, children: [] }),
        ...children,
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(OUT, buffer);
  console.log("Wrote", OUT);
});

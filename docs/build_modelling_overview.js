/**
 * AETHER — ML mathematical modelling, desktop overview, and web content catalogue.
 */
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
        ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
        TableOfContents, ImageRun } = require("docx");
const fs = require("fs");
const path = require("path");

const NAVY = "1B365D";
const GOLD = "C45C26";
const LIGHT = "EEF3F8";
const ROW = "F7F9FC";
const WHITE = "FFFFFF";
const MUTED = "5B6B7C";
const RULE = "C5D0DC";
const TW = 9026;
const FIG = path.join(__dirname, "figures");

const thin = { style: BorderStyle.SINGLE, size: 4, color: RULE };
const borders = { top: thin, bottom: thin, left: thin, right: thin };

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

const num = (text, ref = "numbers") => new Paragraph({
  numbering: { reference: ref, level: 0 },
  spacing: { after: 80, line: 276 },
  children: [r(text, { size: 21 })],
});

const caption = (text) => p(text, { size: 18, italics: true, color: MUTED, after: 240, align: AlignmentType.CENTER });

function eqBox(lines) {
  const children = (Array.isArray(lines) ? lines : [lines]).map((line, i) =>
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: i === (Array.isArray(lines) ? lines.length - 1 : 0) ? 0 : 60 },
      children: [r(line, { size: 22, italics: true, color: NAVY })],
    }),
  );
  return new Table({
    width: { size: TW, type: WidthType.DXA },
    columnWidths: [TW],
    rows: [new TableRow({
      children: [new TableCell({
        borders,
        width: { size: TW, type: WidthType.DXA },
        shading: { fill: LIGHT, type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 160, right: 160 },
        children,
      })],
    })],
  });
}

function figure(file, origW, origH, maxW, name, desc) {
  const data = fs.readFileSync(path.join(FIG, file));
  const w = maxW;
  const h = Math.round(maxW * origH / origW);
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 160, after: 60 },
    children: [new ImageRun({
      type: "png",
      data,
      transformation: { width: w, height: h },
      altText: { name, description: desc, title: name },
    })],
  });
}

const kvTable = (pairs) => table(["Item", "Detail"], pairs, [2800, 6226]);

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
        { reference: "b2", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "b3", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "b4", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "b5", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "b6", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "b7", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "n2", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "n3", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "n4", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "n5", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
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
              r("AETHER  ·  SIH26170  ·  ML modelling, desktop & web catalogue", { size: 16, color: NAVY, bold: true }),
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
              r("Companion to the QA workstation at localhost:8501", { size: 16, color: MUTED }),
              r("    |    Page ", { size: 16, color: MUTED }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: MUTED }),
            ],
          })],
        }),
      },
      children: [
        new Paragraph({ spacing: { before: 280 }, children: [r("SMART INDIA HACKATHON 2026", { size: 20, bold: true, color: GOLD })] }),
        new Paragraph({ spacing: { before: 80, after: 80 }, children: [r("Problem SIH26170  ·  Theme: Smart Automation  ·  Organisation: ISRO / Department of Space", { size: 20, color: MUTED })] }),
        new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 20, color: NAVY, space: 4 } },
          spacing: { before: 360, after: 240 },
          children: [r("AETHER", { size: 64, bold: true, color: NAVY })],
        }),
        p("ML Mathematical Modelling, Desktop Overview, and Web Content Catalogue", { size: 28, color: NAVY, after: 80 }),
        p("A guided tour of every screen, control, and graph on the QA workstation, together with the exact equations the models compute.", { size: 22, color: MUTED, after: 320 }),
        kvTable([
          ["System", "AETHER — Adaptive ESS Thermal Health & Early Reject"],
          ["Document type", "Modelling + desktop / web catalogue (companion to the technical report)"],
          ["Workstation", "Streamlit app  ·  app.py  ·  http://localhost:8501"],
          ["Scope", "Module A / Module B mathematics · screen anatomy · every Plotly chart"],
          ["Data shown", "Held-out lots (test split) and pinned textbook part LOTSIH-0045"],
          ["Date", "10 September 2026"],
        ]),
        gap(),
        p("Figures in this document are print-light recreations of the same Plotly charts the website draws from screening_results.csv and the trained Ridge models. The live app uses a dark theme; the geometry, series, and colours (PASS green, HOLD amber, REJECT red) are identical."),

        new Paragraph({ children: [new PageBreak()] }),
        new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "Contents", font: "Arial", size: 32, bold: true, color: NAVY })] }),
        p("In Microsoft Word, right-click the field below and choose Update Field to refresh page numbers.", { size: 18, italics: true, color: MUTED }),
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),

        h1("1.  Purpose of this document"),
        p("The AETHER desktop is a Streamlit QA workstation. An inspector filters a lot, reads six held-out KPIs, and then works in four tabs: Lot board, QA inspector, Judging rubric, and Methodology. Behind those tabs sit two machine-learning modules whose outputs are fused into PASS, HOLD, or REJECT."),
        p("This document does three jobs that the live app cannot do on paper:"),
        bullet("Write down the mathematical model of every ML block — robust PAT, Isolation Forest, Mahalanobis, Ridge, histogram gradient boosting, safety slope, and the cost-sensitive fusion rule."),
        bullet("Give a desktop overview: how the window is laid out, what each control does, and the inspector workflow from lot to traveller brief."),
        bullet("Catalogue every piece of content and every graph on the website, including what data it plots, how to read it, and which equation it visualises."),

        h2("1.1 What the website is (and is not)"),
        table(
          ["The desktop is", "The desktop is not"],
          [
            ["A local QA workstation for burn-in screening", "A public consumer website"],
            ["A viewer over already-trained models and held-out lots", "A place where 168 h data is used at inference"],
            ["An explainability surface for a human inspector", "A black-box score with no audit trail"],
            ["Fed by data/ and models/ artifacts on disk", "A live ATE connection (swap the CSV to connect one)"],
          ],
          [4513, 4513],
        ),

        h1("2.  Desktop overview"),
        h2("2.1 How the workstation is launched"),
        p("From the project root the command is python -m streamlit run app.py. Streamlit binds port 8501. On first launch the app loads four artifacts; if any are missing it synthesises lots and trains, but the repository already ships them so the dashboard opens immediately."),
        table(
          ["Artifact", "Path", "Role on the desktop"],
          [
            ["Burn-in lots", "data/burnin_parts.csv", "Raw 0 / 24 / 96 / 168 h readings"],
            ["Screened table", "data/screening_results.csv", "Every chart and table on the Lot board"],
            ["Model bundle", "models/screening_bundle.joblib", "Module A + B + thresholds for inspector replay"],
            ["Held-out report", "models/metrics.json", "The six KPI tiles and the Judging rubric"],
          ],
          [2200, 3400, 3426],
        ),
        p("Loading is wrapped in Streamlit cache_resource, so a refresh does not retrain. The what-if slider on the QA inspector tab is the only path that re-runs apply_models on a single edited row."),

        h2("2.2 Window anatomy"),
        p("The page is a single wide Streamlit layout. Nothing is behind a second route. Everything below the hero banner reacts to the three filters at the top."),
        table(
          ["Band", "What the inspector sees"],
          [
            ["Hero", "Kicker SIH26170 · ISRO / DEPARTMENT OF SPACE. Title AETHER — Adaptive ESS Thermal Health & Early Reject. Subtitle describing lot-aware PAT plus 24 h → 168 h drift prediction."],
            ["Filters", "Lot (All lots or one lot id). Split (All / train / val / test; default test). Parameter (IDDQ, Leakage, tpd) — this only changes the Lot board scatter and the what-if slider."],
            ["KPI strip", "Six tiles computed on the held-out test lots, not on the current filter: recall, false negatives, latent catch rate, reject precision, IDDQ 168 h MAE, chamber hours saved."],
            ["Tabs", "Lot board · QA inspector · Judging rubric · Methodology."],
          ],
          [1800, 7226],
        ),
        figure("pipeline.png", 1598, 716, 600, "AETHER screening pipeline",
          "Block diagram from ATE 0 h and 24 h readings through Module A, Module B, fusion, and inspector charts."),
        caption("Figure 1. Screening pipeline the desktop implements. The website never waits for 96 h or 168 h before making the 24 h gate call."),

        h2("2.3 Colour language"),
        p("Every decision-coloured mark on the site uses the same three colours. The print figures in this document keep them."),
        table(
          ["Decision", "Colour", "Meaning on the desktop", "Chamber action"],
          [
            ["PASS", "Green #2ecc71", "Lot-relative and predicted drift are inside the envelope", "Finish remaining 168 h"],
            ["HOLD", "Amber #f1c40f", "Borderline: not clean, not scrap", "Extra readout at 96 h"],
            ["REJECT", "Red #e74c3c", "Maverick and/or unsafe predicted drift", "Pull at 24 h (144 h recovered)"],
          ],
          [1600, 2000, 3226, 2200],
        ),

        h2("2.4 Typical inspector workflow"),
        num("Open http://localhost:8501. Confirm the KPI strip: held-out recall 100%, 0 / 102 false negatives, latent catch 100%, reject precision 98.7%."),
        num("Leave Split on test. Optionally pick one lot. On Lot board, read the donut (mix) and the 0 h vs 24 h scatter (who sits off the diagonal)."),
        num("Sort the table by fused_score. Click through to QA inspector; the selector prefers the pinned SIH example LOTSIH-0045 when it is in view."),
        num("Read the static vs dynamic pair, the time-series trio, and the Ridge waterfalls. Copy the inspector brief into the lot traveller."),
        num("Use the 24 h what-if slider if a re-test reading is expected, then move to Judging rubric for the official three scores."),

        h1("3.  Complete web content catalogue"),
        p("This section lists every control, tile, sentence block, and table the website renders. Graphs are named here and fully specified in Section 4."),

        h2("3.1 Global chrome (always visible)"),
        h3("Hero copy"),
        p("Kicker: SIH26170 · ISRO / DEPARTMENT OF SPACE. Title: AETHER — Adaptive ESS Thermal Health & Early Reject. Subtitle: Lot-aware PAT outlier detection + 24 h → 168 h drift prediction, with inspector-grade explanations."),

        h3("Filters"),
        table(
          ["Control", "Choices", "Effect"],
          [
            ["Lot", "All lots, then every lot_id in the screened table", "Filters Lot board charts/table and the QA inspector component list. KPIs stay on held-out test."],
            ["Split", "All splits, train, val, test (default test)", "Same filter as Lot. Test is the honest view."],
            ["Parameter", "IDDQ, Leakage, tpd, plus VTH / IDSAT / reverse leakage when present", "Selects the Lot board scatter axes and the QA inspector what-if slider. Time series show every parameter the lot has."],
          ],
          [1800, 3200, 4026],
        ),

        h3("KPI strip — six tiles"),
        p("These numbers are always report['test'] from metrics.json. Changing Lot or Split does not rewrite them, so a judge cannot accidentally score the training lots."),
        table(
          ["Tile", "Value on this build", "Help text on the site", "Definition"],
          [
            ["Held-out recall", "100.0%", "False negatives are catastrophic; this is the primary score.", "TP / (TP+FN) where a positive is any non-PASS decision."],
            ["False negatives", "0 / 102", "Defective parts that received PASS.", "Count of is_defective parts with decision PASS, over all defectives."],
            ["Latent catch rate", "100.0%", "Defectives that still pass datasheet limits.", "Caught latent_escape parts / all latent_escape parts."],
            ["Reject precision", "98.7%", "Of 24 h REJECT calls, how many were truly defective.", "is_defective among decision = REJECT."],
            ["IDDQ 168 h MAE", "0.51 µA", "Module B prediction vs hidden ground truth.", "mean |pred_iddq_168h − iddq_168h| on the test lots."],
            ["VTH / IDSAT / IREV MAE", "0.007 V / 0.20 mA / 0.10 µA", "Optional extras; same 0 h / 24 h → 168 h stack.", "Shown when the ATE log has those columns."],
            ["Chamber hours saved", "10,944", "Only from 24 h REJECT — healthy flight parts still finish burn-in.", "144 h × number of early REJECT parts."],
          ],
          [1700, 1700, 2813, 2813],
        ),

        h2("3.2 Tab — Lot board"),
        p("Purpose: lot-level situation awareness. Left third is mix, right two-thirds is geometry, full width below is the ranked table."),
        table(
          ["Element", "Content"],
          [
            ["Graph G1 — decision donut", "PASS / HOLD / REJECT counts for the current filter. Hole annotated 24 h. Caption under the chart states the three chamber actions."],
            ["Graph G2 — 0 h vs 24 h scatter", "One point per part. X = selected parameter at 0 h, Y = same parameter at 24 h, colour = decision. Hover shows part_id."],
            ["Results table", "Sorted by fused_score descending. Height 360 px, no index. Columns listed below."],
          ],
          [2800, 6226],
        ),
        p("Table columns on Lot board:"),
        table(
          ["Column", "What it is"],
          [
            ["part_id / lot_id / split", "Identity and which side of the lot-wise split the part fell on."],
            ["decision", "PASS, HOLD, or REJECT from the fusion rule in Section 5.7."],
            ["fused_score", "s = s_A + 0.18 · 1_drift. Rank key for the table."],
            ["outlier_score", "Module A combined score s_A (PAT + Isolation Forest + Mahalanobis)."],
            ["{param}_0h / {param}_24h", "Measured values of the currently selected parameter."],
            ["pred_{param}_168h", "Module B forecast. Hidden from the model at training time for test lots; shown here for audit."],
            ["{param}_168h", "Actual 168 h (available in this demo because the generator stored it). Not an input."],
            ["defect_type", "healthy, maverick, latent_drift, or runaway."],
            ["latent_escape", "True if defective and still inside every datasheet cap."],
            ["hours_saved", "144 if REJECT, else 0."],
          ],
          [2800, 6226],
        ),

        h2("3.3 Tab — QA inspector"),
        p("Purpose: one-part audit. The component selector is sorted by fused_score. If the pinned SIH example is in the filter, it is pre-selected; otherwise the first latent_escape part is pre-selected."),
        table(
          ["Element", "Content"],
          [
            ["Component selectbox", "part_id list for the current Lot / Split filter."],
            ["Decision heading", "PASS / HOLD / REJECT in the decision colour."],
            ["Fused score metric", "Numeric s for this part. LOTSIH-0045 = 1.07."],
            ["Chamber hours saved", "144 or 0."],
            ["Headline (info banner)", "One sentence: pull now / hold to 96 h / finish 168 h."],
            ["Static vs dynamic pair", "Left: datasheet screen PASS/FAIL. Right: dynamic lot-relative decision. For LOTSIH-0045 a green success banner quotes 10 µA vs 45 µA vs 50 µA."],
            ["Contrast lines", "Per-parameter sentence: measured vs datasheet vs lot median vs robust z."],
            ["Why this call", "Bullet list from PAT hits and Module B safety / datasheet flags."],
            ["Graphs G3–G5", "Time series for IDDQ, leakage, tpd (always all three)."],
            ["Captions + graphs G6–G8", "Per-parameter 0 h → 24 h → pred 168 h line, then Ridge waterfall."],
            ["Inspector brief", "Plain-text block ready to paste into a lot traveller."],
            ["What-if slider", "Rewrites the selected parameter's 24 h value, recomputes slope/z, replays apply_models, and warns with the new decision and score."],
          ],
          [2800, 6226],
        ),

        h2("3.4 Tab — Judging rubric"),
        p("Purpose: map the live numbers onto the three official SIH26170 metrics. Three columns, then the pinned worked example."),
        table(
          ["Column", "What is shown"],
          [
            ["1. Anomaly detection", "Recall 100%. False negatives 0 / 102. Caption: static 24 h datasheet limits would miss 102 of these defectives; AETHER misses 0."],
            ["2. Drift prediction accuracy", "IDDQ MAE 0.507 µA, leakage MAE 0.306 µA, tpd MAE 0.066 ns. Caption quotes linear-extrapolation MAE 1.26 / 0.72 / 0.19."],
            ["3. Explainability", "Four bullets: robust z vs this lot's median; predicted 168 h slope vs healthy safety slope; Ridge waterfall; static vs dynamic side by side. Caption points the judge to QA inspector → LOTSIH-0045."],
          ],
          [2800, 6226],
        ),
        p("Under the three columns the site reprints the inspector brief and the static-vs-dynamic lines for LOTSIH-0045."),

        h2("3.5 Tab — Methodology"),
        p("Narrative blocks, then machine-readable JSON. The four headings on the site are:"),
        bullet("The gap static limits cannot close — 10 µA lot, 45 µA maverick, 50 µA datasheet. Module A is dynamic PAT inside the lot.", "b2"),
        bullet("Early reject at 24 h — Module B never waits for 168 h. Ridge stays in the loop so an inspector can see which feature pushed the forecast.", "b2"),
        bullet("Why three decisions, not two — HOLD exists because space-grade silicon is expensive.", "b2"),
        bullet("Evaluation bias — false negatives costed 80× higher than false positives during threshold talk-track; lots held out entirely.", "b2"),
        p("The site then lists the held-out lot ids and dumps a JSON object with thresholds, test_detection, test_drift_mae, and drift_model_blend. Those values are tabulated in Section 8 of this document."),
        p("Held-out lots printed on the Methodology tab: LOT01, LOT09, LOT10, LOT12, LOT14, LOT17, LOT24."),

        h2("3.6 What the website never shows"),
        bullet("96 h and 168 h are stored and plotted as measured traces for audit, but they are not inputs to Module A or Module B at the 24 h gate.", "b3"),
        bullet("Training-lot KPIs are not on the KPI strip. They exist in metrics.json and are summarised in Section 8.", "b3"),
        bullet("There is no login, no multi-page router, and no write-back to ATE. Decisions are computed, not edited.", "b3"),

        h1("4.  Graphs included in the web application"),
        p("The live app draws eight Plotly figures. G1–G2 live on Lot board and redraw when Lot, Split, or Parameter changes. G3–G8 live on QA inspector and redraw when the selected part changes. There are no charts on Judging rubric or Methodology."),
        table(
          ["ID", "Tab", "Plotly type", "Function in app.py"],
          [
            ["G1", "Lot board", "Donut (Pie, hole 0.62)", "_decision_pie"],
            ["G2", "Lot board", "Scatter", "_lot_scatter"],
            ["G3", "QA inspector", "Lines + markers + hlines", "_series_figure (iddq)"],
            ["G4", "QA inspector", "Lines + markers + hlines", "_series_figure (ileak)"],
            ["G5", "QA inspector", "Lines + markers + hlines", "_series_figure (tpd)"],
            ["G6", "QA inspector", "Waterfall", "_waterfall (iddq)"],
            ["G7", "QA inspector", "Waterfall", "_waterfall (ileak)"],
            ["G8", "QA inspector", "Waterfall", "_waterfall (tpd)"],
          ],
          [900, 1800, 2800, 3526],
        ),

        h2("4.1 G1 — Decision donut"),
        p("Data: value_counts of decision on the current filter. Colours from DECISION_COLOR. textinfo is label+percent. Centre annotation: 24 h. Legend is hidden; labels sit on the ring."),
        p("How to read it: the hole is the 24 h gate. A healthy screening line is a large green ring (finish burn-in), a thin amber wedge (96 h confirmation), and a small red wedge (pull now). On the held-out lots that the KPI strip refers to, the mix is 1,175 PASS (81.1%), 198 HOLD (13.7%), 76 REJECT (5.2%)."),
        figure("decision_donut.png", 714, 683, 360, "Decision donut",
          "Donut chart of PASS, HOLD, and REJECT on held-out lots."),
        caption("Figure 2. Graph G1 as shown on Lot board for Split = test, All lots."),

        h2("4.2 G2 — 0 h versus 24 h scatter"),
        p("One trace per decision. X = {param}_0h, Y = {param}_24h, marker size 8, opacity 0.75, hovertemplate part_id plus the two values. Axis titles take the parameter label and unit from PARAM_META. Horizontal legend above the plot."),
        p("How to read it: healthy parts lie on a tight diagonal near the lot centroid. Mavericks sit far up and right, still usually below the datasheet cap, and are coloured red. HOLD parts hug the upper edge of the healthy cloud. Changing Parameter switches the physical quantity but not the colour encoding."),
        figure("lot_scatter.png", 1528, 913, 600, "Lot scatter leakage",
          "Scatter of leakage at 0 h versus 24 h coloured by PASS, HOLD, REJECT."),
        caption("Figure 3. Graph G2 for Parameter = Leakage current, Split = test. Red points at ~45 µA are in-spec mavericks."),

        h2("4.3 G3–G5 — Time series versus predicted 168 h"),
        p("Each parameter gets its own chart in a three-column row. The inspector always sees all three, regardless of the Parameter filter."),
        p("Traces and reference lines, in draw order:"),
        table(
          ["Layer", "Geometry", "Meaning"],
          [
            ["Measured", "Solid line + markers at 0, 24, 96, 168 h", "What the ATE actually recorded. 96 h and 168 h are audit-only."],
            ["Model 168 h", "Dashed purple from (0, v0) to (168, ŷ)", "Module B blend forecast from 0 h and 24 h only."],
            ["Linear extrap", "Dotted grey from (0, v0) to (168, v0 + 7·Δ24)", "Physics baseline. If purple beats grey, the ML model is earning its keep."],
            ["Datasheet max", "Red dashed horizontal", "50 µA (IDDQ, leakage) or 10 ns (tpd)."],
            ["Safety envelope @ 168 h", "Amber dotted horizontal at v0 + 168 · s_safe", "Healthy 95th-percentile slope, not a datasheet number."],
          ],
          [2200, 3400, 3426],
        ),
        p("The figures below are G3–G5 for the pinned textbook part LOTSIH-0045. Leakage starts at 45.00 µA, is 45.32 µA at 24 h, and is forecast at 46.63 µA against a 50 µA cap — static-legal, dynamically rejected."),
        figure("series_iddq.png", 1132, 697, 600, "IDDQ time series",
          "IDDQ measured trace, model 168 h forecast, linear extrapolation, datasheet and safety lines."),
        caption("Figure 4. Graph G3 — Standby current (IDDQ) for LOTSIH-0045."),
        figure("series_ileak.png", 1132, 697, 600, "Leakage time series",
          "Leakage measured trace, model 168 h forecast, linear extrapolation, datasheet and safety lines."),
        caption("Figure 5. Graph G4 — Leakage current for LOTSIH-0045. This is the SIH 10 / 45 / 50 µA worked example."),
        figure("series_tpd.png", 1132, 697, 600, "tpd time series",
          "Propagation delay measured trace, model 168 h forecast, linear extrapolation, datasheet and safety lines."),
        caption("Figure 6. Graph G5 — Propagation delay for LOTSIH-0045. This part is a leakage maverick; tpd stays ordinary."),

        h2("4.4 G6–G8 — Ridge waterfall (not a black box)"),
        p("Each waterfall is the additive decomposition of the Ridge 168 h prediction in original units. Bars, left to right: intercept (absolute), eight feature contributions (relative, sorted by |contribution|), predicted 168 h (total). Increasing bars are red, decreasing bars cyan, totals purple. A caption above each chart prints 0 h (z) → 24 h (z) → pred 168 h (actual)."),
        eqBox(["ŷ_ridge = β₀ + Σ_j  z_j β_j    with    z_j = (x_j − μ_j) / σ_j"]),
        gap(),
        p("The eight features, in engineering language as labelled on the site, are: parameter @ 0 h, parameter @ 24 h, 24 h change, early slope, relative change, log(0 h), log(24 h), linear 168 h extrap. Because log(0 h) and log(24 h) are nearly collinear, a far-from-lot maverick can produce two huge opposing bars that cancel. The purple total is the number that matters; the large red/cyan pair is the model saying 'this log-level is extreme, but 0 h and 24 h agree with each other'."),
        figure("waterfall_iddq.png", 1277, 736, 600, "IDDQ Ridge waterfall",
          "Waterfall of Ridge contributions for IDDQ 168 h prediction."),
        caption("Figure 7. Graph G6 — IDDQ Ridge waterfall for LOTSIH-0045. Caption on site: 0 h 13.117 µA (z=1.63) → 24 h 13.648 (z=1.97) → pred 168 h 15.610 (actual 14.328)."),
        figure("waterfall_ileak.png", 1277, 736, 600, "Leakage Ridge waterfall",
          "Waterfall of Ridge contributions for leakage 168 h prediction."),
        caption("Figure 8. Graph G7 — Leakage Ridge waterfall for LOTSIH-0045. The canceling log bars are expected for a 35 σ maverick; the purple total 47.15 µA (Ridge; blend ŷ = 46.63 µA) sits just under the 50 µA cap."),
        figure("waterfall_tpd.png", 1276, 736, 600, "tpd Ridge waterfall",
          "Waterfall of Ridge contributions for tpd 168 h prediction."),
        caption("Figure 9. Graph G8 — tpd Ridge waterfall for LOTSIH-0045."),

        h2("4.5 Supporting figures used in this document (not on the website)"),
        p("Two extra plots are included so the modelling section can be read without opening the generator source. They are not Streamlit charts."),
        figure("pat_histogram.png", 1492, 769, 600, "LOTSIH leakage histogram",
          "Histogram of LOTSIH leakage at 24 h with lot median, LOTSIH-0045, and datasheet max."),
        caption("Figure 10. Why the datasheet screen misses the textbook part: the lot sits at ~10 µA, the part at 45.32 µA, the cap at 50 µA."),
        figure("aging_modes.png", 1491, 805, 600, "Generative aging modes",
          "Healthy, latent-drift, runaway, and maverick leakage trajectories versus datasheet cap."),
        caption("Figure 11. Four aging modes the synthetic generator injects. Module A is built for the purple maverick; Module B is built for the amber and red slopes."),

        h1("5.  ML mathematical modelling"),
        p("This section is the model card for the code in src/module_a.py, src/module_b.py, src/features.py, src/decisions.py, and src/generate_data.py. Symbols are collected again in Appendix A."),

        h2("5.1 Decision problem"),
        p("After 24 h of powered burn-in, each part i in lot L must receive one of three actions. 96 h and 168 h readings are hidden at inference. The primary error is a false negative: a defective part released as PASS."),
        table(
          ["Symbol", "Meaning"],
          [
            ["y_i ∈ {0,1}", "Latent defective flag (unknown in production; known in this demo)."],
            ["a_i ∈ {PASS, HOLD, REJECT}", "Action the fusion rule emits."],
            ["C_FN = 1000, C_FP = 12", "Cost of PASS-on-defective vs REJECT-on-healthy."],
            ["C_HD = 40, C_HH = 2", "Cost of HOLD on defective vs HOLD on healthy."],
            ["Recall floor", "MIN_RECALL = 0.97 on the validation lots before precision is maximised."],
          ],
          [2800, 6226],
        ),

        h2("5.2 Observed parameters and time grid"),
        p("Three electrical parameters are tracked on the MIL-STD-883 Method 1015-style grid t ∈ {0, 24, 96, 168} hours. Only t = 0 and t = 24 enter the models."),
        table(
          ["Parameter p", "Label on the site", "Unit", "Datasheet cap L_p", "PAT side"],
          [
            ["iddq", "Standby current (IDDQ)", "µA", "50", "upper"],
            ["ileak", "Leakage current", "µA", "50", "upper"],
            ["tpd", "Propagation delay", "ns", "10", "both"],
          ],
          [1600, 2600, 1200, 1800, 1826],
        ),

        h2("5.3 Physics-informed generative model (training data)"),
        p("Flight ATE data is not public. Lots are synthesised so that the failure modes the problem statement names actually exist, with process-corner shifts so a model cannot memorise one centroid."),
        eqBox("v(t) = v₀ (1 + α t + β t²) + ε,    ε ~ Normal(0, σ_meas²)"),
        gap(),
        p("Healthy parts: small α, β ≈ 0. Mavericks: v₀ offset 3–4× the lot mean, still below 0.88–0.92 of the datasheet. Latent drift: α raised into 0.0018–0.0040 /h. Runaway: α raised and β in 10⁻⁵ /h². Measurement noise is 0.16 µA (IDDQ), 0.09 µA (leakage), 0.025 ns (tpd). 24 lots, 170–230 parts each, plus the pinned 200-part textbook lot LOTSIH."),

        h2("5.4 Lot-relative features"),
        p("Every PAT and Mahalanobis number is computed inside the lot, never against the data book. For values x_{i,p,t} of part i, parameter p, time t in lot L:"),
        eqBox([
          "med_{L,p,t} = median({x_j,p,t : j ∈ L})",
          "MAD_{L,p,t} = median(|x_j,p,t − med_{L,p,t}|)",
          "σ_{L,p,t} = max(1.4826 · MAD_{L,p,t},  σ_floor,p)",
          "z_{i,p,t} = (x_{i,p,t} − med_{L,p,t}) / σ_{L,p,t}",
        ]),
        gap(),
        p("The constant 1.4826 is the consistency factor that makes MAD match the standard deviation of a Gaussian. Floors are 0.15 µA (IDDQ), 0.08 µA (leakage), 0.03 ns (tpd) so a tiny lot cannot invent infinite z. Early slope and relative change are:"),
        eqBox([
          "Δ24 = x_24 − x_0,     s_24 = Δ24 / 24,     r_24 = Δ24 / max(x_0, 0.05)",
          "z_slope = (s_24 − med_slope) / σ_slope",
        ]),

        h2("5.5 Module A — dynamic outlier detection"),
        p("Three complementary views are fused. PAT is the engineering-readable one-sided (or two-sided) gate. Isolation Forest is a non-parametric density probe on a 21-dimensional early vector. Robust Mahalanobis is an elliptical distance on the 9-dimensional z-vector."),

        h3("5.5.1 Robust PAT (AEC-Q001 style)"),
        p("Multiplier k = 6. For IDDQ and leakage (upper-sided) a hit is z > 6. For tpd (two-sided) a hit is |z| > 6. The same k is applied to z_slope. Contribution to the PAT score is clip(z/k, 0, ∞) or clip(|z|/k, 0, ∞)."),
        eqBox([
          "s_PAT^raw = Σ  clip(z / 6, 0, ∞)     over upper tests",
          "            + Σ  clip(|z| / 6, 0, ∞)  over two-sided tests",
          "s_PAT = clip(s_PAT^raw / 4, 0, 1)",
        ]),
        gap(),
        p("pat_hit is true if any individual test fired. Those strings (for example 'PAT ileak@24h z=35.0') become the 'Why this call' bullets on the QA inspector tab."),

        h3("5.5.2 Isolation Forest"),
        p("Feature matrix X ∈ R^{n×21} stacks, for each of the three parameters: x_0, x_24, z_0, z_24, s_24, r_24, z_slope. A RobustScaler maps each column by median and IQR. The forest has 400 trees, contamination 0.06, random_state 42."),
        p("In the original Isolation Forest formulation the anomaly score of a point x is"),
        eqBox([
          "s_IF^paper(x, n) = 2^{ − E[h(x)] / c(n) }",
          "c(n) = 2 H(n−1) − 2(n−1)/n,    H(k) ≈ ln k + γ",
        ]),
        gap(),
        p("sklearn's decision_function is low when the point is abnormal. AETHER flips and min-max normalises over the current batch so the number that enters fusion lives in about [0, 1]:"),
        eqBox("s_IF = ( −f(X) − min(−f) ) / ( max(−f) − min(−f) + 10^{−9} )"),

        h3("5.5.3 Robust Mahalanobis distance"),
        p("Let Z ∈ R^{n×9} be the z-only columns (already lot-normalised, better conditioned than raw+log). Minimum Covariance Determinant with support_fraction 0.9 estimates (μ̂, Σ̂); if MCD fails, empirical covariance is the fallback."),
        eqBox([
          "d²(z) = (z − μ̂)ᵀ Σ̂⁻¹ (z − μ̂)",
          "s_M = clip( d² / (9 · 4),  0, 3 ) / 3",
        ]),
        gap(),
        p("Dividing by 4p puts a Gaussian 2-σ ellipse near s_M ≈ 0.25; clipping at 3 then dividing by 3 bounds the score."),

        h3("5.5.4 Module A fusion"),
        eqBox("s_A = 0.40 s_PAT + 0.35 s_IF + 0.25 s_M"),
        gap(),
        p("PAT is weighted highest because it is the quantity an inspector can recompute with a calculator. Isolation Forest catches multivariate oddities that no single z-score flags. Mahalanobis contributes the elliptical view. On LOTSIH-0045, s_IF = 0.68, s_M = 1.00 (clipped), s_A = 0.89."),

        h2("5.6 Module B — 24 h → 168 h drift predictor"),
        p("One model per parameter. Linear extrapolation is the physics baseline (constant aging rate at 125 °C). Ridge is the primary learner because every coefficient is inspectable. Histogram gradient boosting is blended in only when it reduces validation MAE; on this build the blender picked w = 0.7 for all three parameters."),

        h3("5.6.1 Feature map"),
        eqBox("φ(x_0, x_24) = [ x_0, x_24, Δ24, s_24, r_24, log max(x_0,0.05), log max(x_24,0.05), x_0 + 7 Δ24 ]"),
        gap(),
        p("The last coordinate is the linear 168 h extrapolation (168/24 = 7). It is both a feature and the baseline plotted as the dotted grey line on G3–G5."),

        h3("5.6.2 Ridge"),
        p("Pipeline: StandardScaler then RidgeCV over α ∈ logspace(−3, 3, 13). The Ridge prediction in original units is exactly the waterfall G6–G8."),
        eqBox("ŷ_ridge = β₀ + Σ_j z_j β_j,     z = StandardScaler(φ)"),

        h3("5.6.3 Histogram gradient boosting and blend"),
        p("HGB hyperparameters: max_depth 4, learning_rate 0.06, max_iter 250, l2_regularization 0.1. Blend weight w is chosen on the validation lots from {0, 0.25, 0.4, 0.55, 0.7} by MAE."),
        eqBox("ŷ = (1 − w) ŷ_ridge + w ŷ_HGB,     w = 0.7 on this build"),
        gap(),
        table(
          ["Parameter", "Ridge MAE (val)", "HGB MAE (val)", "Blend MAE (val)", "w", "Safety slope s_safe"],
          [
            ["IDDQ", "0.611 µA", "0.470 µA", "0.470 µA", "0.70", "0.00591 µA/h"],
            ["Leakage", "0.430 µA", "0.300 µA", "0.301 µA", "0.70", "0.00540 µA/h"],
            ["tpd", "0.085 ns", "0.065 ns", "0.065 ns", "0.70", "0.00108 ns/h"],
          ],
          [1400, 1600, 1600, 1600, 900, 1926],
        ),

        h3("5.6.4 Safety slope and datasheet forecast flags"),
        p("On healthy training parts, the realised 0→168 h slope is (x_168 − x_0)/168. s_safe is the 95th percentile of that distribution. A part is drift-flagged if either:"),
        eqBox([
          "(ŷ − x_0) / 168  >  1.5 · s_safe     (predicted slope 50% beyond healthy 95th pct)",
          "ŷ  >  0.90 L_p                        (forecast already at 90% of the datasheet cap)",
        ]),
        gap(),
        p("1_drift is 1 if any of the three parameters trips either test. That bit is the only Module B quantity that enters the fused score; the ŷ values themselves are what G3–G5 and the inspector bullets quote."),

        h2("5.7 Fusion, thresholds, and the three-way action"),
        eqBox("s = s_A + 0.18 · 1_drift"),
        gap(),
        p("Thresholds are calibrated on validation lots only. Candidates are 90 quantiles of s between the 5th and 95th percentile. t_hold is the highest cut that still meets MIN_RECALL = 0.97 (with fallbacks 0.93, 0.88, 0.80). t_rej is the 55th percentile of scores that already sit above t_hold, and is forced at least 0.08 above t_hold. On this build:"),
        eqBox("t_hold = 0.401,     t_rej = 0.683"),
        gap(),
        p("The two-signal reject rule is deliberate. A high Isolation Forest score alone cannot scrap a flight part:"),
        table(
          ["Condition", "Action", "Stage label on the row"],
          [
            ["s ≥ t_rej  AND  (pat_hit OR 1_drift)", "REJECT", "EARLY_24H"],
            ["else if s ≥ t_hold OR 1_drift OR pat_hit", "HOLD", "NEEDS_96H"],
            ["otherwise", "PASS", "CONTINUE_168H"],
          ],
          [4200, 1800, 3026],
        ),
        eqBox("hours_saved = 144 · 1[action = REJECT]"),
        gap(),
        p("144 h is 168 − 24. PASS and HOLD recover no chamber time, because those parts stay in the oven. That is why the KPI 'Chamber hours saved' is 10,944 = 144 × 76 on the test lots, not a claim that healthy flight silicon was pulled early."),

        h2("5.8 Cost used during design (not a loss inside the estimators)"),
        p("Isolation Forest, Ridge, and HGB are not trained on the screening cost. The cost is the language used to justify recall-first thresholding:"),
        eqBox([
          "C = C_FP · 1[REJECT, healthy] + C_FN · 1[PASS, defective]",
          "  + C_HD · 1[HOLD, defective] + C_HH · 1[HOLD, healthy]",
        ]),
        gap(),
        p("With C_FN / C_FP = 1000/12 ≈ 83, a missed latent defect is the event the calibration refuses to buy down with a higher t_hold."),

        h2("5.9 Evaluation protocol"),
        p("Splits are by lot, never by part. GroupShuffleSplit, random_state 42: 25% of lots to test, then 30% of the remainder to validation. A process corner the Isolation Forest has never seen is the only honest test."),
        table(
          ["Split", "Lots", "Parts", "Defectives"],
          [
            ["Train", "LOT04, 06, 08, 11, 15, 16, 18, 19, 21, 22, 23, LOTSIH", "2,478", "205"],
            ["Val", "LOT02, 03, 05, 07, 13, 20", "1,218", "94"],
            ["Test", "LOT01, 09, 10, 12, 14, 17, 24", "1,449", "102"],
          ],
          [1400, 4426, 1600, 1600],
        ),
        p("Detection treats HOLD and REJECT as the positive class (anything other than PASS). Drift MAE is mean |ŷ − x_168| against the hidden 168 h column. Linear-extrapolation MAE is reported beside it so Module B has to beat a physicist with a ruler."),

        h1("6.  Mapping: every web graph to the equation it visualises"),
        table(
          ["Graph", "Equation / quantity"],
          [
            ["G1 donut", "Counts of a_i after the fusion rule in Section 5.7."],
            ["G2 scatter", "Raw (x_0, x_24) in the selected parameter; colour = a_i."],
            ["G3–G5 measured", "v(t) at t ∈ {0,24,96,168} — the generative process plus measurement noise."],
            ["G3–G5 purple dashed", "ŷ = 0.3 ŷ_ridge + 0.7 ŷ_HGB."],
            ["G3–G5 grey dotted", "x_0 + 7 (x_24 − x_0), the last coordinate of φ."],
            ["G3–G5 red h-line", "L_p, the datasheet cap."],
            ["G3–G5 amber h-line", "x_0 + 168 s_safe."],
            ["G6–G8 bars", "β₀ and z_j β_j for the Ridge half of Module B."],
            ["KPI recall / FN", "Confusion of 1[a ≠ PASS] against y."],
            ["KPI IDDQ MAE", "mean |ŷ_iddq − x_iddq,168| on test lots."],
            ["KPI hours saved", "144 × |{i : a_i = REJECT}| on test lots."],
            ["What-if warning", "Recompute s_24, r_24, z_24, z_slope, then the whole of Sections 5.5–5.7 on one row."],
          ],
          [2800, 6226],
        ),

        h1("7.  Worked example on the website — LOTSIH-0045"),
        p("The problem statement's numbers are pinned as lot LOTSIH, part LOTSIH-0045, and pre-selected on the QA inspector tab whenever that part is in the current filter."),
        table(
          ["Quantity", "Value"],
          [
            ["Leakage @ 0 / 24 / 96 / 168 h", "45.00 / 45.32 / 45.90 / 46.55 µA"],
            ["Lot median leakage @ 24 h", "10.20 µA"],
            ["Robust z @ 24 h", "35.0"],
            ["Datasheet cap", "50 µA"],
            ["Static screen", "PASS (45.32 < 50)"],
            ["Dynamic screen", "REJECT"],
            ["s_A / s / hours saved", "0.89 / 1.07 / 144"],
            ["Predicted leakage @ 168 h", "46.63 µA (actual 46.55 µA)"],
          ],
          [3400, 5626],
        ),
        p("Inspector brief as the website prints it:"),
        p("Part LOTSIH-0045 (lot LOTSIH) → REJECT. Recommend REJECT at 24 h — pull this part from the chamber. Continuing burn-in only occupies a slot. Leakage current at 24 h is 45.32 µA — 35.0 robust σ above the lot median (10.14 µA). Datasheet max is 50.00 µA, so a static screen would miss this maverick. Predicted 168 h Standby current (IDDQ) drift exceeds the healthy 95th-percentile safety slope.", { italics: true, size: 20 }),

        h1("8.  Numbers the dashboard is displaying"),
        p("Copied from models/metrics.json, which the KPI strip, Judging rubric, and Methodology JSON all read."),
        h2("8.1 Detection (non-PASS = positive)"),
        table(
          ["Split", "n", "Defectives", "Recall", "FN", "REJECT / HOLD / PASS", "Reject precision", "Hours saved"],
          [
            ["Train", "2478", "205", "100%", "0", "126 / 297 / 2055", "100%", "18,144"],
            ["Val", "1218", "94", "100%", "0", "66 / 170 / 982", "100%", "9,504"],
            ["Test (on site)", "1449", "102", "100%", "0", "76 / 198 / 1175", "98.7%", "10,944"],
          ],
          [1400, 900, 1200, 1000, 700, 1800, 1200, 826],
        ),
        p("A static 24 h datasheet screen misses 102 / 102 test defectives. That is the whole point of Module A, and it is the sentence under Anomaly detection on the Judging rubric tab."),

        h2("8.2 Drift MAE on held-out lots (the three tiles plus the linear baseline)"),
        table(
          ["Parameter", "Model MAE", "Linear-extrap MAE", "Healthy-only model MAE"],
          [
            ["IDDQ", "0.507 µA", "1.259 µA", "0.339 µA"],
            ["Leakage", "0.306 µA", "0.724 µA", "0.218 µA"],
            ["tpd", "0.066 ns", "0.193 ns", "0.049 ns"],
          ],
          [2256, 2256, 2257, 2257],
        ),

        h1("9.  Appendix A — symbol table"),
        table(
          ["Symbol", "Meaning", "Where it appears"],
          [
            ["x_{p,t}, v(t)", "Measured parameter at time t", "All charts; feature code"],
            ["med, MAD, σ, z", "Lot-robust location, scale, z-score", "Module A; inspector bullets"],
            ["k = 6", "PAT multiplier, AEC-Q001 style", "pat_hit, s_PAT"],
            ["s_PAT, s_IF, s_M, s_A", "PAT / Isolation Forest / Mahalanobis / combined outlier", "outlier_score column"],
            ["φ, ŷ_ridge, ŷ_HGB, ŷ", "Drift features and predictions", "G3–G8, pred_*_168h"],
            ["s_safe, 1_drift", "Healthy 95th-pct slope; any safety/datasheet flag", "amber h-line; fused score"],
            ["s, t_hold, t_rej", "Fused score and calibrated cuts", "KPI-adjacent table sort"],
            ["a_i", "PASS / HOLD / REJECT", "G1 colours, G2 colours, decision heading"],
            ["w = 0.7", "HGB blend weight on this build", "Methodology JSON"],
          ],
          [2000, 3600, 3426],
        ),

        h1("10.  Appendix B — source-file map"),
        table(
          ["File", "What it owns on the desktop / in the maths"],
          [
            ["app.py", "Hero, filters, KPI strip, four tabs, G1–G8, what-if slider"],
            ["src/config.py", "TIMES_H, PARAM_META, PAT_K, costs, contamination, floors"],
            ["src/features.py", "robust_center_scale, lot_stats, z, φ"],
            ["src/module_a.py", "PAT, Isolation Forest, MinCovDet, s_A"],
            ["src/module_b.py", "RidgeCV, HGB, blend, s_safe, ridge_contributions"],
            ["src/decisions.py", "calibrate_thresholds, two-signal REJECT, hours_saved"],
            ["src/explain.py", "Inspector brief, static vs dynamic, waterfall payload"],
            ["src/pipeline.py", "Lot-wise split, train_bundle, apply_models"],
            ["src/metrics.py", "detection_report, drift_mae — the KPI definitions"],
            ["src/generate_data.py", "v(t) = v0(1+αt+βt²)+ε and the LOTSIH pin"],
            ["models/metrics.json", "Every number in the KPI strip and Judging rubric"],
            ["data/screening_results.csv", "Every row behind G1, G2, and the Lot board table"],
          ],
          [2800, 6226],
        ),
        gap(),
        p("Launch reminder: python -m streamlit run app.py  →  http://localhost:8501. Open QA inspector and select LOTSIH-0045 to see G3–G8 on the exact part this document plots."),
      ],
    }],
  });

  const out = path.join(__dirname, "AETHER_ML_Modelling_Desktop_and_Web_Catalogue.docx");
  const buf = await Packer.toBuffer(doc);
  fs.writeFileSync(out, buf);
  console.log("Wrote", out, buf.length, "bytes");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

/**
 * AETHER — sources and references used to design the SIH26170 solution.
 */
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
        ShadingType, VerticalAlign, PageNumber, LevelFormat,
        ExternalHyperlink } = require("docx");
const fs = require("fs");
const path = require("path");

const NAVY = "1B365D";
const GOLD = "C45C26";
const ROW = "F7F9FC";
const WHITE = "FFFFFF";
const MUTED = "5B6B7C";
const RULE = "C5D0DC";
const TW = 9026;

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

function cell(text, width, opts = {}) {
  const fill = opts.fill || WHITE;
  const color = opts.color || (opts.header ? WHITE : "222222");
  const bold = opts.header || opts.bold || false;
  const paras = Array.isArray(text) ? text : [String(text)];
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 70, bottom: 70, left: 100, right: 100 },
    verticalAlign: VerticalAlign.CENTER,
    children: paras.map((t) => new Paragraph({
      spacing: { after: 40, line: 240 },
      children: [r(String(t), { size: opts.size || 18, bold, color, italics: opts.italics })],
    })),
  });
}

function table(headers, rows, widths) {
  const head = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => cell(h, widths[i], { header: true, fill: NAVY, size: 18 })),
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

const kvTable = (pairs) => table(["Item", "Detail"], pairs, [2800, 6226]);

function linkP(label, url, o = {}) {
  return new Paragraph({
    spacing: { after: o.after ?? 80, before: o.before ?? 0, line: 240 },
    children: [
      r(o.prefix || "", { size: 18, color: MUTED }),
      new ExternalHyperlink({
        children: [new TextRun({ text: label, font: "Arial", size: 18, color: "1B4F8A", underline: {} })],
        link: url,
      }),
    ],
  });
}

function ieee(n, citation, url) {
  const kids = [
    r(`[${n}]  ${citation}`, { size: 21 }),
  ];
  const block = [
    new Paragraph({
      spacing: { after: url ? 40 : 160, line: 276 },
      indent: { left: 720, hanging: 720 },
      children: kids,
    }),
  ];
  if (url) {
    block.push(new Paragraph({
      spacing: { after: 160, line: 240 },
      indent: { left: 720 },
      children: [
        new ExternalHyperlink({
          children: [new TextRun({ text: url, font: "Arial", size: 18, color: "1B4F8A", underline: {} })],
          link: url,
        }),
      ],
    }));
  }
  return block;
}

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
      ],
    },
    numbering: {
      config: [
        { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        { reference: "b2", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
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
              r("AETHER  ·  SIH26170  ·  Sources and references", { size: 16, color: NAVY, bold: true }),
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
              r("References used to design the solution", { size: 16, color: MUTED }),
              r("    |    Page ", { size: 16, color: MUTED }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: MUTED }),
            ],
          })],
        }),
      },
      children: [
        new Paragraph({ spacing: { before: 400 }, children: [r("SMART INDIA HACKATHON 2026", { size: 20, bold: true, color: GOLD })] }),
        new Paragraph({ spacing: { before: 80, after: 80 }, children: [r("Problem SIH26170  ·  Theme: Smart Automation  ·  Organisation: ISRO / Department of Space", { size: 20, color: MUTED })] }),
        new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 20, color: NAVY, space: 4 } },
          spacing: { before: 400, after: 280 },
          children: [r("AETHER", { size: 64, bold: true, color: NAVY })],
        }),
        p("Adaptive ESS Thermal Health & Early Reject", { size: 32, color: NAVY, after: 80 }),
        p("Sources and references used to come up with the solution", { size: 26, color: GOLD, after: 280 }),
        kvTable([
          ["Document type", "Bibliography and source map (IEEE numbered)"],
          ["Companion reports", "AETHER_SIH26170_Technical_Report.docx; AETHER_ML_Modelling_Desktop_and_Web_Catalogue.docx"],
          ["Date", "12 September 2026"],
          ["Purpose", "Cite every standard, paper, and dataset that shaped Module A, Module B, burn-in cadence, and evaluation"],
        ]),
        gap(),
        p("AETHER was not trained on a public ISRO flight dataset. Real screening data for space-grade parts is not published. The design starts from the SIH26170 problem statement, then maps onto automotive and military screening standards, IDDQ / burn-in literature, and standard machine-learning estimators implemented in scikit-learn. Training lots in data/burnin_parts.csv are physics-informed synthetic data generated by src/generate_data.py."),

        h1("1.  How the sources were used"),
        p("Each citation below is tied to a concrete design choice in the code or the evaluation protocol. Nothing is listed only because it is a well-known paper in the field."),
        table(
          ["AETHER piece", "Source used"],
          [
            ["Problem to solve: dynamic 45 µA vs 10 µA lot; 0 h + 24 h → 168 h; FN cost; explainability", "SIH26170 problem statement [1]"],
            ["PAT k = 6, lot-relative robust limits, mavericks inside the datasheet box", "AEC-Q001 Rev-D [2]"],
            ["125 °C powered burn-in; 0 / 24 / 96 / 168 h readout cadence", "MIL-STD-883 TM 1015 [3]; MIL-PRF-38535 [4]"],
            ["Observables: IDDQ, leakage, propagation delay", "Hawkins / Soden IDDQ reviews [5], [6]"],
            ["Isolation Forest on lot-normalised early features", "Liu, Ting and Zhou, ICDM 2008 [8]"],
            ["Robust Mahalanobis via MinCovDet", "Rousseeuw and van Driessen, 1999 [9]; Mahalanobis, 1936 [10]"],
            ["median + 6 × 1.4826 × MAD", "Hampel, 1974 [11]; AEC-Q001 robust sigma [2]"],
            ["Inspectable 168 h forecast (Ridge)", "Hoerl and Kennard, 1970 [12]"],
            ["Optional histogram gradient-boosting blend", "Friedman, 2001 [13]"],
            ["FN_COST = 1000 vs FP_COST = 12; recall-first thresholds", "SIH26170 [1]; Elkan, 2001 [15]"],
            ["Twelve confirmed-defect ICs (2274 … 2713) as a real-world check", "SEMATECH / Nigh et al., ITC 1998 [7]"],
            ["Training lots (5,145 parts, 25 lots including LOTSIH)", "Synthetic generator — not a downloaded dataset"],
          ],
          [4513, 4513],
        ),
        gap(),
        p("The twelve SEMATECH devices are scored one-at-a-time against a known-good reference lot in scripts/predict_realtime_iddq.py. They are not one manufacturing lot, so in-lot PAT among themselves would be the wrong test. They are not used as training data."),

        h1("2.  Problem statement"),
        p("This is the primary specification. Module A, Module B, the 10 / 45 / 50 µA worked example (pinned as LOTSIH-0045), and the three judging metrics all come from here."),
        ...ieee(1,
          "Smart India Hackathon 2026, problem SIH26170, “AI-Driven Anomaly Detection in Component Burn-In & Screening,” organisation: Indian Space Research Organisation (ISRO) / Department of Space, theme: Smart Automation.",
          "https://sih2026.vuce.in/ps/SIH26170"),

        h1("3.  Screening standards"),
        p("Automotive Part Average Testing already names the idea the problem statement asks for: a part that is still inside the datasheet can be a maverick relative to its lot. Military burn-in methods set the temperature and duration that the 0 / 24 / 96 / 168 h cadence follows."),
        ...ieee(2,
          "Automotive Electronics Council, AEC-Q001 Rev-D, “Guidelines for Part Average Testing.” Static PAT = Robust Mean ± 6 Robust Sigma; Dynamic PAT uses the current lot. Used in AETHER as PAT_K = 6.0 and MAD_TO_SIGMA = 1.4826 in src/config.py.",
          "http://www.aecouncil.com/Documents/AEC_Q001_Rev_D.pdf"),
        ...ieee(3,
          "U.S. Department of Defense, MIL-STD-883, Test Method 1015, “Burn-in Test.” Purpose: screen infant-mortality failures at elevated temperature (125 °C minimum for conditions A–E). AETHER treats 125 °C as the soak, not as a datasheet check.",
          "https://landandmaritimeapps.dla.mil/Downloads/MilSpec/Docs/MIL-STD-883/std883.pdf"),
        ...ieee(4,
          "MIL-PRF-38535, General Specification for Integrated Circuits (Microcircuits) Manufacturing. Class Q typically 160 h and Class V typically 240 h at 125 °C under TM 1015. The problem statement’s 0 h, 24 h, 96 h and 168 h readouts are the practical measurement cadence of that flow.",
          "https://landandmaritimeapps.dla.mil/Downloads/MilSpec/Docs/MIL-PRF-38535/prf38535.pdf"),

        h1("4.  Electronics and IDDQ literature"),
        p("These papers justify why standby current, leakage and delay are the right observables, and they supply the only published real-device table used in this repository."),
        ...ieee(5,
          "J. M. Soden, C. F. Hawkins, R. K. Gulati and W. Mao, “IDDQ Testing: A Review,” in IDDQ Testing of VLSI Circuits. Dordrecht: Springer, 1992, pp. 5–17. IDDQ as a defect-sensitive DC test for bridges, gate-oxide shorts and leakage that stuck-at tests miss.",
          "https://link.springer.com/chapter/10.1007/978-1-4615-3146-3_1"),
        ...ieee(6,
          "C. F. Hawkins, J. M. Soden, R. R. Fritzemeier and L. K. Horning, “Quiescent power supply current measurement for CMOS IC defect detection,” IEEE Transactions on Industrial Electronics, vol. 36, no. 2, pp. 211–218, May 1989."),
        ...ieee(7,
          "P. Nigh, D. Vallett, A. Patel, J. Wright, F. Motika, D. Forlenza, R. Kurtulik and W. Chong, “Failure analysis of timing and IDDq-only failures from the SEMATECH test methods experiment,” Proc. International Test Conference, 1998, pp. 43–52. DOI: 10.1109/TEST.1998.743135. Table 1 is the source of the twelve confirmed-defect ICs (2274, 3392, 2795, 2890, 3488, 2663, 1787, 1947, 2968, 3457, 2557, 2713) scored in scripts/predict_realtime_iddq.py. Pre-burn-in IDDQ and post-burn-in values at 6 / 78 / 150 h, with physical defect found. SEMATECH also concluded that IDDQ is not a complete replacement for burn-in — which is why healthy AETHER parts still finish 168 h.",
          "https://doi.org/10.1109/TEST.1998.743135"),

        h1("5.  Machine-learning methods"),
        p("Module A fuses three complementary views: robust PAT, Isolation Forest, and robust Mahalanobis. Module B uses Ridge as the inspectable 168 h model, with an optional histogram gradient-boosting blend only when it reduces validation MAE. Implementations are scikit-learn classes cited in [14]."),
        ...ieee(8,
          "F. T. Liu, K. M. Ting and Z.-H. Zhou, “Isolation Forest,” Proc. 8th IEEE International Conference on Data Mining (ICDM), Pisa, Italy, 2008, pp. 413–422. DOI: 10.1109/ICDM.2008.17. Used as sklearn.ensemble.IsolationForest on lot-normalised 0 h / 24 h features (400 trees, contamination 0.06).",
          "https://doi.org/10.1109/ICDM.2008.17"),
        ...ieee(9,
          "P. J. Rousseeuw and K. van Driessen, “A Fast Algorithm for the Minimum Covariance Determinant Estimator,” Technometrics, vol. 41, no. 3, pp. 212–223, 1999. Robust covariance of the lot z-vector; Mahalanobis distance flags parts outside the lot ellipsoid (sklearn.covariance.MinCovDet).",
          "https://doi.org/10.1080/00401706.1999.10485670"),
        ...ieee(10,
          "P. C. Mahalanobis, “On the generalised distance in statistics,” Proceedings of the National Institute of Sciences of India, vol. 2, no. 1, pp. 49–55, 1936. Distance of a part to the lot centroid under the estimated covariance."),
        ...ieee(11,
          "F. R. Hampel, “The influence curve and its role in robust estimation,” Journal of the American Statistical Association, vol. 69, no. 346, pp. 383–393, 1974. Median and median absolute deviation; the factor 1.4826 makes MAD consistent for the standard deviation of a normal distribution.",
          "https://doi.org/10.1080/01621459.1974.10482962"),
        ...ieee(12,
          "A. E. Hoerl and R. W. Kennard, “Ridge Regression: Biased Estimation for Nonorthogonal Problems,” Technometrics, vol. 12, no. 1, pp. 55–67, 1970. Primary Module B model (sklearn.linear_model.RidgeCV) because every coefficient is inspectable in the QA waterfall.",
          "https://doi.org/10.1080/00401706.1970.10488634"),
        ...ieee(13,
          "J. H. Friedman, “Greedy function approximation: A gradient boosting machine,” Annals of Statistics, vol. 29, no. 5, pp. 1189–1232, 2001. Optional HistGradientBoostingRegressor blend, used only when it beats Ridge on held-out-lot validation MAE.",
          "https://doi.org/10.1214/aos/1013203451"),
        ...ieee(14,
          "F. Pedregosa et al., “Scikit-learn: Machine Learning in Python,” Journal of Machine Learning Research, vol. 12, pp. 2825–2830, 2011. Concrete implementations: IsolationForest, MinCovDet, EmpiricalCovariance, RidgeCV, HistGradientBoostingRegressor, RobustScaler, StandardScaler.",
          "https://jmlr.org/papers/v12/pedregosa11a.html"),
        ...ieee(15,
          "C. Elkan, “The Foundations of Cost-Sensitive Learning,” Proc. 17th International Joint Conference on Artificial Intelligence (IJCAI), 2001, pp. 973–978. Decision thresholds follow FN cost 1000 versus FP cost 12 rather than a 0.5 accuracy cut. HOLD exists because space-grade silicon is expensive: a two-class scrap/release policy is the wrong shape.",
          "https://cseweb.ucsd.edu/~elkan/kddcost.pdf"),

        h1("6.  Data provenance"),
        h2("6.1 Training and held-out lots — synthetic"),
        p("ISRO / Department of Space screening data for flight parts is not a public download. src/generate_data.py therefore builds lot-structured time series that reproduce the failure modes the problem statement cares about:"),
        bullet("Mavericks — far from the lot centroid, still inside the datasheet box (the 10 / 45 / 50 µA sentence)."),
        bullet("Latent drift — normal at 0 h, anomalous slope, often still in-spec at 168 h."),
        bullet("Runaway — accelerating degradation that a static limit only catches late."),
        p("Healthy parts follow a slow, nearly linear ageing law at 125 °C. Process corners (fast / nominal / slow) shift the whole lot centroid so a global Isolation Forest on raw microamps cannot be used — scores are lot-normalised first. Measurement noise is set to typical parametric-analyser repeatability. Default build: 24 generated lots plus the pinned LOTSIH textbook lot, 5,145 parts, split by lot (not by part) into train / val / test. Optional extras VTH, IDSAT, and reverse leakage are generated with the same defect modes."),
        h2("6.2 Real confirmed-defect ICs — SEMATECH [7]"),
        p("The twelve-row table pasted into the project (device IDs, pre-BI IDDQ, post-BI IDDQ at 6 / 78 / 150 h, and physical defect) is Table 1 of Nigh et al., International Test Conference 1998 [7]. AETHER maps those currents to microamps and scores each IC against a known-good reference lot (LOT01 healthy parts). Mapping notes live in scripts/predict_realtime_iddq.py."),
        table(
          ["Device ID", "Physical defect (as published)"],
          [
            ["2274", "Gate-to-drain short (128 kΩ)"],
            ["3392", "Poly-to-poly short (1.63 kΩ)"],
            ["2795", "Poly-to-NWell short (340 kΩ)"],
            ["2890", "Poly-to-NWell short (194 kΩ)"],
            ["3488", "Metal-to-metal short (184 Ω)"],
            ["2663", "Poly short in gate-array fill (two independent defects)"],
            ["1787", "Metal-to-metal short (75 Ω)"],
            ["1947", "Source-to-drain leakage"],
            ["2968", "Poly-to-diffusion / substrate leakage across 28 transistors"],
            ["3457", "Leakage in gate-array fill logic"],
            ["2557", "Leakage in gate-array fill logic"],
            ["2713", "Leakage in gate-array fill logic"],
          ],
          [2200, 6826],
        ),
        gap(),
        p("These twelve devices are a published check, not the training distribution. SEMATECH also reported that even IDDQ did not fully replace burn-in stressing. AETHER therefore never claims chamber hours back on PASS or HOLD parts; only early REJECT frees 144 h of soak."),

        h1("7.  IEEE reference list (compact)"),
        p("Copy-ready numbered list for the technical report, poster, or judging pack."),
        ...ieee(1, "Smart India Hackathon 2026, SIH26170, “AI-Driven Anomaly Detection in Component Burn-In & Screening,” ISRO / Department of Space. https://sih2026.vuce.in/ps/SIH26170"),
        ...ieee(2, "Automotive Electronics Council, AEC-Q001 Rev-D, Guidelines for Part Average Testing, 2011. http://www.aecouncil.com/Documents/AEC_Q001_Rev_D.pdf"),
        ...ieee(3, "MIL-STD-883, Test Method 1015, Burn-in Test."),
        ...ieee(4, "MIL-PRF-38535, General Specification for Integrated Circuits (Microcircuits) Manufacturing."),
        ...ieee(5, "J. M. Soden, C. F. Hawkins, R. K. Gulati and W. Mao, “IDDQ Testing: A Review,” in IDDQ Testing of VLSI Circuits, Springer, 1992."),
        ...ieee(6, "C. F. Hawkins, J. M. Soden, R. R. Fritzemeier and L. K. Horning, “Quiescent power supply current measurement for CMOS IC defect detection,” IEEE Trans. Ind. Electron., vol. 36, no. 2, pp. 211–218, 1989."),
        ...ieee(7, "P. Nigh et al., “Failure analysis of timing and IDDq-only failures from the SEMATECH test methods experiment,” Proc. ITC, 1998, pp. 43–52, doi: 10.1109/TEST.1998.743135."),
        ...ieee(8, "F. T. Liu, K. M. Ting and Z.-H. Zhou, “Isolation Forest,” Proc. IEEE ICDM, 2008, pp. 413–422, doi: 10.1109/ICDM.2008.17."),
        ...ieee(9, "P. J. Rousseeuw and K. van Driessen, “A Fast Algorithm for the Minimum Covariance Determinant Estimator,” Technometrics, vol. 41, no. 3, pp. 212–223, 1999."),
        ...ieee(10, "P. C. Mahalanobis, “On the generalised distance in statistics,” Proc. Nat. Inst. Sci. India, vol. 2, no. 1, pp. 49–55, 1936."),
        ...ieee(11, "F. R. Hampel, “The influence curve and its role in robust estimation,” J. Amer. Statist. Assoc., vol. 69, no. 346, pp. 383–393, 1974."),
        ...ieee(12, "A. E. Hoerl and R. W. Kennard, “Ridge Regression: Biased Estimation for Nonorthogonal Problems,” Technometrics, vol. 12, no. 1, pp. 55–67, 1970, doi: 10.1080/00401706.1970.10488634."),
        ...ieee(13, "J. H. Friedman, “Greedy function approximation: A gradient boosting machine,” Ann. Statist., vol. 29, no. 5, pp. 1189–1232, 2001."),
        ...ieee(14, "F. Pedregosa et al., “Scikit-learn: Machine Learning in Python,” JMLR, vol. 12, pp. 2825–2830, 2011."),
        ...ieee(15, "C. Elkan, “The Foundations of Cost-Sensitive Learning,” Proc. IJCAI, 2001, pp. 973–978."),

        h1("8.  What was not used"),
        bullet("No public ISRO / Department of Space burn-in CSV. Training data is generated, not downloaded.", "b2"),
        bullet("The SEMATECH ICs [7] are a held-out real-world check. They are not mixed into train / val / test lots.", "b2"),
        bullet("No proprietary ATE STDF from a screening house was ingested. A production line would freeze PAT k and the safety slope on that product after a qualification lot.", "b2"),
        gap(),
        p("End of document. AETHER — Adaptive ESS Thermal Health & Early Reject — SIH26170.", { italics: true, color: MUTED }),
      ],
    }],
  });

  const out = path.join(__dirname, "AETHER_SIH26170_References_and_Sources.docx");
  const buf = await Packer.toBuffer(doc);
  fs.writeFileSync(out, buf);
  console.log("Wrote", out);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

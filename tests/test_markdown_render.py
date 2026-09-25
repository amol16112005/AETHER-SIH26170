"""Regression: indented Streamlit markdown must not render as a code block."""

from app import _dedent_md


def test_dedent_md_exposes_headings():
    raw = """
            ### The gap static limits cannot close

            A lot whose leakage centroid sits at 10 µA
            """
    first_raw = next(line for line in raw.splitlines() if line.strip())
    assert first_raw.startswith("    ")

    fixed = _dedent_md(raw)
    first = fixed.splitlines()[0]
    assert first == "### The gap static limits cannot close"
    assert not first.startswith(" ")


def test_later_hour_plot_appears_only_when_measured():
    import pandas as pd

    from app import _measured_vs_predicted

    frame = pd.DataFrame(
        {
            "part_id": ["A"],
            "iddq_0h": [11.0],
            "pred_iddq_168h": [12.0],
            "iddq_96h": [float("nan")],
            "iddq_168h": [float("nan")],
        }
    )
    assert _measured_vs_predicted(frame, "iddq", 96) is None
    assert _measured_vs_predicted(frame, "iddq", 168) is None
    frame["iddq_168h"] = 12.4
    assert _measured_vs_predicted(frame, "iddq", 168) is not None


def test_methodology_tab_uses_dedented_markdown():
    from pathlib import Path

    source = Path("app.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    method = source.split("with tab_method:", 1)[1]
    assert "_md(" in method
    assert "st.markdown(" not in method.split("_md(", 1)[0]

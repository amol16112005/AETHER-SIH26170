import pandas as pd
import pytest

from src.live_screen import (
    OPTIONAL_LATER,
    LiveScreenError,
    complete_rows,
    ingest_ate_lot,
    lotsih_demo_csv_bytes,
    lotsih_demo_frame,
    parse_live_upload,
    score_incoming_lot,
    screen_lot,
    screen_one_part,
    template_csv_bytes,
    template_frame,
)
from src.module_a import iforest_raw_range
from src.pipeline import apply_models, enrich, load_bundle


def test_template_has_required_columns_and_one_maverick():
    df = template_frame()
    live = complete_rows(df)
    assert len(live) == 25
    assert set(["iddq_0h", "ileak_24h", "tpd_0h"]).issubset(live.columns)
    assert live["ileak_24h"].max() > 40


def test_parse_csv_is_case_insensitive():
    csv = "Part_ID,Lot_ID,IDDQ_0h,IDDQ_24h,ILEAK_0h,ILEAK_24h,TPD_0h,TPD_24h\nA,L,11,11.1,10,10.1,4.7,4.72\n"
    live = parse_live_upload(csv)
    assert live.iloc[0]["part_id"] == "A"
    assert live.iloc[0]["iddq_0h"] == pytest.approx(11.0)


def test_incomplete_rows_are_dropped():
    df = template_frame()
    df.loc[0, "ileak_24h"] = None
    live = complete_rows(df)
    assert len(live) == 24


def test_missing_columns_raise():
    with pytest.raises(LiveScreenError, match="Missing required columns"):
        complete_rows(pd.DataFrame({"part_id": ["x"], "iddq_0h": [1]}))


def test_live_lot_rejects_in_spec_maverick():
    bundle = load_bundle()
    screened = pd.read_csv("data/screening_results.csv")
    ctx = screened[screened["split"] == "train"]
    if_range = iforest_raw_range(ctx, bundle.outlier)
    result, warnings = screen_lot(template_frame(), bundle, iforest_range=if_range)
    maverick = result.loc[result["part_id"] == "LIVE-0010"].iloc[0]
    assert maverick["decision"] == "REJECT"
    assert result["decision"].eq("PASS").sum() >= 6
    assert not warnings or all("LIVELOT" in w or "mates" in w or "single" in w for w in warnings)


def test_one_part_against_lotsih_matches_textbook():
    bundle = load_bundle()
    screened = pd.read_csv("data/screening_results.csv")
    ctx = screened[screened["split"] == "train"]
    if_range = iforest_raw_range(ctx, bundle.outlier)
    ref = screened[screened["lot_id"] == "LOTSIH"]
    demo = screened.loc[screened["sih_example"].astype(bool)].iloc[0]
    out = screen_one_part(
        {
            "part_id": "PROBE",
            "lot_id": "LOTSIH",
            "iddq_0h": float(demo["iddq_0h"]),
            "iddq_24h": float(demo["iddq_24h"]),
            "ileak_0h": float(demo["ileak_0h"]),
            "ileak_24h": float(demo["ileak_24h"]),
            "tpd_0h": float(demo["tpd_0h"]),
            "tpd_24h": float(demo["tpd_24h"]),
        },
        ref,
        bundle,
        iforest_range=if_range,
    )
    assert out.iloc[0]["decision"] == "REJECT"
    assert out.iloc[0]["ileak_24h_z"] > 6


def test_template_csv_bytes_roundtrip():
    live = parse_live_upload(template_csv_bytes())
    assert len(live) == 25
    assert "iddq_96h" not in live.columns
    assert "process_corner" not in live.columns


def test_ingest_ate_lot_fills_later_hours_and_defaults():
    live = ingest_ate_lot(template_csv_bytes())
    assert len(live) == 25
    assert set(["part_id", "lot_id", "iddq_0h", "ileak_24h", "tpd_24h"]).issubset(live.columns)
    for col in OPTIONAL_LATER:
        assert col in live.columns
        assert live[col].isna().all()
    assert (live["process_corner"] == "unknown").all()
    assert live["datasheet_iddq_max"].iloc[0] == 50
    assert live["datasheet_ileak_max"].iloc[0] == 50
    assert live["datasheet_tpd_max"].iloc[0] == 10
    assert "is_defective" not in live.columns
    assert "defect_type" not in live.columns


def test_ingest_requires_lot_id_and_keeps_a_real_168h():
    missing_lot = (
        "part_id,iddq_0h,iddq_24h,ileak_0h,ileak_24h,tpd_0h,tpd_24h\n"
        "A,11,11.1,10,10.1,4.7,4.72\n"
    )
    with pytest.raises(LiveScreenError, match="lot_id"):
        ingest_ate_lot(missing_lot)

    supplied = (
        "Part ID,Lot ID,IDDQ_0h,IDDQ_24h,ILEAK_0h,ILEAK_24h,TPD_0h,TPD_24h,"
        "IDDQ_168h,is_defective,defect_type\n"
        "A,LOT-X,11,11.1,10,10.1,4.7,4.72,12.5,1,latent_drift\n"
    )
    live = ingest_ate_lot(supplied)
    assert live.iloc[0]["part_id"] == "A"
    assert live.iloc[0]["lot_id"] == "LOT-X"
    assert live.iloc[0]["iddq_168h"] == pytest.approx(12.5)
    assert live.iloc[0]["ileak_168h"] != live.iloc[0]["ileak_168h"]
    assert live.iloc[0]["process_corner"] == "unknown"
    assert "is_defective" not in live.columns


def test_ingest_rejects_a_blank_lot_id():
    csv = (
        "part_id,lot_id,iddq_0h,iddq_24h,ileak_0h,ileak_24h,tpd_0h,tpd_24h\n"
        "A,,11,11.1,10,10.1,4.7,4.72\n"
    )
    with pytest.raises(LiveScreenError, match="lot_id is blank"):
        ingest_ate_lot(csv)


def test_live_score_does_not_overwrite_screening_results():
    from hashlib import sha256
    from pathlib import Path

    path = Path("data/screening_results.csv")
    before = sha256(path.read_bytes()).hexdigest()
    bundle = load_bundle()
    raw = ingest_ate_lot(template_csv_bytes())
    scored = apply_models(enrich(raw), bundle)
    assert "decision" in scored.columns
    assert sha256(path.read_bytes()).hexdigest() == before


def test_lotsih_demo_file_is_24h_only_and_includes_the_example():
    frame = lotsih_demo_frame()
    assert len(frame) == 200
    assert "LOTSIH-0045" in set(frame["part_id"])
    assert "iddq_168h" not in frame.columns
    assert "ileak_168h" not in frame.columns
    raw = ingest_ate_lot(lotsih_demo_csv_bytes())
    example = raw.loc[raw["part_id"] == "LOTSIH-0045"].iloc[0]
    assert example["ileak_24h"] == pytest.approx(45.32)
    assert raw["iddq_168h"].isna().all()


def test_ingested_lot_scores_without_labels():
    bundle = load_bundle()
    raw = ingest_ate_lot(template_csv_bytes())
    result, _warnings = score_incoming_lot(raw, bundle)
    live = enrich(raw)
    direct = apply_models(live, bundle)
    assert result["decision"].tolist() == direct["decision"].tolist()
    assert result["fused_score"].tolist() == pytest.approx(direct["fused_score"].tolist())
    assert "iddq_24h_z" in live.columns
    assert set(result["decision"]).issubset({"PASS", "HOLD", "REJECT"})
    assert result.loc[result["part_id"] == "LIVE-0010", "decision"].iloc[0] == "REJECT"
    assert "is_defective" not in result.columns

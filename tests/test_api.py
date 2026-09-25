from hashlib import sha256
from pathlib import Path

from fastapi.testclient import TestClient

from src.api import app
from src.live_screen import template_csv_bytes, template_frame


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_post_screen_lot_csv_uses_saved_bundle_and_leaves_files():
    results = Path("data/screening_results.csv")
    bundle = Path("models/screening_bundle.joblib")
    results_before = _digest(results)
    bundle_before = _digest(bundle)

    with TestClient(app) as client:
        response = client.post(
            "/screen-lot",
            files={"file": ("lot.csv", template_csv_bytes(), "text/csv")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["n_parts"] == 25
    maverick = next(row for row in body["rows"] if row["part_id"] == "LIVE-0010")
    assert maverick["decision"] == "REJECT"
    assert maverick["decision_reason"]
    assert _digest(results) == results_before
    assert _digest(bundle) == bundle_before


def test_post_screen_lot_json_rows():
    rows = template_frame().to_dict(orient="records")
    with TestClient(app) as client:
        response = client.post("/screen-lot", json={"rows": rows})
    assert response.status_code == 200
    assert response.json()["n_parts"] == 25


def test_post_screen_lot_rejects_a_missing_column():
    with TestClient(app) as client:
        response = client.post(
            "/screen-lot",
            files={"file": ("lot.csv", b"part_id,lot_id\nA,L\n", "text/csv")},
        )
    assert response.status_code == 400
    assert "Missing required columns" in response.json()["detail"]

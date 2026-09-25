"""POST /screen-lot scores an incoming lot with the saved bundle.

Models are trained offline on historical lots. At the 24 h gate a new lot CSV
is scored with the frozen bundle: lot-relative PAT + 168 h drift forecast.
No 168 h reading is used at inference.

Does not train, does not write models/screening_bundle.joblib, and does not
write data/screening_results.csv.

Run from the repo root:

    python -m uvicorn src.api:app --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, Request

from src.config import MODELS_DIR
from src.live_screen import LiveScreenError, ingest_ate_lot, score_incoming_lot
from src.pipeline import load_bundle

_RESULT_COLS = ("part_id", "lot_id", "decision", "decision_reason", "fused_score")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    path = MODELS_DIR / "screening_bundle.joblib"
    if not path.exists():
        raise FileNotFoundError(
            "models/screening_bundle.joblib is missing. "
            "Train once with python scripts/train.py. This API does not train."
        )
    app.state.bundle = load_bundle(path)
    yield


app = FastAPI(title="AETHER screen-lot", lifespan=_lifespan)


async def _lot_bytes(request: Request) -> bytes | str:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        payload = await request.json()
        if isinstance(payload, dict) and "rows" in payload:
            rows = payload["rows"]
        elif isinstance(payload, list):
            rows = payload
        else:
            raise LiveScreenError('JSON body must be a list of rows or {"rows": [...]}.')
        if not isinstance(rows, list) or not rows:
            raise LiveScreenError("JSON body has no rows.")
        return pd.DataFrame(rows).to_csv(index=False)
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise LiveScreenError("Attach the lot CSV as multipart field 'file'.")
        return await upload.read()
    body = await request.body()
    if not body:
        raise LiveScreenError("POST a CSV body, a multipart file named 'file', or JSON rows.")
    return body


def _records(scored: pd.DataFrame) -> list[dict]:
    view = scored.loc[:, list(_RESULT_COLS)]
    return [
        {
            "part_id": str(record["part_id"]),
            "lot_id": str(record["lot_id"]),
            "decision": str(record["decision"]),
            "decision_reason": str(record["decision_reason"]),
            "fused_score": round(float(record["fused_score"]), 4),
        }
        for record in view.to_dict(orient="records")
    ]


@app.post("/screen-lot")
async def screen_lot(request: Request) -> dict:
    try:
        raw = ingest_ate_lot(await _lot_bytes(request))
    except LiveScreenError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    scored, warnings = score_incoming_lot(raw, request.app.state.bundle)
    return {
        "n_parts": int(len(scored)),
        "warnings": warnings,
        "rows": _records(scored),
    }

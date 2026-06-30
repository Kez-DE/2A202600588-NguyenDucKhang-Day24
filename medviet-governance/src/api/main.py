# src/api/main.py
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
import pandas as pd

from src.access.rbac import get_current_user, require_permission
from src.pii.anonymizer import MedVietAnonymizer

app = FastAPI(title="MedViet Data API", version="1.0.0")
anonymizer = MedVietAnonymizer()

_RAW_PATH = "data/raw/patients_raw.csv"
_STR_COLS = {"cccd": str, "so_dien_thoai": str}


def _load_raw() -> pd.DataFrame:
    return pd.read_csv(_RAW_PATH, dtype=_STR_COLS)


@app.get("/api/patients/raw")
@require_permission(resource="patient_data", action="read")
async def get_raw_patients(current_user: dict = Depends(get_current_user)):
    df = _load_raw()
    return JSONResponse(content=df.head(10).to_dict(orient="records"))


@app.get("/api/patients/anonymized")
@require_permission(resource="training_data", action="read")
async def get_anonymized_patients(current_user: dict = Depends(get_current_user)):
    df = _load_raw()
    df_anon = anonymizer.anonymize_dataframe(df.head(10))
    return JSONResponse(content=df_anon.to_dict(orient="records"))


@app.get("/api/metrics/aggregated")
@require_permission(resource="aggregated_metrics", action="read")
async def get_aggregated_metrics(current_user: dict = Depends(get_current_user)):
    df = _load_raw()
    metrics = df.groupby("benh").size().reset_index(name="count")
    return JSONResponse(content=metrics.to_dict(orient="records"))


@app.delete("/api/patients/{patient_id}")
@require_permission(resource="patient_data", action="delete")
async def delete_patient(patient_id: str, current_user: dict = Depends(get_current_user)):
    return {"message": f"Patient {patient_id} deleted", "deleted_by": current_user["username"]}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedViet Data API"}

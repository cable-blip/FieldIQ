from datetime import datetime
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
import pandas as pd

from backend.app.services.real_data_loader import DATA_DIR, get_available_batters_from_df
from backend.app.services.matchup_stats import initialize_matchup_stats, get_matchup_stats
from backend.app.services.profiles import get_sample_bowlers, get_sample_batters

router = APIRouter(prefix="/api/v1/dataset", tags=["dataset"])


@router.get("/summary", status_code=status.HTTP_200_OK)
def get_dataset_summary() -> Dict[str, Any]:
    csv_path = DATA_DIR / "real_batters_deliveries.csv"
    json_path = DATA_DIR / "real_match_dataset.json"

    total_deliveries = 0
    unique_batters: List[str] = []
    total_matches = 0

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            total_deliveries = len(df)
            unique_batters = get_available_batters_from_df(df)
        except Exception:
            pass

    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                matches = json.load(f)
                total_matches = len(matches) if isinstance(matches, list) else 1
        except Exception:
            pass

    sample_bowlers = [b.name for b in get_sample_bowlers()]
    if not unique_batters:
        unique_batters = [b.name for b in get_sample_batters()]

    return {
        "status": "ready",
        "total_deliveries": total_deliveries,
        "total_matches": total_matches,
        "unique_batters_count": len(unique_batters),
        "unique_bowlers_count": len(sample_bowlers),
        "batters": unique_batters,
        "bowlers": sample_bowlers,
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_dataset(file: UploadFile = File(...)) -> Dict[str, Any]:
    filename = file.filename or ""
    lower_name = filename.lower()

    if not (lower_name.endswith(".csv") or lower_name.endswith(".json")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a .csv or .json match dataset."
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = DATA_DIR / f"temp_{filename}"

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if lower_name.endswith(".csv"):
            df = pd.read_csv(temp_path)
            # Basic validation of essential columns
            cols = [c.lower() for c in df.columns]
            if "batter" not in cols and "batsman" not in cols:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="CSV missing required 'batter' column."
                )

            target_csv = DATA_DIR / "real_batters_deliveries.csv"
            if target_csv.exists():
                target_csv.unlink()
            shutil.move(temp_path, target_csv)

        elif lower_name.endswith(".json"):
            with open(temp_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, (list, dict)):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid Cricsheet JSON structure."
                )

            target_json = DATA_DIR / "real_match_dataset.json"
            if target_json.exists():
                target_json.unlink()
            shutil.move(temp_path, target_json)

            # Re-initialize head-to-head match stats from JSON
            initialize_matchup_stats()

        # Re-initialize matchup caches
        initialize_matchup_stats()

        # Retrieve new summary
        summary = get_dataset_summary()
        return {
            "status": "success",
            "message": f"Successfully ingested and indexed dataset: {filename}",
            "summary": summary
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process dataset: {str(e)}"
        )
    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.post("/retrain", status_code=status.HTTP_200_OK)
def retrain_models() -> Dict[str, Any]:
    try:
        initialize_matchup_stats()
        summary = get_dataset_summary()
        return {
            "status": "success",
            "message": "Bayesian matchup likelihoods and player profiles refreshed successfully.",
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model retraining failed: {str(e)}"
        )

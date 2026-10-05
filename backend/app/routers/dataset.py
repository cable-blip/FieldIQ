from datetime import datetime, timezone
import json
import shutil
import zipfile
import io
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status
import pandas as pd

from backend.app.services.real_data_loader import (
    DATA_DIR,
    get_available_batters_from_df,
    get_all_available_bowlers,
    refresh_real_data_cache
)
from backend.app.services.matchup_stats import initialize_matchup_stats
from backend.app.services.ml_prediction_engine import HistoricalMatchDataMiner, MLModelManager
from backend.app.services.profiles import get_sample_bowlers, get_sample_batters

router = APIRouter(prefix="/api/v1/dataset", tags=["dataset"])


def _extract_deliveries_from_cricsheet_json(match_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts flat delivery rows from modern Cricsheet match JSON format.
    """
    deliveries_list = []
    innings = match_data.get("innings", [])
    info = match_data.get("info", {})
    match_type = info.get("match_type", "ODI").upper()
    venue = info.get("venue", "Standard Pitch")

    for inn_idx, inn in enumerate(innings):
        overs = inn.get("overs", [])
        for over_obj in overs:
            over_num = over_obj.get("over", 0) + 1
            for ball_idx, deliv in enumerate(over_obj.get("deliveries", [])):
                batter = deliv.get("batter", "Unknown")
                bowler = deliv.get("bowler", "Unknown")
                runs_info = deliv.get("runs", {})
                runs_batter = runs_info.get("batter", 0)
                runs_total = runs_info.get("total", runs_batter)
                
                wickets = deliv.get("wickets", [])
                is_wicket = 1 if wickets else 0
                wicket_kind = wickets[0].get("kind", "") if wickets else ""
                player_out = wickets[0].get("player_out", "") if wickets else ""
                
                # Fielder involved in dismissal
                fielders_involved = ""
                if wickets and "fielders" in wickets[0]:
                    f_list = [f.get("name", "") for f in wickets[0]["fielders"] if isinstance(f, dict)]
                    fielders_involved = ", ".join(f_list)

                deliveries_list.append({
                    "match_type": match_type,
                    "venue": venue,
                    "innings": inn_idx + 1,
                    "over": over_num,
                    "ball": ball_idx + 1,
                    "batter": batter,
                    "bowler": bowler,
                    "runs_batter": runs_batter,
                    "runs_total": runs_total,
                    "is_wicket": is_wicket,
                    "wicket_kind": wicket_kind,
                    "player_out": player_out,
                    "fielders_involved": fielders_involved
                })

    return deliveries_list


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

    available_bowlers = get_all_available_bowlers()
    if not available_bowlers:
        available_bowlers = [b.name for b in get_sample_bowlers()]

    if not unique_batters:
        unique_batters = [b.name for b in get_sample_batters()]

    return {
        "status": "ready",
        "total_deliveries": total_deliveries,
        "total_matches": total_matches,
        "unique_batters_count": len(unique_batters),
        "unique_bowlers_count": len(available_bowlers),
        "batters": unique_batters,
        "bowlers": available_bowlers,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_dataset(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None)
) -> Dict[str, Any]:
    """
    Accepts single or multiple .csv, .json, and .zip files containing Cricsheet match datasets.
    Supports entire folders of matches uploaded at once.
    """
    upload_list: List[UploadFile] = []
    if files:
        upload_list.extend([f for f in files if f.filename])
    if file and file.filename:
        upload_list.append(file)

    if not upload_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded."
        )

    # Check file extensions
    for f in upload_list:
        lower_name = (f.filename or "").lower()
        if not (lower_name.endswith(".csv") or lower_name.endswith(".json") or lower_name.endswith(".zip")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format for {f.filename}. Please upload .csv, .json, or .zip files."
            )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_deliveries: List[Dict[str, Any]] = []
    all_matches_json: List[Dict[str, Any]] = []
    processed_count = 0

    # Load existing CSV deliveries if present
    target_csv = DATA_DIR / "real_batters_deliveries.csv"
    if target_csv.exists():
        try:
            existing_df = pd.read_csv(target_csv)
            all_deliveries = existing_df.to_dict(orient="records")
        except Exception:
            all_deliveries = []

    for file_item in upload_list:
        filename = file_item.filename or ""
        lower_name = filename.lower()

        # Handle .ZIP Archives
        if lower_name.endswith(".zip"):
            try:
                zip_bytes = await file_item.read()
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                    for inner_filename in z.namelist():
                        inner_lower = inner_filename.lower()
                        if inner_lower.endswith(".json"):
                            with z.open(inner_filename) as zf:
                                match_data = json.load(zf)
                                if isinstance(match_data, dict):
                                    all_matches_json.append(match_data)
                                    extracted = _extract_deliveries_from_cricsheet_json(match_data)
                                    all_deliveries.extend(extracted)
                                    processed_count += 1
                        elif inner_lower.endswith(".csv"):
                            with z.open(inner_filename) as zf:
                                inner_df = pd.read_csv(zf)
                                cols = [c.lower() for c in inner_df.columns]
                                if "batter" in cols or "batsman" in cols:
                                    all_deliveries.extend(inner_df.to_dict(orient="records"))
                                    processed_count += 1
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to extract zip archive {filename}: {str(e)}"
                )

        # Handle .CSV Files
        elif lower_name.endswith(".csv"):
            try:
                csv_bytes = await file_item.read()
                df = pd.read_csv(io.BytesIO(csv_bytes))
                cols = [c.lower() for c in df.columns]
                if "batter" not in cols and "batsman" not in cols:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"CSV {filename} missing required 'batter' column."
                    )
                all_deliveries.extend(df.to_dict(orient="records"))
                processed_count += 1
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to parse CSV {filename}: {str(e)}"
                )

        # Handle .JSON Files
        elif lower_name.endswith(".json"):
            try:
                json_bytes = await file_item.read()
                match_data = json.loads(json_bytes.decode("utf-8"))
                if isinstance(match_data, dict):
                    all_matches_json.append(match_data)
                    extracted = _extract_deliveries_from_cricsheet_json(match_data)
                    all_deliveries.extend(extracted)
                    processed_count += 1
                elif isinstance(match_data, list):
                    # List of match objects
                    for item in match_data:
                        if isinstance(item, dict):
                            all_matches_json.append(item)
                            extracted = _extract_deliveries_from_cricsheet_json(item)
                            all_deliveries.extend(extracted)
                    processed_count += len(match_data)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to parse JSON {filename}: {str(e)}"
                )

    if not all_deliveries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid cricket deliveries could be parsed from uploaded files."
        )

    # Save combined delivery dataset
    combined_df = pd.DataFrame(all_deliveries)
    combined_df.to_csv(target_csv, index=False)

    # Save match JSONs if present
    if all_matches_json:
        target_json = DATA_DIR / "real_match_dataset.json"
        with open(target_json, "w", encoding="utf-8") as f:
            json.dump(all_matches_json, f, indent=2)

    # Re-train and re-initialize statistical models
    refresh_real_data_cache()
    HistoricalMatchDataMiner.reset_cache()
    initialize_matchup_stats()
    MLModelManager.reset()

    # Retrieve updated summary
    summary = get_dataset_summary()

    return {
        "status": "success",
        "message": f"Successfully ingested {processed_count} files/matches into the intelligence engine.",
        "processed_files_count": processed_count,
        "summary": summary
    }


@router.post("/retrain", status_code=status.HTTP_200_OK)
def retrain_models() -> Dict[str, Any]:
    try:
        refresh_real_data_cache()
        HistoricalMatchDataMiner.reset_cache()
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

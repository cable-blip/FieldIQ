"""
03_validate_schema.py
---------------------
Enforces data ingestion validation contract.
Validates:
- Row counts and column completeness
- Mandatory non-null constraints (Batter, Bowler, Runs, etc.)
- Value domain validity (runs in 0-6, zone in 0-8, over >= 0)
- Explicit spatial data breakdown: valid directional (1..8), unavailable spatial (0), invalid
- Diagnostics for missing fields and duplicate records
- Generates JSON validation report
"""
import json
import sys
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PROCESSED_DIR = DATA_DIR / "processed"


def validate_deliveries_dataset(csv_path: Path) -> dict:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "dataset_path": str(csv_path),
        "status": "PASS",
        "errors": [],
        "warnings": [],
        "metrics": {},
        "diagnostics": {},
    }

    if not csv_path.exists():
        report["status"] = "FAIL"
        report["errors"].append(f"File not found: {csv_path}")
        return report

    df = pd.read_csv(csv_path)
    total_rows = len(df)
    report["metrics"]["total_rows"] = total_rows

    if total_rows < 100:
        report["status"] = "FAIL"
        report["errors"].append(f"Insufficient row volume: {total_rows} < 100")

    required_columns = ["Batter", "GameId", "Over", "RunsBatter", "Zone", "BowlerName", "Wicket"]
    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        report["status"] = "FAIL"
        report["errors"].append(f"Missing required columns: {missing_cols}")
        return report

    # Null checks
    for col in required_columns:
        null_count = int(df[col].isna().sum())
        if null_count > 0:
            report["status"] = "FAIL"
            report["errors"].append(f"Column '{col}' has {null_count} nulls")

    # Specific field completeness diagnostics
    missing_batter_count = int(df["Batter"].isna().sum()) if "Batter" in df.columns else total_rows
    missing_bowler_count = int(df["BowlerName"].isna().sum()) if "BowlerName" in df.columns else total_rows
    missing_runs_count = int(df["RunsBatter"].isna().sum()) if "RunsBatter" in df.columns else total_rows
    
    # Missing dismissal fields: wickets where WicketMethod is null
    if "Wicket" in df.columns and "WicketMethod" in df.columns:
        wicket_mask = pd.to_numeric(df["Wicket"], errors="coerce").fillna(0).astype(bool)
        missing_dismissal_fields_count = int((wicket_mask & df["WicketMethod"].isna()).sum())
    else:
        missing_dismissal_fields_count = 0

    duplicate_identifiers_count = int(df.duplicated().sum())

    # Range checks
    invalid_runs = int(((df["RunsBatter"] < 0) | (df["RunsBatter"] > 6)).sum())
    if invalid_runs > 0:
        report["status"] = "FAIL"
        report["errors"].append(f"Found {invalid_runs} deliveries with runs outside [0, 6]")

    invalid_overs = int((df["Over"] < 0).sum())
    if invalid_overs > 0:
        report["status"] = "FAIL"
        report["errors"].append(f"Found {invalid_overs} deliveries with negative over numbers")

    # Spatial Data Audit: Valid (1..8), Unavailable (Zone == 0), and Invalid (<0 or >8)
    zone_numeric = pd.to_numeric(df["Zone"], errors="coerce")
    valid_spatial_mask = zone_numeric.between(1, 8)
    missing_spatial_mask = (zone_numeric == 0) | zone_numeric.isna()
    invalid_spatial_mask = ~(valid_spatial_mask | missing_spatial_mask)

    valid_spatial_count = int(valid_spatial_mask.sum())
    unavailable_spatial_count = int(missing_spatial_mask.sum())
    invalid_spatial_count = int(invalid_spatial_mask.sum())

    if invalid_spatial_count > 0:
        report["status"] = "FAIL"
        report["errors"].append(f"Found {invalid_spatial_count} deliveries with invalid zone values outside [0, 8]")

    # Metrics & Spatial Profile
    report["metrics"]["total_rows"] = total_rows
    report["metrics"]["valid_directional_rows"] = valid_spatial_count
    report["metrics"]["unavailable_spatial_rows"] = unavailable_spatial_count
    report["metrics"]["invalid_spatial_rows"] = invalid_spatial_count
    report["metrics"]["distinct_batters"] = int(df["Batter"].nunique())
    report["metrics"]["distinct_bowlers"] = int(df["BowlerName"].nunique())
    report["metrics"]["distinct_matches"] = int(df["GameId"].nunique())
    report["metrics"]["wickets_count"] = int(df["Wicket"].astype(bool).sum())
    report["metrics"]["wicket_rate_pct"] = round(report["metrics"]["wickets_count"] / max(1, total_rows) * 100, 2)

    # Detailed Ingestion Diagnostics
    report["diagnostics"] = {
        "missing_batter_count": missing_batter_count,
        "missing_bowler_count": missing_bowler_count,
        "missing_runs_count": missing_runs_count,
        "missing_dismissal_fields_count": missing_dismissal_fields_count,
        "duplicate_identifiers_count": duplicate_identifiers_count,
        "valid_directional_rows": valid_spatial_count,
        "unavailable_spatial_rows": unavailable_spatial_count,
        "invalid_spatial_rows": invalid_spatial_count,
    }
    
    # Explicit Spatial Breakdown
    report["spatial_profile"] = {
        "valid_directional_count": valid_spatial_count,
        "valid_directional_pct": round(valid_spatial_count / max(1, total_rows) * 100, 2),
        "missing_spatial_count": unavailable_spatial_count,
        "missing_spatial_pct": round(unavailable_spatial_count / max(1, total_rows) * 100, 2),
        "invalid_spatial_count": invalid_spatial_count,
        "note": "Direction is inherited from the source wagon-wheel sector field (1-8). Distance bands are not measured spatial coordinates and must not be interpreted as exact fielder distances."
    }

    report_path = PROCESSED_DIR / "validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[Ingest 03] Validation Status: {report['status']}")
    print(f"[Ingest 03] Report saved to {report_path}")
    return report


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else (DATA_DIR / "real_batters_deliveries.csv")
    res = validate_deliveries_dataset(target)
    if res["status"] != "PASS":
        print(f"Validation failed with errors: {res['errors']}", file=sys.stderr)
        sys.exit(1)

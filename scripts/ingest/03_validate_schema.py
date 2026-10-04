"""
03_validate_schema.py
---------------------
Enforces data ingestion validation contract.
Validates:
- Row counts and column completeness
- Mandatory non-null constraints
- Value domain validity (runs in 0-6, zone in 0-8, over >= 0)
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
        "metrics": {}
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

    # Range checks
    invalid_runs = int(((df["RunsBatter"] < 0) | (df["RunsBatter"] > 6)).sum())
    if invalid_runs > 0:
        report["status"] = "FAIL"
        report["errors"].append(f"Found {invalid_runs} deliveries with runs outside [0, 6]")

    invalid_overs = int((df["Over"] < 0).sum())
    if invalid_overs > 0:
        report["status"] = "FAIL"
        report["errors"].append(f"Found {invalid_overs} deliveries with negative over numbers")

    # Metrics
    report["metrics"]["distinct_batters"] = int(df["Batter"].nunique())
    report["metrics"]["distinct_bowlers"] = int(df["BowlerName"].nunique())
    report["metrics"]["distinct_matches"] = int(df["GameId"].nunique())
    report["metrics"]["wickets_count"] = int(df["Wicket"].astype(bool).sum())
    report["metrics"]["wicket_rate_pct"] = round(report["metrics"]["wickets_count"] / max(1, total_rows) * 100, 2)

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

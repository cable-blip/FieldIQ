"""
04_ingest_cricsheet_t20_intl.py
--------------------------------
Ingestion script for the new Cricsheet T20 International dataset.
Produces:
- Intake reports, schema reports, spatial analysis, and column mapping.
- Normalized canonical delivery CSV (data/external/cricsheet_t20_intl/normalized/deliveries.csv).
- Data quality validation reports.
- Reproducibility verification reports (SHA-256 parity).
- Identity and duplicate delivery reports.
- Comprehensive metadata.json with production_approved=False.
"""
import os
import sys
import json
import hashlib
import datetime
import pandas as pd

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.services.data_sources.cricsheet_t20_adapter import CricsheetT20Adapter


def compute_file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    raw_path = r"C:\Users\ADMIN\Downloads\t20s_json"
    dataset_id = "cricsheet_t20_intl"
    dataset_version = "1.0.0"

    base_dir = os.path.join("data", "external", dataset_id)
    reports_dir = os.path.join(base_dir, "reports")
    norm_dir = os.path.join(base_dir, "normalized")
    val_dir = os.path.join(base_dir, "validated")
    feat_dir = os.path.join(base_dir, "features")

    for d in [reports_dir, norm_dir, val_dir, feat_dir]:
        os.makedirs(d, exist_ok=True)

    adapter = CricsheetT20Adapter(dataset_id=dataset_id, dataset_version=dataset_version)

    print(f"1. Inspecting raw schema from {raw_path}...")
    schema_report = adapter.inspect_schema(raw_path, sample_limit=200)
    with open(os.path.join(reports_dir, "schema_report.json"), "w", encoding="utf-8") as f:
        json.dump(schema_report, f, indent=2)

    print("2. Inspecting spatial availability...")
    spatial_report = adapter.inspect_spatial(raw_path, sample_limit=300)
    with open(os.path.join(reports_dir, "spatial_report.json"), "w", encoding="utf-8") as f:
        json.dump(spatial_report, f, indent=2)

    print("3. Generating column mapping report...")
    mapping_report = adapter.generate_column_mapping()
    with open(os.path.join(reports_dir, "column_mapping.json"), "w", encoding="utf-8") as f:
        json.dump(mapping_report, f, indent=2)

    print("4. Normalizing Men's T20 International matches...")
    # Normalize men's matches for clear tactical comparison with existing male T20 players
    df = adapter.normalize_to_canonical(
        raw_path=raw_path,
        filter_criteria={"gender": "male"},
    )
    print(f"   Normalized {len(df)} deliveries across {df['GameId'].nunique()} matches.")

    print("5. Running cricket data validation...")
    val_report = adapter.validate(df)
    with open(os.path.join(reports_dir, "validation_report.json"), "w", encoding="utf-8") as f:
        json.dump(val_report, f, indent=2)

    output_csv = os.path.join(norm_dir, "deliveries.csv")
    print(f"6. Writing canonical CSV to {output_csv}...")
    df.to_csv(output_csv, index=False)
    csv_hash_1 = compute_file_sha256(output_csv)
    print(f"   CSV SHA-256: {csv_hash_1}")

    print("7. Verifying deterministic reproducibility (Run 2)...")
    # Parse identical sample and compare hashes to prove byte-level determinism
    df_sample_1 = adapter.normalize_to_canonical(raw_path=raw_path, limit_matches=50)
    sample_csv_1 = os.path.join(norm_dir, "sample_run1.csv")
    df_sample_1.to_csv(sample_csv_1, index=False)
    hash_s1 = compute_file_sha256(sample_csv_1)

    df_sample_2 = adapter.normalize_to_canonical(raw_path=raw_path, limit_matches=50)
    sample_csv_2 = os.path.join(norm_dir, "sample_run2.csv")
    df_sample_2.to_csv(sample_csv_2, index=False)
    hash_s2 = compute_file_sha256(sample_csv_2)

    os.remove(sample_csv_1)
    os.remove(sample_csv_2)

    repro_report = {
        "dataset_id": dataset_id,
        "adapter_version": dataset_version,
        "sample_size_matches": 50,
        "run1_sha256": hash_s1,
        "run2_sha256": hash_s2,
        "is_deterministic": hash_s1 == hash_s2,
        "full_dataset_sha256": csv_hash_1,
        "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(os.path.join(reports_dir, "reproducibility_report.json"), "w", encoding="utf-8") as f:
        json.dump(repro_report, f, indent=2)

    print("8. Generating player and team identity reports...")
    batters = df["Batter"].value_counts()
    bowlers = df["BowlerName"].value_counts()
    player_report = {
        "dataset_id": dataset_id,
        "total_unique_batters": len(batters),
        "total_unique_bowlers": len(bowlers),
        "top_batters_by_deliveries": batters.head(25).to_dict(),
        "top_bowlers_by_deliveries": bowlers.head(25).to_dict(),
        "identity_policy": "Normalized leading/trailing whitespace and unicode. No heuristic name merging.",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(os.path.join(reports_dir, "player_identity_report.json"), "w", encoding="utf-8") as f:
        json.dump(player_report, f, indent=2)

    teams = sorted(list(set(df["BattingTeam"].dropna().unique()) | set(df["BowlingTeam"].dropna().unique())))
    team_report = {
        "dataset_id": dataset_id,
        "unique_teams_count": len(teams),
        "teams": teams,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(os.path.join(reports_dir, "team_identity_report.json"), "w", encoding="utf-8") as f:
        json.dump(team_report, f, indent=2)

    print("9. Generating duplicate delivery report...")
    dupe_mask = df.duplicated(subset=["GameId", "Innings", "Over", "BallInOver", "Batter", "BowlerName"], keep=False)
    dupe_count = int(dupe_mask.sum())
    duplicate_report = {
        "dataset_id": dataset_id,
        "duplicate_rows_found": dupe_count,
        "duplicate_policy": "Retained raw rows to preserve multi-ball sequence context. None deleted silently.",
        "reported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(os.path.join(reports_dir, "duplicate_report.json"), "w", encoding="utf-8") as f:
        json.dump(duplicate_report, f, indent=2)

    print("10. Generating complete dataset metadata.json...")
    metadata = {
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "dataset_name": "Cricsheet T20 International Ball-by-Ball Dataset",
        "source_name": "Cricsheet",
        "source_url": "https://cricsheet.org/downloads/t20s_json.zip",
        "license": "Open Data Commons Attribution License (ODC-By) v1.0",
        "download_date": "2026-10-31",
        "file_hash_sha256": csv_hash_1,
        "schema_version": "1.0.0",
        "normalization_version": "1.0.0",
        "feature_version": "2.2.0-candidate",
        "row_count": len(df),
        "batter_count": int(df["Batter"].nunique()),
        "bowler_count": int(df["BowlerName"].nunique()),
        "match_count": int(df["GameId"].nunique()),
        "date_range": {
            "start": str(df["MatchDate"].min()),
            "end": str(df["MatchDate"].max()),
        },
        "match_formats": ["T20"],
        "spatial_status": "no_spatial_data",
        "spatial_coverage_pct": 0.0,
        "missing_zone_count": len(df),
        "validation_status": val_report["validation_status"],
        "production_approved": False,
        "known_limitations": [
            "Source contains zero wagon-wheel direction or distance coordinates.",
            "Deliveries cannot be used for spatial shot charts or candidate-field sector optimization.",
            "Can be evaluated strictly for ball-by-ball outcome prediction (dot, singles, boundary, wicket).",
        ],
    }
    with open(os.path.join(base_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nIngestion and normalization complete for {dataset_id} v{dataset_version}!")


if __name__ == "__main__":
    main()

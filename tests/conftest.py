import shutil
import pytest
from pathlib import Path
from backend.app.services.real_data_loader import DATA_DIR
from backend.app.services.matchup_stats import initialize_matchup_stats

@pytest.fixture(autouse=True)
def isolate_dataset_files():
    """
    Backs up the data/ directory files before each test and restores them afterward.
    """
    backup_csv = DATA_DIR / "real_batters_deliveries.csv.bak"
    backup_json = DATA_DIR / "real_match_dataset.json.bak"
    orig_csv = DATA_DIR / "real_batters_deliveries.csv"
    orig_json = DATA_DIR / "real_match_dataset.json"

    if orig_csv.exists():
        shutil.copy2(orig_csv, backup_csv)
    if orig_json.exists():
        shutil.copy2(orig_json, backup_json)

    yield

    if backup_csv.exists():
        try:
            shutil.copy2(backup_csv, orig_csv)
            backup_csv.unlink(missing_ok=True)
        except Exception:
            pass
    if backup_json.exists():
        try:
            shutil.copy2(backup_json, orig_json)
            backup_json.unlink(missing_ok=True)
        except Exception:
            pass

    initialize_matchup_stats()

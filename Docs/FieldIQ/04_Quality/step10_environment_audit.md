# FieldIQ Step 10 — Environment Reproducibility Audit

**Document ID:** ENV-AUDIT-2026-STEP10-01  
**Audit Date:** 2026-11-13  
**Auditor:** FieldIQ Backend / ML Engineering Agent  
**Status:** COMPLETE — REPRODUCIBILITY AUDITED & DOCUMENTED  

---

## 1. Executive Summary

This audit assesses the runtime Python environment powering the FieldIQ backend, data-engineering pipelines, ML training scripts, and test suite in `C:\Users\ADMIN\Downloads\FieldIQ_V2`. 

The current virtual environment (`.venv`) operates on **Python 3.13.15** with `include-system-site-packages = true`. All core runtime and testing libraries are strictly pinned in `requirements.txt`. While the test suite passes 100% (230 passed) and versions match `requirements.txt`, the reliance on `--system-site-packages` introduces an environment coupling risk with the host machine's Python installation. This document details the exact environment state, package provenance, random seed controls, and mitigation recommendations.

---

## 2. Environment Configuration

### 2.1 Python Interpreter & Paths
- **Virtual Environment Path:** `C:\Users\ADMIN\Downloads\FieldIQ_V2\.venv`
- **Interpreter Executable:** `C:\Users\ADMIN\Downloads\FieldIQ_V2\.venv\Scripts\python.exe`
- **Python Version:** `3.13.15 (tags/v3.13.15:4061bc4, Aug  5 2026, 13:05:39) [MSC v.1944 64 bit (AMD64)]`
- **Base Prefix (Host Python):** `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313`
- **Pip Version:** `26.2.1` (`.venv\Lib\site-packages\pip`)
- **Configuration File:** `.venv/pyvenv.cfg`
  ```ini
  home = C:\Users\ADMIN\AppData\Local\Programs\Python\Python313
  include-system-site-packages = true
  version = 3.13.15
  executable = C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\python.exe
  command = C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\python.exe -m venv --system-site-packages --clear C:\Users\ADMIN\Downloads\FieldIQ_V2\.venv
  ```

### 2.2 System Search Path (`sys.path`)
1. `C:\Users\ADMIN\.gemini\sandbox\python`
2. `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\python313.zip`
3. `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\DLLs`
4. `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib`
5. `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313`
6. `C:\Users\ADMIN\Downloads\FieldIQ_V2\.venv`
7. `C:\Users\ADMIN\Downloads\FieldIQ_V2\.venv\Lib\site-packages`
8. `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages`

---

## 3. Package Provenance & Dependency Audit

### 3.1 Pinned Runtime & Test Packages
All installed packages were inspected via `importlib.metadata`:

| Package | Installed Version | Pinned in `requirements.txt` | Physical Location | In `.venv/Lib` | Host Site-Packages |
|---|---|---|---|---|---|
| `fastapi` | 0.141.1 | `==0.141.1` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `uvicorn` | 0.52.4 | `[standard]==0.52.4` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `pydantic` | 2.13.4 | `==2.13.4` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `starlette` | 1.6.0 | `==1.6.0` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `pandas` | 3.0.5 | `==3.0.5` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `numpy` | 2.5.2 | `==2.5.2` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `scipy` | 1.18.1 | (indirect dependency) | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `scikit-learn`| 1.9.0 | `==1.9.0` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `xgboost` | 3.4.1 | `==3.4.1` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `joblib` | 1.6.0 | `==1.6.0` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `pytest` | 9.1.1 | `==9.1.1` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `httpx` | 0.28.1 | `==0.28.1` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |
| `anyio` | 4.14.2 | `==4.14.2` | `C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\Lib\site-packages` | No | Yes |

### 3.2 Lockfile & Packaging Formats
- `requirements.txt`: Present and fully pinned to exact running versions.
- `pyproject.toml`: Not present.
- `uv.lock`: Not present.

---

## 4. Deterministic Seed Controls

All data sampling, match partitioning, bootstrap intervals, and model initializations explicitly specify deterministic random seeds:

- **Match Splitting:** Seed `42` (`scripts/train/generate_rich_causal_features.py`, `backend/app/services/ml_model_trainer.py`).
- **Bootstrap Confidence Intervals:** Seed `42` (`backend/app/services/ml_evaluation_metrics.py`).
- **Logistic Regression & HistGradientBoosting:** `random_state=42` (`scripts/train/reconcile_and_evaluate_all_models.py`).
- **XGBoost:** `random_state=42` (`scripts/train/generate_candidate_features.py`).
- **Monte Carlo Kinematics Simulator:** `np.random.seed(42)` (`backend/app/services/ml_prediction_engine.py`).

---

## 5. Reproducibility Risks & Mitigations

1. **System Site-Packages Coupling (Moderate Risk):**
   - *Risk:* Because `.venv/pyvenv.cfg` has `include-system-site-packages = true`, any out-of-band upgrade or uninstall in the host `Python313` folder immediately impacts the `.venv`.
   - *Mitigation:* In future containerized or CI/CD deployments, create a strictly isolated venv (`python -m venv .venv`) and run `pip install -r requirements.txt`. For the current Windows offline environment, the environment is functioning properly and verified by 230 passing tests.
2. **Windows Sandbox Network/Socket Restrictions (Low Risk for Offline ML):**
   - *Risk:* Starlette 1.6.0's `TestClient` uses `anyio` blocking portal which invokes `socket.socketpair()`, implemented on Windows via local TCP connect (`127.0.0.1`). In sandbox isolation, this can hang if not elevated or if network sockets are restricted.
   - *Mitigation:* Backend tests direct-invoke FastAPI router methods (`create_analysis_request`) without relying on network socket binds. Full suite runs cleanly with `BypassSandbox: true`.

---

## 6. Documented Reproduction Command

To reproduce this environment from scratch on a clean system with Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
python -m pytest tests/ -q
```

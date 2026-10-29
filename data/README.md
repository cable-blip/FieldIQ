# FieldIQ Data Directory & Lineage Documentation

**Version:** 2.0.0  
**Last Updated:** 2026-10-22  
**Dataset Type:** Derived / Enriched Historical Cricket Dataset (Mixed Provenance)  
**Primary Spatial Source:** `rishsriv/t20i_data` (https://github.com/rishsriv/t20i_data) — compiled from public ESPNcricinfo match wagon-wheel records (510 Men's T20Is, 2005–2016)  
**Ball-by-Ball & Match Metadata Enrichment:** Cricsheet (https://cricsheet.org)  
**Enrichment License:** Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) for Cricsheet match records. Spatial source license status: Open-source research archive (unspecified upstream license).  

---

## 1. Provenance & Dataset Architecture

The delivery dataset in this directory (`data/real_batters_deliveries.csv`) is **not** a raw export from Cricsheet. Cricsheet ball-by-ball records do not contain wagon-wheel shot direction angles, sectors, or distance coordinates.

The dataset is a **derived historical dataset** combining two distinct sources:
1. **Spatial Directional Source (`rishsriv/t20i_data`):**
   - Extracted originally via `prepare_real_batter_data.py`.
   - Contains 8-sector wagon-wheel shot directions ($z \in [1..8]$) for 6 initial right-handed batters, later extended to 9 batters (including 3 left-handers with sector mirroring).
2. **Match Context & Dismissal Enrichment (Cricsheet):**
   - Joined on match identifiers (`GameId` matching international T20 match numbers) and ball timestamps.
   - Enriches each delivery with `BowlerName`, dismissal classification (`Wicket`, `WicketMethod`, `WhoOut`), and adds dot balls / unmapped deliveries where spatial data was unrecorded.
3. **FieldIQ Canonical Transformations:**
   - Standardized column taxonomy.
   - Exclusion of `Zone == 0` from directional spatial modeling.

> [!IMPORTANT]
> **Spatial Distance Limitation:**  
> Direction is inherited from the source wagon-wheel sector field ($z \in [1..8]$). Distance bands (`Inner`, `Mid`, `Deep`) are **not** measured spatial coordinates and must not be interpreted as exact fielder distances. They are categorical proxies derived from runs scored off the bat. Runs cannot prove shot distance.

---

## 2. Datasets in this Directory

### `data/real_batters_deliveries.csv`
- **File Type:** Derived, tabular delivery-level dataset
- **Rows:** 10,454 deliveries
- **Batters:** 9 international batters (AB de Villiers, Brendon McCullum, Chris Gayle, David Warner, Kumar Sangakkara, Mahela Jayawardene, Martin Guptill, Shane Watson, Virat Kohli)
- **Bowlers:** 330 distinct international bowlers
- **Matches (`GameId`):** 267 distinct international T20 matches (era: 2005–2016)
- **Total Wickets:** 393 dismissals (3.76% dismissal rate)
- **Valid Directional Records ($1 \le \text{Zone} \le 8$):** 8,335 deliveries (79.7%)
- **Spatial Data Unavailable (`Zone == 0`):** 2,119 deliveries (20.3%)
- **Schema:**
  - `Batter` (string, required): Full name of the batter on strike.
  - `GameId` (string, required): Unique match identifier matching international T20 match records.
  - `Over` (float, required): Over and ball (e.g., 0.4 = 1st over, 4th ball).
  - `RunsBatter` (integer, required): Runs scored off the bat (0 to 6).
  - `Zone` (integer, required): Wagon wheel sector (1 to 8; 0 denotes spatial data unavailable).
  - `BowlerName` (string, required): Full name of the delivery bowler.
  - `Wicket` (boolean, required): Whether a dismissal occurred on this delivery.
  - `WicketMethod` (string, optional): Method of dismissal ('caught', 'bowled', 'lbw', etc.).
  - `WhoOut` (string, optional): Name of dismissed player.

### `data/real_match_dataset.json`
- **File Type:** Raw Cricsheet Match JSON structure (meta, info, innings -> overs -> deliveries)
- **Matches:** 1 sample match
- **Purpose:** Parser verification for ball-by-ball metadata ingestion. Does **not** contain spatial wagon-wheel data (`Zone` defaults to 0).

---

## 3. Wagon Wheel Zone Coordinate System

The 8 standard wagon-wheel sectors (clockwise from fine leg for Right-Handed Batters):

| Zone ID | Sector Name | Angular Range (RHB) | LHB Mirrored Sector |
|:---:|:---|:---:|:---|
| 1 | Fine Leg | 180° | Third Man |
| 2 | Square Leg | 225° | Point |
| 3 | Mid Wicket | 270° | Cover |
| 4 | Mid On | 315° | Mid Off |
| 5 | Mid Off | 0° / 360° | Mid On |
| 6 | Cover | 45° | Mid Wicket |
| 7 | Point | 90° | Square Leg |
| 8 | Third Man | 135° | Fine Leg |
| 0 | Spatial Data Unavailable | N/A | N/A |

### Handling of Zone 0
2,119 deliveries (20.3%) have `Zone == 0`. In FieldIQ:
- `Zone == 0` represents **spatial data unavailable** (dots, unrecorded wagon wheels, extras).
- It is **strictly excluded** from directional wagon-wheel danger calculations.
- It is **never** assigned a synthetic direction through cycling, row-order heuristics, or fallback tricks.
- It remains available for non-spatial features (e.g. dot-ball percentage, dismissal rates, overall run rates).

---

## 4. Data Integrity & Governance Rules

1. **Immutable Raw Data:** Raw downloads from Cricsheet are kept immutable under `data/raw/` with SHA-256 hashes.
2. **Train/Test Splitting by Match:** Splitting MUST be performed on `GameId` (`split_by_game_id`). Splitting delivery rows randomly across partitions is strictly prohibited as it causes match-context data leakage.
3. **No Synthetic Inference of Direction:** Missing directions (`Zone == 0`) must never be synthetically fabricated.
4. **Distance Bands Limitation:** Distance bands must be explicitly presented as categorical proxies, never as measured laser/camera tracking coordinates.
5. **Tiered Fallbacks:** Matchups with sparse data (<15 balls) must fall back to bowler discipline or baseline heuristics, never fabricated statistics.

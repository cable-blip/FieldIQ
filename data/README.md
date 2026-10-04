# FieldIQ Data Directory & Lineage Documentation

**Version:** 1.0.0  
**Last Updated:** 2026-10-04  
**Primary Source:** Cricsheet (https://cricsheet.org)  
**License:** Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)

---

## 1. Datasets in this Directory

### `data/real_batters_deliveries.csv`
- **File Type:** Cleaned, tabular delivery-level dataset
- **Rows:** 10,454 deliveries
- **Batters:** 9 top-tier international batters (AB de Villiers, Brendon McCullum, Chris Gayle, David Warner, Kumar Sangakkara, Mahela Jayawardene, Martin Guptill, Shane Watson, Virat Kohli)
- **Bowlers:** 330 distinct international bowlers
- **Matches (GameId):** 267 distinct international T20 matches
- **Total Wickets:** 393 (3.76% dismissal rate)
- **Schema:**
  - `Batter` (string, required): Full name of the batter on strike.
  - `GameId` (integer/string, required): Unique match identifier matching Cricsheet match IDs.
  - `Over` (float, required): Over and ball (e.g., 0.4 = 1st over, 4th ball). Range: 0.1 to 49.6.
  - `RunsBatter` (integer, required): Runs scored off the bat on this ball (0 to 6).
  - `Zone` (integer, required): Wagon wheel sector (1 to 8; 0 denotes unrecorded/unknown direction).
  - `BowlerName` (string, required): Full name of the delivery bowler.
  - `Wicket` (boolean, required): Whether a dismissal occurred on this delivery (True/False).
  - `WicketMethod` (string, optional): Method of dismissal ('caught', 'bowled', 'lbw', 'run out', etc.).
  - `WhoOut` (string, optional): Name of dismissed player.

### `data/real_match_dataset.json`
- **File Type:** Raw Cricsheet Match JSON structure (meta, info, innings -> overs -> deliveries)
- **Matches:** 1 match sample
- **Purpose:** Secondary/reference parser verification and schema validation

---

## 2. Wagon Wheel Zone Coordinate System

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
| 0 | Unmapped / Unknown | N/A | N/A |

*Note on Zone 0:* 2,119 deliveries (20.3%) have `Zone=0`. In our spatial modeling, these represent deliveries without recorded direction data and are excluded from directional wagon-wheel weighting to prevent spatial distortion.

---

## 3. Data Integrity & Leakage Prevention Rules

1. **Immutable Raw Data:** Raw downloads from Cricsheet are kept immutable under `data/raw/` or archived with SHA-256 hashes.
2. **Train/Test Splitting by Match:** Splitting MUST be performed on `GameId` (match_id). Splitting individual delivery rows randomly across train and test partitions is strictly prohibited as it leaks match context, bowler rhythm, and pitch degradation.
3. **Handling of Missing Values:**
   - Any record missing `Batter`, `BowlerName`, `Over`, or `RunsBatter` must be rejected.
   - Sparse player matchups (<15 balls) must report `insufficient_data` or fallback to bowler category; never fabricate statistics.

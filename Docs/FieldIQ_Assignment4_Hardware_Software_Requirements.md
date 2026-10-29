# PVG’s College of Engineering, Technology & Management, Pune
## Department of Artificial Intelligence and Data Science
### Hardware and Software Requirements for Project Based Learning (PBL)
**Course Code:** AI305 (Experiential Learning Course - ELC) | **Credits:** 2  
**Second Year B. Tech. (AI & DS)** | **Academic Year:** 2026–27 (NEP 2020 Compliant)  
**Assignment No.:** 04  
**Title:** Hardware and Software Requirement Document with Component Data Sheets & Estimated Cost  
**Faculty / BOS Chairman:** Dr. Minakshi Pradeep Atre  
**Project Title:** FieldIQ — AI-Powered Cricket Tactical Intelligence & 3D Decision-Support Platform  

---

### Guidelines for Students for Deciding Software–Hardware Requirements
1. **Policy & Compliance:** Use institution-approved software and strictly comply with open-source licenses (e.g., MIT, CC BY-SA 4.0, Apache 2.0), user privacy standards, and college laboratory acceptable-use policies.
2. **Version Control & Backups:** Maintain Git repositories with documented dependencies via `requirements.txt` (exact pinned versions) and `package.json`, along with periodic offline and cloud backups.
3. **Data Integrity & Licensing:** Use only approved datasets (e.g., Cricsheet under CC BY-SA 4.0 license and ESPNcricinfo historical wagon-wheel sectors). Do not invent or synthetically populate missing fields; mark unavailable data explicitly (e.g., Zone 0).
4. **Electrical Safety & Lab Norms:** Ensure proper earthing, regulated low-voltage power supply, surge suppression, and adherence to lab safety regulations when operating high-performance computing workstations.
5. **No AI Lookups & Uncertainty Transparency:** The system is decision-support software. It must never present probabilistic forecasts as certainties or disguise static lookup tables as machine learning models.

---

## 1. Project Objective
To design, implement, and deploy **FieldIQ**, an AI-powered cricket tactical intelligence and decision-support platform that analyzes batter and bowler historical matchups, match state, ground geometry, and pitch kinematics to dynamically generate, optimize, and validate legal fielding configurations. The platform integrates a decomposed probabilistic machine-learning engine (predicting wicket, boundary, and run probabilities), a two-stage field optimization pipeline, an automated ICC/MCC fielding rules compliance engine, and an interactive 3D WebGL tactical stadium interface (Three.js/React Three Fiber) supporting human-in-the-loop "what-if" tactical evaluation and Bayesian live match updates.

---

## 2. Computer Laboratory Hardware Specifications

| Component | Minimum Specification | Recommended Specification (Lab Workstation) | Justification for FieldIQ Project |
| :--- | :--- | :--- | :--- |
| **CPU** | Intel Core i5 10th Gen / AMD Ryzen 5 3600 (6 Cores / 12 Threads) | Intel Core i5 12th Gen (i5-12400) / AMD Ryzen 5 5600X (6 Cores / 12 Threads, up to 4.4 GHz) | Required for rapid feature extraction, GameId-partitioned cross-validation, and parallel Monte Carlo delivery trajectory simulations (1,000+ stochastic iterations). |
| **RAM** | 8 GB DDR4 2666 MHz | 16 GB (2 × 8 GB Dual-Channel) DDR4 3200 MHz / DDR5 4800 MHz | Ingestion and memory-caching of 10,454 ball-by-ball delivery records, vectorized NumPy kinematics, and running FastAPI backend alongside Node.js Vite dev server concurrently. |
| **Storage** | 256 GB SATA SSD | 512 GB M.2 NVMe PCIe Gen 4.0 SSD (Read: up to 5000 MB/s, Write: up to 4200 MB/s) | Rapid loading of Cricsheet JSON archives (22.7 MB compressed, >150 MB uncompressed), pre-computed feature arrays, model binaries (`.joblib`), and 3D GLTF stadium assets. |
| **Graphics (GPU)** | Integrated Graphics (Intel UHD 630 / AMD Radeon Vega) | Dedicated NVIDIA GeForce GTX 1650 (4 GB GDDR6) or RTX 3050 (6 GB / 8 GB GDDR6) | Dedicated GPU rendering is essential for smooth 60 FPS Three.js/WebGL 3D stadium visualization, real-time lighting/shadows, interactive 11-player avatar drag-and-drop, and optional CUDA-accelerated XGBoost tree construction. |
| **Operating System** | Windows 10 64-bit / Ubuntu 22.04 LTS | Windows 11 64-bit / Ubuntu 24.04 LTS | Compatible with modern Python 3.13 runtimes, Node.js v24+, POSIX shell tooling, and WebGL 2.0 graphics pipeline. |
| **Display** | 19.5-inch LED (1600 × 900) | 23.8-inch Full HD (1920 × 1080) IPS Display, anti-glare, 75 Hz/100 Hz | High-resolution canvas required for rendering the 3D cricket oval, 34 spatial field positions, wagon-wheel radial sector overlays, and dual-pane tactical analytics. |
| **Network** | Fast Ethernet (100 Mbps) / Wi-Fi 4 | Gigabit Ethernet (1000 Mbps) & Dual-band Wi-Fi 5/6 (802.11ac/ax) | High-throughput connection for downloading official Cricsheet archives, installing pinned dependencies via `pip` and `npm`, and team Git collaboration. |
| **Peripherals** | Standard USB Keyboard and Optical Mouse | Ergonomic mechanical/membrane keyboard, high-precision optical mouse, surge-protected spike guard | Precision mouse input required for placing fielders on the 3D canvas and adjusting coordinates during what-if simulations. |

> **Procurement Note:** For general coursework, dedicated GPUs are not mandatory for introductory data analysis; however, for **FieldIQ**, the real-time 3D stadium rendering (WebGL/Three.js) and 1,000-iteration Monte Carlo kinematic trajectory calculations benefit substantially from a modern multi-core CPU and entry-level dedicated GPU (such as NVIDIA GTX 1650 / RTX 3050) available in institutional computing laboratories.

---

## 3. Project-Specific Hardware Needs & Infrastructure

| Item / Resource | Suggested Allocation | Application & Technical Rationale |
| :--- | :--- | :--- |
| **Primary Development Workstation** | 1 per student group (or shared departmental AI lab terminal) | Hosting backend microservices (Uvicorn/FastAPI), executing model training scripts, running 91+ automated test suites, and building client bundles. |
| **High-Speed Broadband Internet** | Shared Lab Gigabit LAN / Wi-Fi | Ingesting raw Cricsheet data bundles (`cricsheet_t20s.zip`), updating Python/Node package registries, and syncing GitHub commits. |
| **Local / External Storage Backup** | 1 × 64 GB USB 3.2 Flash Drive or Cloud Backup (Google Drive / GitHub) | Redundant backups of historical delivery datasets, trained model weights (`v3_decomposed`), test logs, and project documentation. |
| **Secondary Testing Screen / Device** | Optional (1 laptop or tablet per group) | Real-time cross-browser validation (Chrome, Firefox, Edge) to verify WebGL viewport responsiveness and touch/click fielder remapping. |

---

## 4. Hardware Cost Estimation & Bill of Materials (BOM)

The estimated hardware cost for setting up a dedicated AI & Data Science PBL workstation suitable for running FieldIQ is provided below (costs reflect current commercial pricing in Indian Rupees, AY 2026–27):

| Sr. No. | Component | Model / Technical Specification | Qty | Unit Price (INR ₹) | Total Cost (INR ₹) | Datasheet / Technical Source Link |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| 1 | **Processor (CPU)** | Intel Core i5-12400 (6 Cores, 12 Threads, 2.50 GHz to 4.40 GHz, 18MB Cache, LGA1700, 65W) | 1 | ₹12,499 | ₹12,499 | [Intel ARK i5-12400](https://www.intel.com/content/www/us/en/products/sku/134586/intel-core-i512400-processor-18m-cache-up-to-4-40-ghz/specifications.html) |
| 2 | **Motherboard** | ASUS Prime B660M-A WiFi D4 (Intel B660 Chipset, PCIe 4.0, Dual M.2, DDR4, Realtek 1Gb Ethernet) | 1 | ₹10,200 | ₹10,200 | [ASUS Prime B660M-A](https://www.asus.com/motherboards-components/motherboards/prime/prime-b660m-a-wifi-d4/techspec/) |
| 3 | **System Memory (RAM)** | Kingston FURY Beast 16 GB (2 × 8 GB Kit) DDR4 3200 MHz CL16 DIMM (KF432C16BBK2/16) | 1 | ₹3,600 | ₹3,600 | [Kingston FURY Beast Spec](https://www.kingston.com/datasheets/KF432C16BBK2_16.pdf) |
| 4 | **Solid-State Drive (SSD)** | Crucial P3 Plus 512 GB M.2 2280 PCIe Gen 4.0 ×4 NVMe SSD (Read 5000 MB/s, Write 4200 MB/s) | 1 | ₹3,400 | ₹3,400 | [Crucial P3 Plus Datasheet](https://content.crucial.com/content/dam/crucial/ssd-products/p3-plus/flyer/crucial-p3-plus-productflyer-en.pdf) |
| 5 | **Graphics Card (GPU)** | ZOTAC Gaming GeForce RTX 3050 6GB GDDR6 (2048 CUDA Cores, 96-bit, PCIe 4.0, Direct X 12, WebGL 2.0) | 1 | ₹15,800 | ₹15,800 | [NVIDIA RTX 3050 Specifications](https://www.nvidia.com/en-in/geforce/graphics-cards/30-series/rtx-3050/) |
| 6 | **Power Supply Unit (PSU)** | Cooler Master MWE 550 Bronze V2 (550W, 80 PLUS Bronze Certified, Non-Modular) | 1 | ₹3,750 | ₹3,750 | [Cooler Master MWE 550](https://www.coolermaster.com/en-global/products/mwe-550-bronze-v2/) |
| 7 | **Cabinet / Chassis** | Ant Esports ICE-100 Mid-Tower Cabinet (Tempered Glass, Mesh Front, 3 × 120mm Fans) | 1 | ₹2,650 | ₹2,650 | [Ant Esports ICE-100](https://antesports.com/) |
| 8 | **Display Monitor** | LG 24MP400-B 23.8" Full HD (1920 × 1080) IPS Panel, 75 Hz, AMD FreeSync, HDMI / VGA | 1 | ₹7,800 | ₹7,800 | [LG 24MP400-B Datasheet](https://www.lg.com/in/monitors/fhd-qhd/24mp400-b/) |
| 9 | **Input Peripherals** | Logitech MK215 Wireless Keyboard & Mouse Combo (2.4 GHz Nano USB Receiver) | 1 | ₹1,200 | ₹1,200 | [Logitech MK215 Specs](https://www.logitech.com/en-in/products/combos/mk215-wireless-keyboard-mouse.html) |
| 10 | **Networking & Safety** | Cat6 UTP RJ45 Ethernet Patch Cord (3m) + Goldmedal 4-Socket Surge Protector Spike Guard | 1 | ₹800 | ₹800 | [Cat6 & Power Protection Standards](https://www.goldmedalindia.com/) |
| **Total Estimated Hardware Cost** | | **Comprehensive AI Workstation Setup** | | | **₹61,749** | *(Approx. ₹15,437 per student for a 4-member group; ₹0 if leveraging college lab)* |

---

## 5. Component Technical Data Sheets & Engineering Specifications

To fulfill the rigorous technical submission requirements stipulated by the department, the critical hardware components utilized for FieldIQ's compute and rendering workloads are detailed below with their official engineering parameters:

### 5.1 Processor: Intel® Core™ i5-12400 Processor
* **Manufacturer:** Intel Corporation  
* **Official Technical Datasheet:** [https://www.intel.com/content/www/us/en/products/sku/134586/intel-core-i512400-processor-18m-cache-up-to-4-40-ghz/specifications.html](https://www.intel.com/content/www/us/en/products/sku/134586/intel-core-i512400-processor-18m-cache-up-to-4-40-ghz/specifications.html)
* **Architecture & Cores:** 6 Performance-cores (P-cores), 0 Efficient-cores, 12 Total Threads (Golden Cove architecture on Intel 7 process).
* **Clock Frequencies:** Base Frequency: 2.50 GHz; Intel Turbo Boost Max Frequency: 4.40 GHz.
* **Cache:** 18 MB Intel® Smart Cache (L3), 7.5 MB Total L2 Cache.
* **Power & Thermal:** Processor Base Power: 65 W; Maximum Turbo Power: 117 W; Maximum Operating Temperature ($T_{\text{junction}}$): 100 °C.
* **Instruction Sets & Vector Acceleration:** Intel® SSE4.1, SSE4.2, Intel® AVX2 (crucial for accelerated NumPy array math and vector calculations).
* **Memory Support:** Up to 128 GB DDR4-3200 MT/s or DDR5-4800 MT/s, 2 memory channels, Max Bandwidth 76.8 GB/s.
* **PCI Express Revisions:** PCIe 5.0 and 4.0 support (up to 20 lanes).

### 5.2 Motherboard: ASUS Prime B660M-A WiFi D4
* **Manufacturer:** ASUSTeK Computer Inc.  
* **Official Specification Sheet:** [https://www.asus.com/motherboards-components/motherboards/prime/prime-b660m-a-wifi-d4/techspec/](https://www.asus.com/motherboards-components/motherboards/prime/prime-b660m-a-wifi-d4/techspec/)
* **Chipset & Socket:** Intel® B660 Chipset; Socket LGA1700 supporting 12th/13th/14th Gen Intel processors.
* **Memory Expansion:** 4 × DIMM slots, max 128 GB DDR4 unbuffered memory up to 5333(OC) MHz, Dual Channel Architecture.
* **Storage Interfaces:** 2 × M.2 slots (M.2_1 PCIe 4.0 x4 mode, M.2_2 PCIe 4.0 x4 mode), 4 × SATA 6Gb/s ports.
* **Expansion Slots:** 1 × PCIe 4.0 x16 slot (supports x16 mode), 1 × PCIe 3.0 x16 slot (supports x4 mode), 1 × PCIe 3.0 x1 slot.
* **I/O & Connectivity:** Realtek 1Gb Ethernet, Wi-Fi 6 (802.11 a/b/g/n/ac/ax), Bluetooth v5.2, 2 × USB 3.2 Gen 2 ports, 4 × USB 2.0 ports, HDMI 2.1, DisplayPort 1.4.

### 5.3 System Memory: Kingston FURY™ Beast DDR4 16 GB (2 × 8 GB)
* **Manufacturer:** Kingston Technology Corporation  
* **Part Number:** `KF432C16BBK2/16`  
* **Datasheet Document:** [https://www.kingston.com/datasheets/KF432C16BBK2_16.pdf](https://www.kingston.com/datasheets/KF432C16BBK2_16.pdf)
* **Module Configuration:** 288-pin Unbuffered DIMM, 1G × 64-bit (8 GB) per module, 2Rx8 / 1Rx8 architecture.
* **Operating Profile (XMP Profile 1):** DDR4-3200 CL16-18-18 @ 1.35V.
* **Standard JEDEC Timing:** DDR4-2400 CL17-17-17 @ 1.2V.
* **Operating Temperature Range:** 0 °C to +85 °C; Storage Temperature: -55 °C to +100 °C.
* **Data Transfer Bandwidth:** Peak transfer rate of 25,600 MB/s (PC4-25600) per channel; 51.2 GB/s aggregate bandwidth in dual-channel mode.

### 5.4 Solid-State Storage: Crucial P3 Plus 512 GB PCIe 4.0 NVMe SSD
* **Manufacturer:** Micron Technology, Inc. / Crucial  
* **Part Number:** `CT500P3PSSD8`  
* **Datasheet Document:** [https://content.crucial.com/content/dam/crucial/ssd-products/p3-plus/flyer/crucial-p3-plus-productflyer-en.pdf](https://content.crucial.com/content/dam/crucial/ssd-products/p3-plus/flyer/crucial-p3-plus-productflyer-en.pdf)
* **Form Factor & Interface:** M.2 Type 2280; PCIe Gen 4.0 ×4, NVMe 1.4 protocol.
* **NAND Technology:** Micron® Advanced 176-layer 3D QLC NAND Flash.
* **Sequential Performance:** Sequential Read: up to 5,000 MB/s; Sequential Write: up to 3,600 MB/s.
* **Random 4K I/O Performance:** Random Read: up to 650,000 IOPS; Random Write: up to 800,000 IOPS.
* **Reliability & Endurance:** Mean Time Between Failures (MTTF): 1.5 million hours; Total Bytes Written (TBW): 150 TBW.
* **Operational Limits:** Voltage: $3.3\text{V} \pm 5\%$; Operating Temperature: 0 °C to 70 °C.

### 5.5 Graphics Card: NVIDIA GeForce RTX 3050 (6 GB GDDR6)
* **Manufacturer:** NVIDIA Corporation  
* **Product Architecture:** NVIDIA Ampere Architecture (GA107 Die, 8nm Samsung process).  
* **Official Technical Reference:** [https://www.nvidia.com/en-in/geforce/graphics-cards/30-series/rtx-3050/](https://www.nvidia.com/en-in/geforce/graphics-cards/30-series/rtx-3050/)
* **Compute Capabilities:** 2,048 CUDA Cores, 64 Tensor Cores (3rd Gen), 16 RT Cores (2nd Gen).
* **Clock Frequencies:** Base Clock: 1042 MHz; Boost Clock: 1470 MHz.
* **Memory Subsystem:** 6 GB GDDR6, 96-bit Memory Interface Width, Memory Clock: 14 Gbps, Memory Bandwidth: 168.0 GB/s.
* **API & Graphics Standards:** Microsoft DirectX® 12 Ultimate, Vulkan 1.3, OpenGL 4.6, OpenCL 3.0, **WebGL 2.0 (Three.js hardware accelerated)**.
* **Thermal & Power:** Graphics Card Power (TGP): 70 W; Recommended System Power: 300 W – 450 W; Max GPU Temperature: 90 °C.

---

## 6. Software Requirements Specifications

All software platforms, runtime libraries, and frameworks utilized in the development, testing, and deployment of FieldIQ are pinned to strict, production-verified versions:

| Software Category | Platform / Tool | Pinned Version | License Type | Specific Purpose in FieldIQ |
| :--- | :--- | :---: | :---: | :--- |
| **Operating System** | Windows 11 64-bit / Ubuntu Linux | 24.04 LTS / Win 11 | Proprietary / Open Source | Host environment for Python backend and Node.js frontend tooling. |
| **Backend Runtime** | Python | 3.13.15 | PSF License | Core backend execution runtime, data manipulation, and mathematical modeling. |
| **Web API Framework** | FastAPI | 0.141.1 | MIT License | High-performance asynchronous REST API framework serving field recommendations. |
| **ASGI Web Server** | Uvicorn (standard) | 0.52.4 | BSD-3-Clause | Production-grade lightning-fast ASGI server for handling asynchronous API requests. |
| **Data Schema Validation** | Pydantic | 2.13.4 | MIT License | Strict type enforcement for `AnalysisRequest`, `FieldPlacementSchema`, and player schemas. |
| **Web Middleware** | Starlette | 1.6.0 | BSD-3-Clause | Foundational HTTP toolkit and routing layer underpinning FastAPI. |
| **Numerical Computation** | NumPy | 2.5.2 | BSD-3-Clause | Vectorized kinematics calculations, distance matrices, and Monte Carlo probability generation. |
| **Data Analysis & ETL** | pandas | 3.0.5 | BSD-3-Clause | Loading, cleaning, and partitioning 10,454 Cricsheet ball-by-ball delivery records. |
| **Machine Learning Core** | scikit-learn | 1.9.0 | BSD-3-Clause | Preprocessing pipelines, One-Hot Encoding, Stratified K-Fold validation, and evaluation metrics. |
| **Gradient Boosting ML** | XGBoost | 3.4.1 | Apache-2.0 | Decomposed multi-model predictor ($P(\text{wicket})$, $P(\text{boundary})$, and remainder runs). |
| **Model Persistence** | joblib | 1.6.0 | BSD-3-Clause | Serialization and low-latency deserialization of trained model pipelines (`.joblib`). |
| **Backend Test Suite** | pytest | 9.1.1 | MIT License | Automated regression suite verifying 91 tests across contracts, optimization, and security. |
| **Asynchronous HTTP Client**| httpx | 0.28.1 | BSD-3-Clause | End-to-end integration testing of REST endpoints and synchronous API contracts. |
| **Async Concurrency** | anyio | 4.14.2 | MIT License | Structured concurrency library powering asynchronous test loops. |
| **Frontend Runtime** | Node.js / npm | v24.21.0 / v11.x | MIT License | JavaScript/TypeScript execution runtime for building and bundling the client application. |
| **Frontend Framework** | React | 19.2.8 | MIT License | Declarative component UI library for tactical panels, controls, and what-if editors. |
| **Virtual DOM Renderer** | React DOM | 19.2.8 | MIT License | DOM rendering package for React web interface. |
| **Language** | TypeScript | 6.0.2 | Apache-2.0 | Type-safe front-end programming enforcing API contracts and geometry interfaces. |
| **3D Graphics Engine** | Three.js | 0.185.1 | MIT License | WebGL 3D rendering engine rendering the stadium, pitch, boundary ropes, and players. |
| **React 3D Bridge** | @react-three/fiber | 9.7.0 | MIT License | Declarative React wrapper for Three.js managing canvas state and render loops. |
| **3D UI Helpers** | @react-three/drei | 10.7.8 | MIT License | Three.js camera controls (OrbitControls), lighting helpers, and spatial HTML annotations. |
| **Frontend Bundler** | Vite | 8.2.2 | MIT License | Next-generation ultra-fast frontend build tool and Hot Module Replacement (HMR) server. |
| **Frontend Test Runner** | Vitest | 4.1.11 | MIT License | Unit test runner verifying UI components (`MinimalFormView.test.tsx`) in 315 ms. |
| **Frontend Linter** | Oxlint | 1.79.0 | MIT License | High-performance Rust-based linter ensuring clean frontend codebase standards. |
| **Version Control** | Git / GitHub | 2.45+ | GPL v2 / Cloud | Distributed source control, branch management, issue tracking, and code reviews. |
| **Architecture & Diagrams** | diagrams.net (draw.io) | Latest Web | Open Source | Architectural diagrams, data flow representations, and UML class diagrams. |

---

## 7. Project-Type Mapping

The table below correlates each major development activity of FieldIQ with its corresponding hardware resource demands and core toolchain:

| Project Activity / Stage | Primary Hardware Resource | Core Tools & Frameworks | Description of Engineering Execution |
| :--- | :--- | :--- | :--- |
| **1. Historical Data Ingestion & Cleaning** | Multi-Core CPU, High-Speed NVMe SSD, Gigabit Internet | Python 3.13, pandas 3.0.5, Cricsheet CC BY-SA 4.0 data archive | Downloading 22.7 MB Cricsheet T20 JSON archive, parsing 10,454 deliveries across 267 matches, resolving 330 bowlers and 9 batters, strictly isolating unrecorded spatial rows (`Zone == 0`). |
| **2. Feature Engineering & Dataset Splitting** | Multi-Core CPU (AVX2), 16 GB RAM | pandas, NumPy 2.5.2, scikit-learn 1.9.0 | Generating rolling batter strike rates, phase identifiers, and leak-free `GameId` match-level partitions (Seed 42: 7,403 train, 1,573 val, 1,478 test deliveries). |
| **3. Decomposed ML Model Training & Gating** | Multi-Core CPU / Dedicated GPU (NVIDIA RTX 3050) | XGBoost 3.4.1, joblib 1.6.0, scikit-learn | Training Model 1 ($P(\text{wicket})$), Model 2 ($P(\text{boundary})$), and Model 3 ($P(\text{remainder})$). Applying 5-stage deployment gates (PR-AUC, F1, 3-split stability spread, calibration). |
| **4. Matchup Intelligence & Bayesian Updating** | Multi-Core CPU, 16 GB RAM | Python dataclasses, `H2HStatsEngine`, `LiveMatchSession` | Evaluating 4-tier fallback hierarchy (`direct_h2h` $\rightarrow$ `vs_bowler_type_phase` $\rightarrow$ `vs_bowler_type` $\rightarrow$ `insufficient_data`). Executing live Bayesian zone danger updates ball-by-ball. |
| **5. Trajectory Kinematics & Monte Carlo Simulation** | Multi-Core CPU (Parallel execution across 12 threads) | NumPy vectorization, `PitchPhysicsEngine`, `GroundGeometryEngine` | Simulating 1,000 stochastic delivery outcomes per tactical recommendation, factoring in wind velocity, pitch restitution/seam, and asymmetric boundary curves. |
| **6. ICC Rules Validation & Field Optimization** | Standard CPU, 8–16 GB RAM | Python, `rules_engine.py`, `optimizer.py` | Validating 11 field positions against ICC restrictions (max 2 fielders outside 30-yard circle during Powerplay). Auto-fixing violations via ring-boundary positional swaps. |
| **7. 3D WebGL Ground Visualization & What-If UI** | Dedicated GPU (NVIDIA RTX 3050), FHD 24" Monitor | React 19, TypeScript, Three.js 0.185, @react-three/fiber, Vite | Rendering dynamic 3D stadium, 34 field positions, interactive fielder drag-and-drop, real-time coordinate editing, and triggering `/api/v1/analysis/evaluate` for what-if recalculation. |
| **8. Automated Quality Assurance & Testing** | Multi-Core CPU, 16 GB RAM | pytest 9.1.1, Vitest 4.1.11, httpx, oxlint | Executing 91 backend automated regression tests in 52.9s and frontend Vitest component tests in 315ms to guarantee zero regressions. |

---

## 8. Tangible Project Deliverables

1. **Production-Ready Backend Service:**
   * Fully asynchronous FastAPI application (`backend/app/main.py`) exposing verified REST endpoints (`/api/v1/analysis`, `/api/v1/analysis/evaluate`, `/api/v1/players`, `/api/v1/match/delivery`).
   * Two-stage field optimizer combining heuristic tactical placement (Stage A) with greedy zone threat coverage (Stage B).
   * Verified ICC/MCC rule compliance engine enforcing legal field constraints across T20 and ODI match phases.
2. **Decomposed Probabilistic Machine Learning Models:**
   * Trained and gated XGBoost model binaries (`models/v3_decomposed/`) strictly preserving probability sum unity ($\sum P_i = 1.0 \pm 10^{-5}$).
   * Full model governance metadata (`model_metadata.json`) recording dataset split seeds, precision, recall, PR-AUC, and temperature-calibrated log-loss.
3. **Interactive 3D WebGL Tactical Visualizer:**
   * Modular React 19 + TypeScript frontend application built on Vite.
   * Full 3D cricket stadium rendered in Three.js and `@react-three/fiber`, featuring 34 real ground positions, wagon-wheel threat overlays, and 11 interactive fielder avatars.
   * Real-time "What-If" tactical simulator allowing users to drag/edit fielder coordinates and immediately inspect recalculated Expected Runs Saved (ERS) and Expected Wicket Opportunity (EWO).
4. **Curated & Audited Cricket Dataset:**
   * Cleaned delivery dataset (`data/real_batters_deliveries.csv`, 10,454 rows across 9 international batters and 330 bowlers).
   * Provenance audit logs (`data/README.md`) attributing Cricsheet ball-by-ball records (CC BY-SA 4.0) and ESPNcricinfo wagon-wheel angles.
5. **Comprehensive Verification & Test Suite:**
   * 91 automated backend unit and contract tests (`pytest`) with 100% pass rate.
   * Frontend Vitest unit test suite covering client form behaviors and API payload bindings.
6. **Academic Documentation & Technical Reports:**
   * Complete Software & Hardware Requirements Specification (this document).
   * System Architecture Diagrams, UML Class Diagrams, and API Data Contracts.
   * Project Progress Logbook and Final PBL Project Report.

---

## 9. Domain Constraints, Ethical Principles & Important Limitations

In strict adherence to the project's engineering constitution and academic integrity guidelines:
* **Decision Support vs. Prediction Certainty:** FieldIQ is a **tactical decision-support system**, not a deterministic crystal ball. Cricket is inherently stochastic; hence, model predictions are expressed strictly as calibrated conditional probabilities ($P(\text{wicket})$, $P(\text{boundary})$) accompanied by confidence metrics (e.g., test recall 13.0%, precision 16.4%). Predictions are never presented to human decision-makers as guaranteed outcomes.
* **No Synthetic Lookups Disguised as AI:** The platform relies strictly on empirical data-driven probabilities, physics-based kinematic trajectories, and mathematical optimization. Hard-coded rules exist solely as ICC legality boundary constraints and baseline safety fallbacks.
* **Spatial Coordinate Limitations & Handling of Missing Data (Zone 0):** The dataset inherits 8 radial direction sectors ($z \in [1..8]$) from source wagon-wheel records, while distance bands (`Inner`, `Mid`, `Deep`) serve as categorical proxies. Deliveries with unrecorded spatial coordinates (`Zone == 0`, 2,119 deliveries / 20.3%) are **strictly excluded** from spatial threat calculations and are never synthetically fabricated or silently imputed.
* **Data Licensing & Attribution:** Historical match logs are licensed under the Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0) via Cricsheet.
* **Human-in-the-Loop Supremacy:** The AI platform provides optimal recommendations; the human captain or analyst retains full authority to accept, modify, or reject placements through the interactive 3D interface.

---

**Prepared by:**  
Second Year B. Tech. Student Project Group (AI & DS)  
PVG’s College of Engineering, Technology & Management, Pune  

**Submitted to:**  
**Dr. Minakshi Pradeep Atre**  
Chairman, Board of Studies (BOS) — Artificial Intelligence & Data Science  
PVG’s COETM, Pune – 411009

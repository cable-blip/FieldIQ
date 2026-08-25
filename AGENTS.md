# CRICKET TACTICAL INTELLIGENCE
## Engineering & AI Development Rules

## 1. PROJECT PURPOSE

This project is a professional-grade cricket tactical intelligence
and decision-support platform.

The system analyzes:

- Batter
- Bowler
- Fielder
- Batter × Bowler matchup
- Match state
- Delivery characteristics
- Recent delivery sequence
- Historical data
- Fielder × position capability
- Tactical objective
- Cricket rules

The system generates and evaluates legal field configurations and
provides explainable tactical recommendations through an interactive
3D interface.

The system is decision-support software.

It must NOT claim to predict cricket outcomes with certainty.

---

## 2. CORE PRINCIPLE

DO NOT BUILD A LOOKUP TABLE DISGUISED AS AI.

The system must eventually use data-driven conditional probabilities,
optimization and simulation.

Hard-coded cricket rules may exist as:

- baseline logic
- fallback logic
- validation
- domain constraints

They must NOT become the primary intelligence layer.

---

## 3. ARCHITECTURE PRINCIPLE

Keep these layers separate:

DATA
→ FEATURE ENGINEERING
→ PLAYER INTELLIGENCE
→ MATCHUP INTELLIGENCE
→ MATCH STATE
→ SEQUENCE INTELLIGENCE
→ OUTCOME PREDICTION
→ FIELD GENERATION
→ OPTIMIZATION
→ SIMULATION
→ RULE VALIDATION
→ EXPLANATION
→ HUMAN DECISION
→ 3D VISUALIZATION

Do not bypass architectural layers without documenting why.

---

## 4. REAL DATA PRINCIPLE

The system must support real-world cricket datasets.

Never invent unavailable data.

If a dataset does not contain a field:

- do not fabricate it
- do not infer it silently
- mark it unavailable
- expose the limitation where appropriate

Every dataset must have:

- schema
- version
- source
- validation status
- quality information

---

## 5. UNCERTAINTY

Never present uncertain predictions as facts.

Recommendations must support:

- probability
- confidence
- data coverage
- uncertainty
- alternative strategies

---

## 6. SECURITY

NEVER commit:

- passwords
- API keys
- JWT secrets
- database credentials
- private keys
- confidential datasets
- production secrets

Use environment variables.

`.env` must remain local.

`.env.example` may be committed.

---

## 7. GITHUB

GitHub is the source of truth for source code and project history.

Every meaningful architectural change must be committed.

Use clear commit messages.

Do not commit generated secrets or confidential real-world datasets.

---

## 8. OBSIDIAN

Obsidian is the project knowledge base.

Architecture decisions, specifications, research,
data definitions and major decisions should be documented there.

Do not allow implementation decisions to exist only inside chat.

---

## 9. CURSOR

Cursor is primarily responsible for:

- Backend
- Python
- FastAPI
- ML
- Data pipelines
- Database
- Optimization
- Simulation
- Testing
- Security implementation

Cursor must follow the documented architecture.

---

## 10. ANTIGRAVITY

Antigravity is primarily responsible for:

- Frontend
- 3D cricket field
- React
- Three.js
- React Three Fiber
- UI/UX
- Animation
- Visualization
- Browser testing

Antigravity must visualize intelligence produced by the backend.

It must NOT independently invent cricket tactical logic.

---

## 11. 3D IS FUNCTIONAL

The 3D interface is not decoration.

It must eventually represent:

- field positions
- player movement
- tactical zones
- heatmaps
- ball trajectories
- field changes
- simulations
- explanations

---

## 12. TESTING

Every important engine must eventually have:

- unit tests
- integration tests
- validation tests
- edge-case tests

Critical tactical scenarios should become
golden test scenarios.

---

## 13. RULES

Cricket legality must be implemented separately from tactical intelligence.

Rules must be versioned and configurable.

The model must never silently encode changing cricket regulations.

---

## 14. HUMAN CONTROL

The AI recommends.

The human decision-maker decides.

The interface must eventually support:

- Accept
- Modify
- Reject
- What-if simulation

Manual changes must trigger recalculation where appropriate.

---

## 15. MODEL GOVERNANCE

Models must be versioned.

Track:

- model version
- dataset version
- feature version
- training period
- evaluation metrics
- calibration
- deployment status

Never silently replace a production model.

---

## 16. DEVELOPMENT RULE

Build incrementally.

Do NOT attempt to build the entire platform in one step.

Every module must have:

1. Specification
2. Interface
3. Implementation
4. Tests
5. Documentation
6. Git commit

---

## 17. NO FAKE COMPLETION

Never claim a feature is complete when it is only:

- mocked
- hard-coded
- visually simulated
- partially implemented

Clearly distinguish:

- Mock
- Prototype
- Functional
- Data-driven
- Production-ready

---

## 18. CODE QUALITY

Prefer:

- small modules
- clear interfaces
- typed models
- validation
- explicit errors
- testable functions
- documented assumptions

Avoid:

- giant files
- duplicated logic
- hidden global state
- magic numbers
- unexplained hard-coded cricket decisions

---

## 19. WHEN UNCERTAIN

Before changing architecture:

1. Check the project documentation.
2. Check existing implementation.
3. Preserve existing contracts.
4. Prefer the smallest change.
5. Document significant architectural decisions.

---

## 20. FINAL PRINCIPLE

Build a serious cricket tactical intelligence platform.

Do not optimize for:

"looks impressive."

Optimize for:

- correctness
- explainability
- data integrity
- security
- reproducibility
- maintainability
- tactical usefulness
- realistic simulation
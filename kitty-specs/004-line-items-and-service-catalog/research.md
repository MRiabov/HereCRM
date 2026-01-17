# Research Findings: Line Items & Service Catalog

## Decisions

### 1. Catalog Management via State Machine

**Decision**: Use a dedicated `SETTINGS` conversation state.
**Rationale**: Prevents command ambiguity. "Add service X" in the main flow could be confused with "Add Job X". A modal state ensures intent is clear.
**Alternatives**:

- **Hash commands** (e.g. `/add-service`): Harder for non-tech users to remember.
- **Natural Language Router**: Too risky for config changes.

### 2. Line Item Inference Logic

**Decision**: Hybrid LLM + Deterministic Logic.

- LLM extracts: `description`, `total_amount`, `quantity` (if explicit).
- Code Logic matches `description` -> `Service` (fuzzy match).
- Code Logic calculates:
  - If `Total` & `Service.Default` & `!Qty` -> `Qty = Total / Default`
  - If `Total` & `Qty` -> `UnitPrice = Total / Qty` (Override Default)
**Rationale**: LLM is bad at math. Code is good at math. LLM is good at extraction.

## Questions Resolved

- **Service Entity**: Confirmed as necessary for standardizing price/desc defaults.
- **Inference Location**: Logic will reside in specific domain service/repo method, triggered before DB insert.

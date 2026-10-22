# Prompt Log

## Purpose
This log records how I used AI assistance to understand the loan-calc codebase, generate and refine pytest coverage, debug failing tests, and validate fixes. I also note where AI-generated advice was reviewed against the repository source and corrected/rejected based on project constraints (especially around financial contract rules: annual interest rate as a percentage, tenure in months, monthly-rate conversion, amortisation schedule behavior, and prepayment timing).

## 1. Codebase understanding and architecture review
- I used prompts requesting a function-by-function explanation of the project’s core calculation flow (EMI computation, amortisation schedule, totals, outstanding balance, prepayment savings, and helpers).
- I provided the AI with code/file context by referencing the repository’s `loan_calc/calculator.py` implementation.
- I reviewed AI explanations against the source before writing/aligning the project documentation in `ARCHITECTURE.md`.
- Assumptions checked during the audit:
  - Annual interest rate input is a **percentage** (e.g., `10.0` means 10% p.a.).
  - Monthly decimal interest rate must be derived consistently via `annual_rate / 1200`.
  - Tenure is measured strictly in **months**.
  - Amortisation schedule behavior must include a row for each contractual month and settle the final balance appropriately.
  - Prepayment timing is 1-based by `prepay_month`, and the contract policy is **keep EMI constant and shorten tenure**.

## 2. Documentation review
- I reviewed AI suggestions for docstrings and type hints before acceptance, ensuring they did not change behavior unintentionally.
- I clarified public API units in documentation review:
  - annual interest rate is a percentage
  - tenure is in months
- I kept documentation edits conceptually separate from behavioral bug fixes where possible, so that test failures could be traced to calculation logic rather than description drift.

## 3. Test-generation review
- I asked the AI to propose pytest tests covering:
  - normal cases
  - boundary cases
  - arithmetic invariants
  - amortisation schedule behavior
  - prepayment scenarios
- The key scenarios adopted for regression:
  - **0% interest**
  - **one-month tenure**
  - a **very large principal**
  - amortisation invariants (e.g., decomposition relationships and outstanding balance consistency)
  - **zero prepayment**
  - **partial prepayment**
  - **prepayment exceeding the remaining balance**
- I reviewed proposed tests against standard loan-contract rules rather than blindly matching current implementation behavior, so the tests would expose genuine financial-contract bugs (off-by-one scheduling, inconsistent rate conversions, and prepayment settlement logic issues).

## 4. Incorrect AI suggestion or explanation corrected
### Example: schedule-length test initially encoded a bug
- **AI suggestion or explanation:** An early generated test plan encoded assertions that mirrored implementation quirks (including schedule length behavior that omitted the final payment month).
- **Why it was wrong:** A standard amortising loan schedule should contain one row for every contractual payment month, including the final month. A one-month loan must have one row and end with a zero balance.
- **Decision:** I rejected the suggestion and changed the tests to require exactly `tenure_months` rows, a final row for the final payment month, full principal repayment reconciliation, and a final balance approximately equal to zero.
- **Outcome:** This regression test exposed and supported the fix for the off-by-one amortisation-schedule bug.

### Example: summary EMI assertion was too strict
- **Issue:** A test initially expected the formatted EMI for ₹10,00,000 at 9% over 240 months to match an exact constant value.
- **Why it was wrong:** EMI formatting/rounding semantics apply, and the project’s acceptance criterion is within a small tolerance; strict equality was not appropriate for formatted currency output.
- **Decision:** I corrected the test to assert equality to the formatted output of `emi(...)` (or within a documented tolerance), rather than hard-coding a brittle constant.
- **Outcome:** Preserved correct calculation and ensured `summary()` formatting was tested appropriately.

## 5. Bugs found and fixed
| Bug | Evidence from test failure | Production-code fix | Regression test | Commit |
|---|---|---|---|---|
| Off-by-one amortisation schedule | Tests expecting schedule rows per month and final-zero balance failed; one-month tenure schedule length and end settlement were incorrect | Updated `amortisation_schedule()` to generate rows for months `1..tenure_months` and force final-month settlement so remaining balance amortises to ~0 | Regression tests verifying schedule length, one-month loan row presence, principal reconciliation, and final balance ~0 | TODO: add commit hash |
| Monthly interest-rate precision | Monthly-rate conversion tests failed for inputs like 7.5% and 0.01% because `_monthly_rate()` rounded intermediate values | Changed `_monthly_rate()` to return `annual_rate / 1200` without intermediate rounding | Regression tests verifying `_monthly_rate(7.5)` equals `7.5/1200` and `_monthly_rate(0.01)` equals `0.01/1200` | TODO: add commit hash |
| Remaining-tenure rate basis mismatch for prepayment | Prepayment tests (including `prepay_amount=0`) failed with `ValueError("instalment too small...")` | Updated `remaining_tenure()` to use the same monthly interest basis as EMI/schedule by using `_monthly_rate(annual_rate)` instead of `annual_rate / 100` | Regression tests covering zero prepayment and partial prepayment behavior | TODO: add commit hash |

## 6. Coverage work
- Initial coverage was approximately 60%.
- Missing coverage came from untested validation and branches, including:
  - remaining-tenure feasibility checks
  - schedule branches
  - offer comparison
  - eligibility calculation
  - INR formatting
  - CSV export
  - summary generation
- I added meaningful tests that exercised these behaviors, especially around edge cases and prepayment settlement.
- Final result: all tests passed and coverage reached 100%, exceeding the required 85%.

## 7. Final validation
- [x] Three seeded bugs identified and fixed in separate production-code changes.
- [x] Regression tests were added for each bug.
- [x] EMI acceptance example was kept within the required tolerance semantics (no brittle strict-equality assumptions for formatted currency).
- [x] `ARCHITECTURE.md` was written and reviewed.
- [x] At least one AI-generated suggestion/test was corrected rather than accepted blindly.
- [x] Full pytest suite passes.
- [x] Coverage is at least 85%.

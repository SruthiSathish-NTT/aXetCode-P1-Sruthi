# ASSIGNMENT P1

## Understand, Test and Fix Legacy Code

| Tool | Level | Effort |
|---|---|---|
| aXet Plugin | Foundation | 3–4 hours |

Use aXet Plugin chat to understand an unfamiliar codebase, write unit tests for it, and fix the bugs those tests expose.

## Scenario

You inherit `loan-calc`, a small Python module (about 250 lines, with no tests or documentation) that computes EMI, amortisation schedules, and prepayment savings. Users report incorrect numbers for some loans.

The starter repository contains three seeded bugs.

## What to Do

1. Use chat with file and workspace context to explain each function.
   - Write the result into `ARCHITECTURE.md`.
   - Correct anything the AI got wrong.

2. Generate docstrings and type hints for every public function.
   - Review each suggestion before accepting it.

3. Ask the plugin to propose test cases, including these edge cases:
   - 0% interest
   - 1-month tenure
   - Very large principal
   - Prepayment larger than the balance

   Write the tests using `pytest`.

4. Run the tests.
   - For each failure, use chat to diagnose it.
   - Fix the code, not the test, unless the test itself is wrong.

5. Reach at least **85% line coverage** using:

   ```bash
   pytest --cov
   ```

## Acceptance Criteria

- [ ] All three seeded bugs are found and fixed, each in its own commit.
- [ ] The test suite passes with coverage ≥ 85%.
- [ ] EMI for ₹10,00,000 at 9% p.a. over 240 months matches ₹8,997 (± 1).
- [ ] `ARCHITECTURE.md` is accurate and written in your own words.
- [ ] The prompt log records at least one case where the AI explanation or test was wrong.

## Stretch Goal

Ask the plugin to add input validation and a custom exception hierarchy, then add tests for them.

## Skills Covered

- Context-aware chat
- Code explanation
- Test generation
- AI-assisted debugging
- Judging suggestions instead of accepting them

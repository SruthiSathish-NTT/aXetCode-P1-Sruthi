import math

import pytest

from datetime import date

from loan_calc.calculator import (
    _monthly_rate,
    amortisation_schedule,
    compare_offers,
    eligible_amount,
    emi,
    format_inr,
    outstanding_after,
    prepayment_savings,
    remaining_tenure,
    schedule_to_csv,
    summary,
    total_interest,
    total_payment,
)


def approx0(x, tol=1e-9):
    return abs(x) <= tol


# -----------------------
# A) Interest-rate + EMI
# -----------------------

@pytest.mark.parametrize(
    "annual_rate, expected_monthly",
    [
        (0, 0.0),
        (12, 12 / 1200),
        (7.5, 7.5 / 1200),
        (9.0, 9.0 / 1200),
        (0.01, 0.01 / 1200),
    ],
)
def test_monthly_rate_contract_conversion(annual_rate, expected_monthly):
    """
    Verifies: (1) contract rule for converting annual percent rate to monthly decimal.
    Fails if: precision/rounding/denominator is wrong.
    """
    got = _monthly_rate(annual_rate)
    assert got == pytest.approx(expected_monthly, rel=1e-12, abs=1e-12)


def test_emi_zero_interest_exact_expected_values():
    """
    Verifies: (1) contract rule for 0% interest special-case.
    Also validates mathematical invariant totals.
    """
    principal = 120_000
    annual_rate = 0
    tenure_months = 12

    m = emi(principal, annual_rate, tenure_months)
    assert m == 10_000.00

    tp = total_payment(principal, annual_rate, tenure_months)
    assert tp == 120_000.00

    ti = total_interest(principal, annual_rate, tenure_months)
    assert ti == 0.00

def test_zero_interest_schedule_has_equal_principal_payments():
    principal = 120_000.00
    annual_rate = 0.0
    tenure_months = 12

    sched = amortisation_schedule(principal, annual_rate, tenure_months)

    assert len(sched) == tenure_months

    for row in sched:
        assert row["interest"] == pytest.approx(0.0, abs=1e-6)
        assert row["principal"] == pytest.approx(10_000.0, abs=1e-6)

    assert sched[-1]["balance"] == pytest.approx(0.0, abs=1e-6)


def test_emi_matches_required_known_example():
    """
    Acceptance criterion:
    ₹10,00,000 at 9% p.a. for 240 months should have an EMI of ₹8,997 ± ₹1.
    """
    result = emi(
        principal=1_000_000,
        annual_rate=9.0,
        tenure_months=240,
    )

    assert result == pytest.approx(8_997, abs=1)


def test_one_month_tenure_amortises_contract():
    """
    Verifies: (1) contract rule that a 1-month loan has exactly 1 amortisation month
             and reaches zero remaining balance after month 1.
    """
    principal = 50_000.00
    annual_rate = 9.0
    tenure_months = 1

    r = _monthly_rate(annual_rate)

    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    assert len(sched) == 1, "Expected one amortisation row for month 1"

    row = sched[0]
    # Interest for the single month should be principal * monthly_rate.
    expected_interest = round(principal * r, 2)
    assert row["month"] == 1
    assert row["interest"] == pytest.approx(expected_interest, rel=0, abs=1e-8)

    # Remaining balance must be 0 after the only payment.
    assert row["balance"] == pytest.approx(0.0, abs=1e-6)

    # Principal portion must equal principal at 0-length after first (because tenure=1).
    assert row["principal"] == pytest.approx(round(principal, 2), rel=0, abs=1e-6)


# ---------------------------------------
# B) Amortisation schedule (core behavior)
# ---------------------------------------

def test_schedule_length_one_row_per_month():
    """
    Verifies: (1) contract rule: schedule contains one row per month in tenure.
    Fails if: off-by-one schedule error.
    """
    principal = 100_000.00
    annual_rate = 10.0
    tenure_months = 24

    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    assert len(sched) == tenure_months


def test_schedule_end_balance_zero():
    """
    Verifies: (1) contract rule: final month fully amortises the loan.
    """
    principal = 123_456.78
    annual_rate = 6.5
    tenure_months = 18

    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    final = sched[-1]["balance"]
    assert final == pytest.approx(0.0, abs=1e-4)


def test_schedule_decomposition_invariant_payment_equals_principal_plus_interest():
    """
    Verifies: (2) mathematical invariant per row:
      emi == principal + interest (with the same rounding used by the calculator).
    """
    principal = 200_000.00
    annual_rate = 8.0
    tenure_months = 12

    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    for row in sched:
        assert row["emi"] == pytest.approx(row["principal"] + row["interest"], rel=0, abs=1e-6)


def test_outstanding_after_matches_schedule_state():
    """
    Verifies: (1) business rule + (2) invariant consistency:
      outstanding_after(..., m) equals schedule month m-1 row balance.
    """
    principal = 90_000.00
    annual_rate = 10.0
    tenure_months = 20

    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    for months_paid in [1, 6, 12, tenure_months]:
        got = outstanding_after(principal, annual_rate, tenure_months, months_paid)
        expected = sched[months_paid - 1]["balance"]
        assert got == pytest.approx(expected, rel=0, abs=1e-6)

def test_outstanding_after_zero_months_equals_original_principal():
    principal = 90_000.00

    result = outstanding_after(
        principal=principal,
        annual_rate=10.0,
        tenure_months=20,
        months_paid=0,
    )

    assert result == pytest.approx(principal, abs=1e-6)


def test_schedule_principal_repayments_equal_original_principal():
    principal = 123_456.78
    annual_rate = 6.5
    tenure_months = 18

    sched = amortisation_schedule(principal, annual_rate, tenure_months)

    total_principal_paid = sum(row["principal"] for row in sched)

    assert total_principal_paid == pytest.approx(principal, abs=0.05)
    assert sched[-1]["month"] == tenure_months
    assert sched[-1]["balance"] == pytest.approx(0.0, abs=0.05)

def test_large_principal_produces_finite_results():
    principal = 1_000_000_000_000.00
    annual_rate = 7.5
    tenure_months = 360

    monthly_emi = emi(principal, annual_rate, tenure_months)
    total = total_payment(principal, annual_rate, tenure_months)
    interest = total_interest(principal, annual_rate, tenure_months)
    sched = amortisation_schedule(principal, annual_rate, tenure_months)

    assert math.isfinite(monthly_emi)
    assert math.isfinite(total)
    assert math.isfinite(interest)
    assert monthly_emi > 0
    assert len(sched) == tenure_months
    assert sched[-1]["balance"] == pytest.approx(0.0, abs=0.05)


# -------------------------
# C) Totals (invariants)
# -------------------------

def test_total_payment_interest_identities():
    """
    Verifies: (2) mathematical invariant:
      total_interest == total_payment - principal
    and total_payment is EMI * tenure (consistent with implementation rounding).
    """
    principal = 80_000.00
    annual_rate = 11.0
    tenure_months = 36

    m = emi(principal, annual_rate, tenure_months)
    tp = total_payment(principal, annual_rate, tenure_months)
    ti = total_interest(principal, annual_rate, tenure_months)

    assert tp == pytest.approx(m * tenure_months, rel=0, abs=1e-6)
    assert ti == pytest.approx(tp - principal, rel=0, abs=1e-6)


# -------------------------
# D) Prepayment settlement
# -------------------------

def test_prepayment_zero_noop_contract():
    """
    Verifies: (1) contract rule:
      prepay_amount=0 should not change tenure and should save 0 interest.
    """
    principal = 200_000.00
    annual_rate = 10.0
    tenure_months = 24

    prepay_month = 6
    prepay_amount = 0.0

    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    assert 1 <= prepay_month <= tenure_months

    # Sanity: balance at prepay_month exists.
    balance_at_p = sched[prepay_month - 1]["balance"]
    assert balance_at_p >= 0

    res = prepayment_savings(principal, annual_rate, tenure_months, prepay_month, prepay_amount)

    assert res["months_saved"] == 0
    assert res["new_tenure"] == tenure_months
    assert res["interest_saved"] == pytest.approx(0.0, abs=1e-6)


def test_prepayment_greater_than_remaining_balance_pays_off_immediately():
    """
    Explicit requirement:
    If prepayment > remaining balance at prepay_month, loan should be paid off immediately.
    """
    principal = 100_000.00
    annual_rate = 10.0
    tenure_months = 24

    prepay_month = 6
    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    balance_at_p = sched[prepay_month - 1]["balance"]
    assert balance_at_p >= 0

    prepay_amount = balance_at_p + 1.00  # explicitly > remaining balance

    res = prepayment_savings(principal, annual_rate, tenure_months, prepay_month, prepay_amount)

    assert res["new_tenure"] == prepay_month
    assert res["months_saved"] == (tenure_months - prepay_month)
    assert res["interest_saved"] >= 0


def test_prepayment_less_than_balance_shortens_tenure_and_saves_interest():
    """
    Verifies: (1) contract rule:
      positive prepayment less than remaining balance should shorten tenure and save interest.
    """
    principal = 150_000.00
    annual_rate = 9.0
    tenure_months = 60

    prepay_month = 12
    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    balance_at_p = sched[prepay_month - 1]["balance"]
    assert 0 < 10_000.00 < balance_at_p

    res = prepayment_savings(principal, annual_rate, tenure_months, prepay_month, 10_000.00)

    assert res["new_tenure"] < tenure_months
    assert res["months_saved"] > 0
    assert res["interest_saved"] > 0

# ------------------------------------
# E) Validation and remaining tenure
# ------------------------------------

@pytest.mark.parametrize(
    ("principal", "annual_rate", "tenure_months", "message"),
    [
        (100_000.00, 9.0, 0, "tenure must be positive"),
        (100_000.00, 9.0, -12, "tenure must be positive"),
        (0.00, 9.0, 12, "principal must be positive"),
        (-1.00, 9.0, 12, "principal must be positive"),
    ],
)
def test_emi_rejects_non_positive_principal_or_tenure(
    principal,
    annual_rate,
    tenure_months,
    message,
):
    with pytest.raises(ValueError, match=message):
        emi(principal, annual_rate, tenure_months)


def test_outstanding_after_more_than_full_tenure_is_zero():
    result = outstanding_after(
        principal=100_000.00,
        annual_rate=9.0,
        tenure_months=24,
        months_paid=25,
    )

    assert result == 0.0


def test_remaining_tenure_is_zero_when_balance_is_already_paid():
    assert remaining_tenure(
        balance=0.0,
        annual_rate=9.0,
        instalment=5_000.00,
    ) == 0


def test_remaining_tenure_at_zero_interest_uses_simple_division():
    assert remaining_tenure(
        balance=10_000.00,
        annual_rate=0.0,
        instalment=3_000.00,
    ) == 4


def test_remaining_tenure_rejects_instalment_that_cannot_cover_interest():
    with pytest.raises(ValueError, match="instalment too small to repay"):
        remaining_tenure(
            balance=100_000.00,
            annual_rate=12.0,
            instalment=1_000.00,
        )

# -------------------------
# F) Loan offer comparison
# -------------------------

def test_compare_offers_sorts_by_total_cost_and_includes_processing_fee():
    offers = [
        {
            "bank": "Higher Cost Bank",
            "rate": 10.0,
            "tenure": 24,
        },
        {
            "bank": "Lower Cost Bank",
            "rate": 8.0,
            "tenure": 24,
            "processing_fee_pct": 1.0,
        },
    ]

    results = compare_offers(principal=100_000.00, offers=offers)

    assert len(results) == 2
    assert results[0]["total_cost"] <= results[1]["total_cost"]
    assert results[0]["bank"] == "Lower Cost Bank"
    assert results[0]["processing_fee"] == pytest.approx(1_000.00)

    for result in results:
        assert set(result) == {
            "bank",
            "emi",
            "total_interest",
            "processing_fee",
            "total_cost",
        }
        assert result["total_cost"] == pytest.approx(
            result["total_interest"] + result["processing_fee"],
            abs=0.01,
        )

# ---------------------
# G) Eligibility amount
# ---------------------

def test_eligible_amount_is_zero_when_no_income_is_available_for_emi():
    result = eligible_amount(
        monthly_income=50_000.00,
        existing_emis=25_000.00,
        annual_rate=9.0,
        tenure_months=120,
        foir=0.5,
    )

    assert result == 0.0


def test_eligible_amount_at_zero_interest():
    result = eligible_amount(
        monthly_income=100_000.00,
        existing_emis=10_000.00,
        annual_rate=0.0,
        tenure_months=12,
        foir=0.5,
    )

    # Available EMI capacity: 100,000 * 0.5 - 10,000 = 40,000
    # At 0% interest over 12 months: 40,000 * 12 = 480,000.
    assert result == pytest.approx(480_000.00)


def test_eligible_amount_at_interest_matches_available_emi_capacity():
    monthly_income = 100_000.00
    existing_emis = 10_000.00
    foir = 0.5
    annual_rate = 9.0
    tenure_months = 120

    available_emi = monthly_income * foir - existing_emis

    amount = eligible_amount(
        monthly_income=monthly_income,
        existing_emis=existing_emis,
        annual_rate=annual_rate,
        tenure_months=tenure_months,
        foir=foir,
    )

    assert amount > 0
    assert emi(amount, annual_rate, tenure_months) == pytest.approx(
        available_emi,
        abs=0.01,
    )

# ------------------
# H) INR formatting
# ------------------

@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (12.3, "₹12.30"),
        (1_23_456.78, "₹1,23,456.78"),
        (-1_23_456.78, "-₹1,23,456.78"),
        (1_23_45_678.9, "₹1,23,45,678.90"),
    ],
)
def test_format_inr_uses_indian_numbering_and_two_decimal_places(amount, expected):
    assert format_inr(amount) == expected

# -----------------------
# I) CSV and loan summary
# -----------------------

def test_schedule_to_csv_writes_header_and_schedule_rows(tmp_path):
    rows = [
        {
            "month": 1,
            "emi": 10_000.00,
            "interest": 1_000.00,
            "principal": 9_000.00,
            "balance": 91_000.00,
        },
        {
            "month": 2,
            "emi": 10_000.00,
            "interest": 910.00,
            "principal": 9_090.00,
            "balance": 81_910.00,
        },
    ]
    output_path = tmp_path / "schedule.csv"

    result = schedule_to_csv(rows, str(output_path))

    assert result is None
    assert output_path.read_text() == (
        "month,emi,interest,principal,balance\n"
        "1,10000.0,1000.0,9000.0,91000.0\n"
        "2,10000.0,910.0,9090.0,81910.0\n"
    )

def test_summary_returns_formatted_values_and_expected_end_month():
    result = summary(
        principal=1_000_000.00,
        annual_rate=9.0,
        tenure_months=240,
        start=date(2024, 1, 15),
    )

    assert result["principal"] == "₹10,00,000.00"
    assert result["rate"] == "9.0% p.a."
    assert result["tenure"] == "240 months"
    assert result["emi"] == format_inr(
        emi(
            principal=1_000_000.00,
            annual_rate=9.0,
            tenure_months=240,
        )
    )
    assert result["total_interest"].startswith("₹")
    assert result["total_payment"].startswith("₹")
    assert result["last_emi"] == "2044-01"
    assert result["currency"] == "INR"


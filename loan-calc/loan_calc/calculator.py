import math
from datetime import date
from typing import Any, Dict, List, Optional


DEFAULT_CURRENCY = "INR"


def _monthly_rate(annual_rate):
    # Contract: monthly decimal rate must equal annual_rate / 1200 (no rounding).
    return annual_rate / 1200


def emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Calculate the monthly EMI for a loan.

    Args:
        principal: Loan principal amount.
        annual_rate: Annual interest rate in percent.
        tenure_months: Loan tenure in months.

    Returns:
        The monthly equated installment (EMI), rounded to 2 decimals.
    """
    if tenure_months <= 0:
        raise ValueError("tenure must be positive")
    if principal <= 0:
        raise ValueError("principal must be positive")
    r = _monthly_rate(annual_rate)
    if r == 0:
        return round(principal / tenure_months, 2)
    f = (1 + r) ** tenure_months
    return round(principal * r * f / (f - 1), 2)


def total_payment(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Calculate total amount paid over the full tenure.

    Args:
        principal: Loan principal amount.
        annual_rate: Annual interest rate in percent.
        tenure_months: Loan tenure in months.

    Returns:
        Total payment (principal + interest), rounded to 2 decimals.
    """
    return round(emi(principal, annual_rate, tenure_months) * tenure_months, 2)


def total_interest(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Calculate total interest paid over the full tenure.

    Args:
        principal: Loan principal amount.
        annual_rate: Annual interest rate in percent.
        tenure_months: Loan tenure in months.

    Returns:
        Total interest (total payment minus principal), rounded to 2 decimals.
    """
    return round(total_payment(principal, annual_rate, tenure_months) - principal, 2)


def amortisation_schedule(principal: float, annual_rate: float, tenure_months: int) -> List[Dict[str, float]]:
    """Build an amortization schedule for each month.

    Contract:
    - one row per month in the tenure (months 1..tenure_months inclusive)
    - final month should amortise the remaining balance (after rounding)
    """
    r = _monthly_rate(annual_rate)
    instalment = emi(principal, annual_rate, tenure_months)

    balance = principal
    rows: List[Dict[str, float]] = []
    for month in range(1, tenure_months + 1):
        interest = round(balance * r, 2)

        # Default: use fixed EMI (already rounded to 2 decimals).
        principal_part = round(instalment - interest, 2)
        instalment_amt = instalment

        # Final month: force amortisation to clear remaining balance.
        if month == tenure_months:
            principal_part = round(balance, 2)
            instalment_amt = round(principal_part + interest, 2)

        balance = round(balance - principal_part, 2)
        rows.append({
            "month": month,
            "emi": instalment_amt,
            "interest": interest,
            "principal": principal_part,
            "balance": max(balance, 0.0),
        })
    return rows


def outstanding_after(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    months_paid: int,
) -> float:
    """Return the outstanding principal after a given number of months.

    Args:
        principal: Loan principal amount.
        annual_rate: Annual interest rate in percent.
        tenure_months: Total loan tenure in months.
        months_paid: Number of months already paid.

    Returns:
        Remaining loan balance. If months_paid is <= 0, returns principal;
        if months_paid exceeds the schedule length, returns 0.0.
    """
    if months_paid <= 0:
        return round(principal, 2)
    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    if months_paid > len(sched):
        return 0.0
    return sched[months_paid - 1]["balance"]


def remaining_tenure(balance: float, annual_rate: float, instalment: float) -> int:
    """Return the number of months needed to repay a loan balance.

    Args:
        balance: Current outstanding principal.
        annual_rate: Annual interest rate in percent.
        instalment: Fixed monthly EMI amount.

    Returns:
        Number of months remaining (ceiling), or 0 if balance is <= 0.

    Raises:
        ValueError: If the instalment is too small to repay the loan.
    """
    r = annual_rate / 100
    if balance <= 0:
        return 0
    if r == 0:
        return math.ceil(balance / instalment)
    if instalment <= balance * r:
        raise ValueError("instalment too small to repay the loan")
    n = -math.log(1 - balance * r / instalment) / math.log(1 + r)
    return math.ceil(n)


def prepayment_savings(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    prepay_month: int,
    prepay_amount: float,
) -> Dict[str, Any]:
    """Compute EMI/tenure impact and interest savings from a lump-sum prepayment.

    The EMI is kept the same; the remaining tenure is shortened based on the
    reduced balance after the prepayment.

    Args:
        principal: Original loan principal.
        annual_rate: Annual interest rate in percent.
        tenure_months: Original tenure in months.
        prepay_month: 1-based month when the prepayment happens.
        prepay_amount: Lump-sum amount paid at the prepayment month.

    Returns:
        A dictionary containing:
        - emi: Monthly EMI.
        - months_saved: Months reduced vs. original plan.
        - new_tenure: New tenure in months.
        - interest_saved: Total interest saved (rounded to 2 decimals).
        - interest_paid_before_prepayment: Interest accumulated up to prepay month.
    """
    instalment = emi(principal, annual_rate, tenure_months)
    sched = amortisation_schedule(principal, annual_rate, tenure_months)
    balance = sched[prepay_month - 1]["balance"]
    new_balance = balance - prepay_amount
    if new_balance <= 0:
        months_left = 0
    else:
        months_left = remaining_tenure(new_balance, annual_rate, instalment)
    original_left = tenure_months - prepay_month
    interest_paid_so_far = sum(row["interest"] for row in sched[:prepay_month])
    original_interest = total_interest(principal, annual_rate, tenure_months)
    new_total = instalment * prepay_month + prepay_amount + instalment * months_left
    new_interest = new_total - principal
    return {
        "emi": instalment,
        "months_saved": original_left - months_left,
        "new_tenure": prepay_month + months_left,
        "interest_saved": round(original_interest - new_interest, 2),
        "interest_paid_before_prepayment": round(interest_paid_so_far, 2),
    }


def compare_offers(principal: float, offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compare multiple loan offers and rank them by total cost.

    Args:
        principal: Loan principal amount.
        offers: List of offer dicts, each containing:
            - bank (str): Lender name.
            - rate (float): Annual interest rate in percent.
            - tenure (int): Tenure in months.
            - processing_fee_pct (float, optional): Processing fee as % of principal.

    Returns:
        List of result dicts sorted by total cost (ascending), each containing:
        bank, emi, total_interest, processing_fee, and total_cost.
    """
    out = []
    for o in offers:
        e = emi(principal, o["rate"], o["tenure"])
        ti = total_interest(principal, o["rate"], o["tenure"])
        fee = o.get("processing_fee_pct", 0) * principal / 100
        out.append({
            "bank": o["bank"],
            "emi": e,
            "total_interest": ti,
            "processing_fee": round(fee, 2),
            "total_cost": round(ti + fee, 2),
        })
    out.sort(key=lambda x: x["total_cost"])
    return out


def eligible_amount(
    monthly_income: float,
    existing_emis: float,
    annual_rate: float,
    tenure_months: int,
    foir: float = 0.5,
) -> float:
    """Estimate the maximum loan principal eligible under FOIR constraints.

    Args:
        monthly_income: Borrower's monthly income.
        existing_emis: Existing monthly EMIs.
        annual_rate: Annual interest rate in percent.
        tenure_months: Proposed loan tenure in months.
        foir: Fixed Obligation to Income Ratio (default 0.5).

    Returns:
        Maximum eligible principal amount (rounded to 2 decimals).
    """
    available = monthly_income * foir - existing_emis
    if available <= 0:
        return 0.0
    r = _monthly_rate(annual_rate)
    if r == 0:
        return round(available * tenure_months, 2)
    f = (1 + r) ** tenure_months
    return round(available * (f - 1) / (r * f), 2)


def format_inr(amount: float) -> str:
    """Format a float amount as an Indian Rupee string (INR, ₹).

    Uses Indian numbering system (lakhs, crores).

    Args:
        amount: The monetary amount to format.

    Returns:
        A formatted string like '₹1,23,456.78', with a leading '-' for negatives.
    """
    neg = amount < 0
    amount = abs(round(amount, 2))
    whole, frac = f"{amount:.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + tail
    return ("-" if neg else "") + "₹" + whole + "." + frac


def schedule_to_csv(rows: List[Dict[str, float]], path: str) -> None:
    """Write an amortization schedule to a CSV file.

    Args:
        rows: List of schedule rows (each containing month, emi, interest,
            principal, and balance).
        path: Output file path.

    Returns:
        None
    """
    with open(path, "w") as fh:
        fh.write("month,emi,interest,principal,balance\n")
        for r in rows:
            fh.write(f'{r["month"]},{r["emi"]},{r["interest"]},{r["principal"]},{r["balance"]}\n')


def summary(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    start: Optional[date] = None,
) -> Dict[str, Any]:
    """Generate a human-readable loan summary dictionary.

    Args:
        principal: Loan principal amount.
        annual_rate: Annual interest rate in percent.
        tenure_months: Loan tenure in months.
        start: Loan start date (defaults to today).

    Returns:
        A dictionary with formatted strings for: principal, rate, tenure,
        emi, total_interest, total_payment, last_emi date, and currency.
    """
    start = start or date.today()
    e = emi(principal, annual_rate, tenure_months)
    end_year = start.year + (start.month - 1 + tenure_months) // 12
    end_month = (start.month - 1 + tenure_months) % 12 + 1
    return {
        "principal": format_inr(principal),
        "rate": f"{annual_rate}% p.a.",
        "tenure": f"{tenure_months} months",
        "emi": format_inr(e),
        "total_interest": format_inr(total_interest(principal, annual_rate, tenure_months)),
        "total_payment": format_inr(total_payment(principal, annual_rate, tenure_months)),
        "last_emi": f"{end_year}-{end_month:02d}",
        "currency": DEFAULT_CURRENCY,
    }

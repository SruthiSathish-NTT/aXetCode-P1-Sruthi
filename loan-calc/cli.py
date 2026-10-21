import argparse
import json

from loan_calc import amortisation_schedule, prepayment_savings, summary


def main():
    ap = argparse.ArgumentParser(description="Loan calculator")
    ap.add_argument("principal", type=float)
    ap.add_argument("rate", type=float, help="annual interest rate in %")
    ap.add_argument("tenure", type=int, help="tenure in months")
    ap.add_argument("--schedule", action="store_true")
    ap.add_argument("--prepay-month", type=int)
    ap.add_argument("--prepay-amount", type=float)
    a = ap.parse_args()

    print(json.dumps(summary(a.principal, a.rate, a.tenure), indent=2, ensure_ascii=False))
    if a.schedule:
        for row in amortisation_schedule(a.principal, a.rate, a.tenure):
            print(row)
    if a.prepay_month and a.prepay_amount:
        print(json.dumps(prepayment_savings(a.principal, a.rate, a.tenure, a.prepay_month, a.prepay_amount), indent=2))


if __name__ == "__main__":
    main()

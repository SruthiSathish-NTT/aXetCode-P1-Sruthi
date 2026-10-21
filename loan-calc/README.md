# loan-calc (starter for Assignment P1)

A small Python module for retail loan calculations: EMI, amortisation schedule, prepayment savings, offer comparison and eligibility.

It has no tests and no documentation. Users report that some numbers are wrong. Your job is described in Assignment P1.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Try it

```bash
python cli.py 1000000 9 240
python cli.py 1000000 9 240 --schedule
python cli.py 1000000 9 240 --prepay-month 24 --prepay-amount 200000
```

## Run tests (once you have written them)

```bash
pytest --cov=loan_calc --cov-report=term-missing
```

Put your tests in the `tests/` folder.

"""Fail-closed spending policy for ASTRA Studio.

Budget is deliberately fixed at zero in source. Environment variables,
repository secrets and workflow configuration cannot raise this ceiling.
A future nonzero budget requires an explicit reviewed source-code change
following user authorization. This is an application-side guard, not a
replacement for provider billing limits.
"""
from decimal import Decimal

MONTHLY_OPENAI_BUDGET_INR = Decimal("0")
PAID_API_AUTHORIZED = False


def paid_openai_allowed():
    return PAID_API_AUTHORIZED and MONTHLY_OPENAI_BUDGET_INR > 0


def assert_no_paid_api():
    if not paid_openai_allowed():
        raise PermissionError("ASTRA OpenAI API spending blocked: ₹0/month budget")


def policy():
    return {
        "monthly_openai_budget_inr": str(MONTHLY_OPENAI_BUDGET_INR),
        "paid_api_authorized": PAID_API_AUTHORIZED,
        "paid_openai_allowed": paid_openai_allowed(),
    }

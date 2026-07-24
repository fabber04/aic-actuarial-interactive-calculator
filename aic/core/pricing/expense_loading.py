"""Expense loading helpers."""

from __future__ import annotations


def variable_expense_amount(premium: float, expense_ratio: float) -> float:
    return max(0.0, float(premium) * max(0.0, float(expense_ratio)))


def fixed_expense_amount(fixed_expense: float) -> float:
    return max(0.0, float(fixed_expense))

"""ASCII console helpers for reserving reports (cp1252-safe)."""

from __future__ import annotations


def fmt(val: float, decimals: int = 4) -> str:
    return f"{val:,.{decimals}f}"


def banner(title: str, width: int = 70) -> None:
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def section(title: str, width: int = 70) -> None:
    print("\n" + "-" * width)
    print(f"  {title}")
    print("-" * width)

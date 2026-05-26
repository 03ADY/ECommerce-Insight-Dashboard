"""Normalize dates for Streamlit widgets (avoid datetime vs date comparison errors)."""

from datetime import date, datetime

import pandas as pd


def to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def clamp_date(value, lo: date, hi: date) -> date:
    d = to_date(value)
    if d < lo:
        return lo
    if d > hi:
        return hi
    return d


def ordered_range(start, end, lo: date, hi: date) -> tuple[date, date]:
    """Return (start, end) as date objects within bounds, with start <= end."""
    s = clamp_date(start, lo, hi)
    e = clamp_date(end, lo, hi)
    if s > e:
        s, e = e, s
    return s, e

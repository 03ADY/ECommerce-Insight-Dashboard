"""One-click demo scenarios for presenter flow."""

from datetime import timedelta

import pandas as pd


def build_scenarios(df: pd.DataFrame) -> dict[str, dict]:
    dmin = df["purchase_date"].min().normalize()
    dmax = df["purchase_date"].max().normalize()
    all_cats = sorted(df["product_category"].unique().tolist())
    all_genders = sorted(df["gender"].unique().tolist()) if "gender" in df.columns else []

    def _r(days: int) -> tuple:
        end = dmax.date()
        start = (dmax - timedelta(days=days - 1)).date()
        return start, end

    scenarios = {
        "Full dataset": {
            "start": dmin.date(),
            "end": dmax.date(),
            "categories": all_cats,
            "genders": all_genders,
            "blurb": "Complete history — executive overview.",
        },
        "Last 90 days": {
            "start": _r(90)[0],
            "end": _r(90)[1],
            "categories": all_cats,
            "genders": all_genders,
            "blurb": "Recent quarter momentum and trends.",
        },
        "Last 30 days": {
            "start": _r(30)[0],
            "end": _r(30)[1],
            "categories": all_cats,
            "genders": all_genders,
            "blurb": "Short-window pulse check for ops standups.",
        },
        "Electronics focus": {
            "start": dmin.date(),
            "end": dmax.date(),
            "categories": [c for c in all_cats if "electronic" in c.lower()] or all_cats[:1],
            "genders": all_genders,
            "blurb": "Category deep-dive for merchandising.",
        },
        "Beauty & Clothing": {
            "start": dmin.date(),
            "end": dmax.date(),
            "categories": [c for c in all_cats if any(x in c.lower() for x in ("beauty", "cloth"))],
            "genders": all_genders,
            "blurb": "Lifestyle categories bundle performance.",
        },
        "Custom range": {
            "start": dmin.date(),
            "end": dmax.date(),
            "categories": all_cats,
            "genders": all_genders,
            "blurb": "Pick your own dates and filters below.",
        },
    }
    return scenarios

"""Auto-generated executive narrative and insight cards (no LLM required)."""

from datetime import datetime

import pandas as pd

from retail.analytics import (
    compute_kpis,
    estimate_roi,
    new_vs_returning,
    pareto_categories,
    rfm_segments,
)


def _trend_word(pct: float | None) -> str:
    if pct is None:
        return "flat"
    if pct >= 5:
        return "up strongly"
    if pct > 0:
        return "up"
    if pct <= -5:
        return "down sharply"
    if pct < 0:
        return "down"
    return "flat"


def insight_cards(
    df: pd.DataFrame,
    deltas: dict,
    *,
    top_category: str | None = None,
    at_risk_pct: float | None = None,
    returning_share: float | None = None,
    forecast_growth: float | None = None,
) -> list[dict]:
    rev_pct = deltas.get("revenue")
    cards = [
        {
            "icon": "📈",
            "title": "Revenue trend",
            "body": f"Revenue is {_trend_word(rev_pct)}"
            + (f" ({rev_pct:+.1f}% vs prior period)." if rev_pct is not None else "."),
            "tone": "positive" if (rev_pct or 0) >= 0 else "warning",
        },
        {
            "icon": "🏷️",
            "title": "Category leader",
            "body": f"{top_category or 'N/A'} drives the largest share of filtered revenue.",
            "tone": "neutral",
        },
        {
            "icon": "👥",
            "title": "Customer mix",
            "body": f"Returning buyers contribute {returning_share or 0:.0f}% of revenue — "
            f"{'healthy loyalty' if (returning_share or 0) >= 50 else 'acquisition-heavy period'}.",
            "tone": "positive" if (returning_share or 0) >= 50 else "neutral",
        },
        {
            "icon": "⚠️",
            "title": "Retention watch",
            "body": f"{at_risk_pct or 0:.0f}% of segmented customers are At Risk — prioritize win-back.",
            "tone": "warning" if (at_risk_pct or 0) > 20 else "positive",
        },
    ]
    if forecast_growth is not None:
        cards.append({
            "icon": "🔮",
            "title": "Forecast outlook",
            "body": f"Model projects {forecast_growth:+.1f}% revenue change vs recent run-rate over the forecast window.",
            "tone": "positive" if forecast_growth >= 0 else "warning",
        })
    return cards


def _top_category(df: pd.DataFrame) -> str:
    if df.empty:
        return "—"
    return df.groupby("product_category")["amount"].sum().idxmax()


def _at_risk_share(rfm: pd.DataFrame) -> float:
    if rfm.empty:
        return 0.0
    n = len(rfm)
    return rfm[rfm["segment"] == "At Risk"].shape[0] / n * 100


def _returning_share(df: pd.DataFrame) -> float:
    nvr = new_vs_returning(df)
    row = nvr[nvr["buyer_type"] == "Returning"]
    return float(row["revenue_share"].iloc[0]) if not row.empty else 0.0


def _forecast_growth_pct(df: pd.DataFrame, fc: pd.DataFrame) -> float | None:
    if fc.empty or df.empty:
        return None
    recent = df.groupby(df["purchase_date"].dt.date)["amount"].sum().tail(14).mean()
    projected = fc["yhat"].head(14).mean()
    if not recent:
        return None
    return ((projected - recent) / recent) * 100


def build_context(
    df: pd.DataFrame,
    df_prior: pd.DataFrame,
    deltas: dict,
    start,
    end,
    scenario_name: str,
    fc: pd.DataFrame | None = None,
) -> dict:
    rfm = rfm_segments(df)
    kpis = compute_kpis(df)
    roi = estimate_roi(rfm, uplift_pct=10)
    return {
        "kpis": kpis,
        "deltas": deltas,
        "top_category": _top_category(df),
        "at_risk_pct": _at_risk_share(rfm),
        "returning_share": _returning_share(df),
        "forecast_growth": _forecast_growth_pct(df, fc) if fc is not None else None,
        "pareto_cats_to_80": int((pareto_categories(df)["cumulative_pct"] <= 80).sum()),
        "roi_uplift": roi["annual_uplift"],
        "period": f"{start} → {end}",
        "scenario": scenario_name,
        "orders_prior": compute_kpis(df_prior)["orders"] if not df_prior.empty else 0,
    }


def executive_brief(ctx: dict) -> str:
    rev = ctx["kpis"]["revenue"]
    d_rev = ctx["deltas"].get("revenue")
    lines = [
        f"# CommerceIQ Executive Brief",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Scenario: **{ctx['scenario']}** · Period: {ctx['period']}",
        "",
        "## Headline",
        f"Total revenue **${rev:,.0f}**"
        + (f" ({d_rev:+.1f}% vs prior period)." if d_rev is not None else "."),
        "",
        "## Key findings",
        f"- Leading category: **{ctx['top_category']}**.",
        f"- Returning customer revenue share: **{ctx['returning_share']:.0f}%**.",
        f"- At Risk segment: **{ctx['at_risk_pct']:.0f}%** of RFM-scored customers.",
        f"- Top categories to 80% revenue: **{ctx['pareto_cats_to_80']}**.",
    ]
    if ctx.get("forecast_growth") is not None:
        lines.append(f"- Forecast vs recent run-rate: **{ctx['forecast_growth']:+.1f}%**.")
    lines.extend([
        "",
        "## Recommended actions",
        "- Launch win-back for At Risk segment with limited-time offer.",
        "- Double down on top category merchandising and cross-sell bundles.",
        f"- Modeled retention uplift (+10% on target segments): **${ctx['roi_uplift']:,.0f}**/year.",
        "",
        "---",
        "*CommerceIQ Enterprise — demo analytics brief*",
    ])
    return "\n".join(lines)


def data_quality_score(df: pd.DataFrame) -> dict:
    n = len(df)
    dup_orders = df["order_id"].duplicated().sum() if "order_id" in df.columns else 0
    null_amount = df["amount"].isna().sum()
    future = (df["purchase_date"] > pd.Timestamp.now()).sum() if "purchase_date" in df.columns else 0
    issues = dup_orders + null_amount + future
    score = max(0, 100 - min(issues / max(n, 1) * 100, 30))
    return {
        "score": round(score, 1),
        "rows": n,
        "duplicate_lines": int(dup_orders),
        "null_amounts": int(null_amount),
        "future_dates": int(future),
        "status": "Excellent" if score >= 95 else "Good" if score >= 85 else "Review",
    }

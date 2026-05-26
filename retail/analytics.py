"""Retail analytics engine — KPIs, RFM, forecasting, cohorts, ROI."""

from datetime import timedelta

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from statsmodels.tsa.arima.model import ARIMA

SEGMENT_PLAYBOOKS = {
    "Champions": "VIP early access, loyalty rewards, referral program",
    "Loyal": "Cross-sell bundles, category expansion offers",
    "Potential": "Onboarding series, second-purchase incentive within 14 days",
    "At Risk": "Win-back email/SMS, limited-time discount, satisfaction survey",
}

AGE_BINS = [0, 25, 35, 45, 55, 65, 120]
AGE_LABELS = ["18–25", "26–35", "36–45", "46–55", "56–65", "65+"]


def compute_kpis(df: pd.DataFrame) -> dict:
    orders = df["order_id"].nunique()
    revenue = float(df["amount"].sum())
    return {
        "revenue": revenue,
        "orders": orders,
        "aov": revenue / orders if orders else 0.0,
        "customers": df["customer_id"].nunique(),
        "units": int(df["quantity"].sum()) if "quantity" in df.columns else 0,
    }


def _pct_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None if current == 0 else 100.0
    return ((current - previous) / previous) * 100


def period_comparison(df_current: pd.DataFrame, df_prior: pd.DataFrame) -> dict:
    """Compare KPIs between current and equal-length prior period."""
    cur, pri = compute_kpis(df_current), compute_kpis(df_prior)
    deltas = {}
    for key in cur:
        deltas[key] = _pct_change(cur[key], pri[key])
    return {"current": cur, "prior": pri, "delta_pct": deltas}


def prior_period_slice(df: pd.DataFrame, start, end) -> pd.DataFrame:
    """Return rows for the period immediately before [start, end], same length."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    days = (end - start).days + 1
    prior_end = start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=days - 1)
    return df[
        (df["purchase_date"].dt.date >= prior_start.date())
        & (df["purchase_date"].dt.date <= prior_end.date())
    ]


def new_vs_returning(df: pd.DataFrame) -> pd.DataFrame:
    first = df.groupby("customer_id")["purchase_date"].min().rename("first_purchase")
    orders = (
        df.groupby("order_id")
        .agg(amount=("amount", "sum"), customer_id=("customer_id", "first"), purchase_date=("purchase_date", "min"))
        .reset_index()
    )
    orders = orders.merge(first, on="customer_id")
    orders["buyer_type"] = np.where(
        orders["purchase_date"].dt.normalize() == orders["first_purchase"].dt.normalize(),
        "New",
        "Returning",
    )
    summary = (
        orders.groupby("buyer_type")
        .agg(revenue=("amount", "sum"), orders=("order_id", "nunique"))
        .reset_index()
    )
    total_rev = summary["revenue"].sum()
    summary["revenue_share"] = (summary["revenue"] / total_rev * 100).round(1) if total_rev else 0
    return summary


def pareto_customers(df: pd.DataFrame, top_pct: float = 0.2) -> dict:
    spend = df.groupby("customer_id")["amount"].sum().sort_values(ascending=False)
    if spend.empty:
        return {"top_share_customers": 0, "top_share_revenue": 0, "curve": pd.DataFrame()}
    n_top = max(1, int(len(spend) * top_pct))
    top_rev = spend.head(n_top).sum()
    total = spend.sum()
    cum = spend.cumsum() / total * 100
    curve = pd.DataFrame({
        "customer_rank_pct": np.linspace(0, 100, len(cum)),
        "cumulative_revenue_pct": cum.values,
    })
    return {
        "top_share_customers": round(n_top / len(spend) * 100, 1),
        "top_share_revenue": round(top_rev / total * 100, 1) if total else 0,
        "curve": curve,
    }


def pareto_categories(df: pd.DataFrame) -> pd.DataFrame:
    cat = (
        df.groupby("product_category")["amount"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    cat.columns = ["product_category", "revenue"]
    total = cat["revenue"].sum()
    cat["cumulative_pct"] = (cat["revenue"].cumsum() / total * 100).round(1) if total else 0
    cat["revenue_share"] = (cat["revenue"] / total * 100).round(1) if total else 0
    return cat


def demographics_summary(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = df.copy()
    if "age" in d.columns:
        d["age_band"] = pd.cut(d["age"], bins=AGE_BINS, labels=AGE_LABELS, right=True)
        by_age = (
            d.groupby("age_band", observed=True)
            .agg(revenue=("amount", "sum"), customers=("customer_id", "nunique"))
            .reset_index()
        )
    else:
        by_age = pd.DataFrame(columns=["age_band", "revenue", "customers"])

    if "gender" in d.columns:
        cross = (
            d.groupby(["gender", "product_category"], observed=True)["amount"]
            .sum()
            .reset_index()
        )
    else:
        cross = pd.DataFrame(columns=["gender", "product_category", "amount"])
    return by_age, cross


def basket_stats(df: pd.DataFrame) -> dict:
    per_order = df.groupby("order_id").agg(
        lines=("order_id", "count"),
        units=("quantity", "sum") if "quantity" in df.columns else ("order_id", "count"),
        amount=("amount", "sum"),
    )
    avg_units = per_order["units"].mean() if not per_order.empty else 0
    if "price_per_unit" in df.columns and "quantity" in df.columns:
        expected = (df["quantity"] * df["price_per_unit"]).sum()
        actual = df["amount"].sum()
        discount_gap = max(0, expected - actual)
    else:
        discount_gap = 0.0
    return {
        "avg_units_per_order": round(avg_units, 2),
        "avg_lines_per_order": round(per_order["lines"].mean(), 2) if not per_order.empty else 0,
        "total_discount_gap": round(discount_gap, 2),
    }


def rfm_segments(df: pd.DataFrame, n_clusters: int = 4) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    snap = df["purchase_date"].max() + timedelta(days=1)
    rfm = df.groupby("customer_id").agg(
        recency=("purchase_date", lambda d: (snap - d.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("amount", "sum"),
    ).reset_index()
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    rfm["cluster"] = km.fit_predict(rfm[["recency", "frequency", "monetary"]])
    centers = km.cluster_centers_
    order = sorted(range(n_clusters), key=lambda i: centers[i][2], reverse=True)
    labels = ["Champions", "Loyal", "Potential", "At Risk"]
    rfm["segment"] = rfm["cluster"].map({order[i]: labels[i] for i in range(n_clusters)})
    rfm["playbook"] = rfm["segment"].map(SEGMENT_PLAYBOOKS)
    return rfm


def cohort_retention(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["month"] = d["purchase_date"].dt.to_period("M")
    first = d.groupby("customer_id")["month"].min().rename("cohort")
    d = d.join(first, on="customer_id")
    cohort = d.groupby(["cohort", "month"]).agg(customers=("customer_id", "nunique")).reset_index()
    cohort["period"] = (cohort["month"] - cohort["cohort"]).apply(lambda x: x.n)
    return cohort.pivot(index="cohort", columns="period", values="customers").fillna(0)


def cohort_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly revenue retained by acquisition cohort."""
    d = df.copy()
    d["month"] = d["purchase_date"].dt.to_period("M")
    first = d.groupby("customer_id")["month"].min().rename("cohort")
    d = d.join(first, on="customer_id")
    cohort = d.groupby(["cohort", "month"]).agg(revenue=("amount", "sum")).reset_index()
    cohort["period"] = (cohort["month"] - cohort["cohort"]).apply(lambda x: x.n)
    return cohort.pivot(index="cohort", columns="period", values="revenue").fillna(0)


def cohort_ltv_curve(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["month"] = d["purchase_date"].dt.to_period("M")
    first = d.groupby("customer_id")["month"].min().rename("cohort")
    d = d.join(first, on="customer_id")
    d["period"] = (d["month"] - d["cohort"]).apply(lambda x: x.n)
    rev = d.groupby(["cohort", "period"])["amount"].sum().reset_index()
    rev["cumulative_revenue"] = rev.groupby("cohort")["amount"].cumsum()
    return rev


def estimate_roi(rfm: pd.DataFrame, uplift_pct: float = 10.0) -> dict:
    """Rough annualized uplift if At Risk / Potential segments increase spend."""
    if rfm.empty:
        return {"annual_uplift": 0, "segments": pd.DataFrame()}
    seg = rfm.groupby("segment").agg(
        customers=("customer_id", "count"),
        avg_spend=("monetary", "mean"),
        total_spend=("monetary", "sum"),
    ).reset_index()
    target = seg[seg["segment"].isin(["At Risk", "Potential"])]
    monthly_base = target["total_spend"].sum() / 12 if target["total_spend"].sum() else 0
    uplift = monthly_base * (uplift_pct / 100) * 12
    seg["targeted"] = seg["segment"].isin(["At Risk", "Potential"])
    return {"annual_uplift": round(uplift, 2), "segments": seg, "uplift_pct": uplift_pct}


def forecast_revenue(df: pd.DataFrame, periods: int = 90) -> tuple[pd.DataFrame, str | None, dict]:
    empty = pd.DataFrame(columns=["ds", "yhat", "yhat_lower", "yhat_upper"])
    meta = {"mape": None, "model": "ARIMA(5,1,0)"}
    if len(df) < 14:
        return empty, "Need at least 14 days of data.", meta
    daily = df.set_index("purchase_date").resample("D")["amount"].sum().fillna(0)
    if (daily > 0).sum() < 10:
        return empty, "Insufficient sales days for forecasting.", meta

    holdout = min(14, len(daily) // 4)
    try:
        if holdout >= 7:
            train, test = daily.iloc[:-holdout], daily.iloc[-holdout:]
            fit_bt = ARIMA(train, order=(5, 1, 0)).fit()
            pred = fit_bt.forecast(steps=holdout)
            mask = test.values != 0
            if mask.any():
                mape = np.mean(np.abs((test.values[mask] - pred.values[mask]) / test.values[mask])) * 100
                meta["mape"] = round(float(mape), 2)

        fit = ARIMA(daily, order=(5, 1, 0)).fit()
        frame = fit.get_forecast(steps=periods).summary_frame().reset_index()
        frame.columns = ["ds", "yhat", "se", "yhat_lower", "yhat_upper"]
        return frame[["ds", "yhat", "yhat_lower", "yhat_upper"]], None, meta
    except Exception as exc:
        return empty, str(exc), meta


def forecast_by_category(df: pd.DataFrame, periods: int = 30, top_n: int = 4) -> pd.DataFrame:
    cats = df.groupby("product_category")["amount"].sum().nlargest(top_n).index.tolist()
    rows = []
    for cat in cats:
        sub = df[df["product_category"] == cat]
        daily = sub.set_index("purchase_date").resample("D")["amount"].sum().fillna(0)
        if (daily > 0).sum() < 7:
            continue
        try:
            fit = ARIMA(daily, order=(2, 1, 0)).fit()
            fc = fit.forecast(steps=periods)
            for i, val in enumerate(fc.values):
                rows.append({"ds": daily.index[-1] + timedelta(days=i + 1), "category": cat, "yhat": val})
        except Exception:
            continue
    return pd.DataFrame(rows)


def detect_anomalies(df: pd.DataFrame, window: int = 7, sigma: float = 2.0) -> pd.DataFrame:
    daily = df.groupby(df["purchase_date"].dt.date)["amount"].sum().reset_index()
    daily.columns = ["date", "revenue"]
    if len(daily) < window + 2:
        return pd.DataFrame(columns=["date", "revenue", "z_score", "anomaly"])
    roll = daily["revenue"].rolling(window, min_periods=window).mean()
    std = daily["revenue"].rolling(window, min_periods=window).std().replace(0, np.nan)
    daily["z_score"] = ((daily["revenue"] - roll) / std).round(2)
    daily["anomaly"] = daily["z_score"].abs() >= sigma
    return daily.dropna(subset=["z_score"])


def product_leaderboard(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return (
        df.groupby("product_category")
        .agg(revenue=("amount", "sum"), orders=("order_id", "nunique"), units=("quantity", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(n)
    )

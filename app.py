"""CommerceIQ Enterprise — retail analytics command center."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from retail.analytics import (
    SEGMENT_PLAYBOOKS,
    basket_stats,
    cohort_ltv_curve,
    cohort_retention,
    cohort_revenue,
    compute_kpis,
    demographics_summary,
    detect_anomalies,
    estimate_roi,
    forecast_by_category,
    forecast_revenue,
    new_vs_returning,
    pareto_categories,
    pareto_customers,
    period_comparison,
    prior_period_slice,
    product_leaderboard,
    rfm_segments,
)
from retail.config import APP_NAME, DAY_ORDER
from retail.data import filter_sales, load_sales
from retail.insights import (
    build_context,
    data_quality_score,
    executive_brief,
    insight_cards,
)
from retail.scenarios import build_scenarios

st.set_page_config(page_title=APP_NAME, page_icon="📊", layout="wide")

st.markdown("""
<style>
.insight-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; margin: 0.5rem 0 1rem; }
.insight-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 0.9rem 1rem; border-left: 4px solid #6366f1; }
.insight-card.warning { border-left-color: #f59e0b; }
.insight-card.positive { border-left-color: #22c55e; }
.insight-card h4 { margin: 0 0 0.35rem; font-size: 0.85rem; color: #64748b; }
.insight-card p { margin: 0; font-size: 0.92rem; color: #0f172a; line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background:linear-gradient(135deg,#0ea5e9,#6366f1);padding:1.5rem 2rem;border-radius:14px;color:white;margin-bottom:1rem;">
<h1 style="margin:0;">📊 {APP_NAME}</h1>
<p style="margin:0.4rem 0 0;opacity:0.9;">Demo scenarios · Executive brief · Goal tracking · Drill-down</p>
</div>
""", unsafe_allow_html=True)


def _delta_label(pct: float | None) -> str:
    if pct is None:
        return "—"
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}% vs prior period"


def _metric_with_delta(col, label: str, value: str, pct: float | None):
    delta = _delta_label(pct) if pct is not None else None
    with col:
        st.metric(label, value, delta=delta)


def _render_insight_cards(cards: list[dict]):
    html = '<div class="insight-grid">'
    for c in cards[:5]:
        html += f'<div class="insight-card {c.get("tone", "neutral")}"><h4>{c["icon"]} {c["title"]}</h4><p>{c["body"]}</p></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


df_full = load_sales()
if df_full is None:
    st.error("Place `retail_sales_dataset.csv` in the project folder.")
    st.stop()

scenarios = build_scenarios(df_full)
dmin, dmax = df_full["purchase_date"].min().date(), df_full["purchase_date"].max().date()
all_cats = sorted(df_full["product_category"].unique())
all_genders = sorted(df_full["gender"].unique()) if "gender" in df_full.columns else []

with st.sidebar:
    st.markdown("### 🎬 Demo")
    present_mode = st.toggle("Present mode", value=True, help="Cleaner layout for live demos")
    scenario = st.selectbox("Scenario", list(scenarios.keys()), index=1)
    st.caption(scenarios[scenario]["blurb"])

    preset = scenarios[scenario]
    use_custom_dates = scenario == "Custom range" or st.checkbox("Edit dates & filters", value=(scenario == "Custom range"))

    if use_custom_dates:
        start, end = st.date_input("Date range", [preset["start"], preset["end"]], min_value=dmin, max_value=dmax)
        cats = st.multiselect("Categories", all_cats, default=preset["categories"])
        genders = st.multiselect("Gender", all_genders, default=preset["genders"]) if all_genders else []
    else:
        start, end = preset["start"], preset["end"]
        cats, genders = preset["categories"], preset["genders"]
        st.success(f"📅 {start} → {end}")

    st.markdown("---")
    forecast_days = 90 if present_mode else st.slider("Forecast horizon (days)", 30, 180, 90, 15)
    roi_uplift = 10 if present_mode else st.slider("ROI uplift (%)", 5, 25, 10)
    revenue_goal = 0.0 if present_mode else st.number_input(
        "Revenue goal ($)", min_value=0.0, value=0.0, step=1000.0, help="0 = auto (110% of prior period)"
    )

    dq = data_quality_score(df_full)
    st.markdown("### Data health")
    st.progress(min(dq["score"] / 100, 1.0), text=f"{dq['status']} · {dq['score']}%")

    if st.button("📥 Export filtered CSV"):
        st.session_state["export"] = True

df = filter_sales(df_full, start, end, cats, genders or None)
if df.empty:
    st.warning("No data for selected filters.")
    st.stop()

df_prior = prior_period_slice(df_full, start, end)
if not df_prior.empty:
    df_prior = filter_sales(
        df_prior,
        df_prior["purchase_date"].min().date(),
        df_prior["purchase_date"].max().date(),
        cats,
        genders or None,
    )

if not df_prior.empty:
    cmp = period_comparison(df, df_prior)
else:
    cur = compute_kpis(df)
    cmp = {
        "current": cur,
        "prior": {k: 0 for k in cur},
        "delta_pct": {k: None for k in cur},
    }
kpis, deltas = cmp["current"], cmp["delta_pct"]

fc, fc_err, fc_meta = forecast_revenue(df, forecast_days)
ctx = build_context(df, df_prior, deltas, start, end, scenario, fc if not fc_err else None)
cards = insight_cards(
    df, deltas,
    top_category=ctx["top_category"],
    at_risk_pct=ctx["at_risk_pct"],
    returning_share=ctx["returning_share"],
    forecast_growth=ctx.get("forecast_growth"),
)
brief = executive_brief(ctx)

c1, c2, c3, c4, c5 = st.columns(5)
_metric_with_delta(c1, "Revenue", f"${kpis['revenue']:,.0f}", deltas.get("revenue"))
_metric_with_delta(c2, "Orders", f"{kpis['orders']:,}", deltas.get("orders"))
_metric_with_delta(c3, "AOV", f"${kpis['aov']:,.2f}", deltas.get("aov"))
_metric_with_delta(c4, "Customers", f"{kpis['customers']:,}", deltas.get("customers"))
_metric_with_delta(c5, "Units sold", f"{kpis['units']:,}", deltas.get("units"))

prior_rev = cmp["prior"]["revenue"] if not df_prior.empty else kpis["revenue"] * 0.9
goal = revenue_goal if revenue_goal > 0 else prior_rev * 1.1
progress = min(kpis["revenue"] / goal, 1.0) if goal else 0
g1, g2 = st.columns([3, 1])
with g1:
    st.progress(progress, text=f"Revenue goal: ${kpis['revenue']:,.0f} / ${goal:,.0f} ({progress*100:.0f}%)")
with g2:
    if fc_meta.get("mape"):
        st.caption(f"Forecast MAPE: **{fc_meta['mape']:.1f}%**")

st.markdown("#### 💡 Executive insights")
_render_insight_cards(cards)

with st.expander("📑 Executive brief & download", expanded=present_mode):
    st.markdown(brief)
    st.download_button("Download brief (.md)", brief.encode(), "commerceiq_executive_brief.md")

if st.session_state.get("export"):
    st.download_button("Download filtered data", df.to_csv(index=False).encode(), "filtered_sales.csv")

tabs = st.tabs([
    "📈 Overview",
    "👥 Customers",
    "🎯 Demographics",
    "👥 RFM & Playbooks",
    "🔮 Forecast",
    "📋 Cohorts",
    "💰 Business ROI",
    "🔍 Drill-down",
])

with tabs[0]:
    daily = df.groupby(df["purchase_date"].dt.date)["amount"].sum().reset_index()
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Daily revenue", "By category", "Day of week", "Gender"),
        specs=[[{}, {}], [{}, {"type": "pie"}]],
        vertical_spacing=0.12,
    )
    fig.add_trace(go.Scatter(x=daily["purchase_date"], y=daily["amount"], mode="lines", name="Revenue"), row=1, col=1)
    top = df.groupby("product_category")["amount"].sum().nlargest(6).reset_index()
    fig.add_trace(go.Bar(x=top["product_category"], y=top["amount"]), row=1, col=2)
    dow = df.copy()
    dow["dow"] = dow["purchase_date"].dt.day_name()
    by_dow = dow.groupby("dow")["amount"].sum().reindex(DAY_ORDER).fillna(0)
    fig.add_trace(go.Bar(x=by_dow.index, y=by_dow.values), row=2, col=1)
    if "gender" in df.columns:
        g = df.groupby("gender")["amount"].sum()
        fig.add_trace(go.Pie(labels=g.index, values=g.values, hole=0.4), row=2, col=2)
    fig.update_layout(height=700, showlegend=False, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    anomalies = detect_anomalies(df)
    if not anomalies.empty and anomalies["anomaly"].any():
        st.subheader("⚠️ Revenue anomalies")
        st.dataframe(anomalies[anomalies["anomaly"]][["date", "revenue", "z_score"]], use_container_width=True, hide_index=True)

with tabs[1]:
    nvr = new_vs_returning(df)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.plotly_chart(px.bar(nvr, x="buyer_type", y="revenue", color="buyer_type", title="Revenue by buyer type"), use_container_width=True)
    with col2:
        st.dataframe(nvr, use_container_width=True, hide_index=True)

    p_cust, p_cat = pareto_customers(df), pareto_categories(df)
    m1, m2 = st.columns(2)
    m1.metric("Top 20% customers → revenue", f"{p_cust['top_share_revenue']:.1f}%")
    m2.metric("Categories to 80% revenue", f"{(p_cat['cumulative_pct'] <= 80).sum()}")

    pc1, pc2 = st.columns(2)
    with pc1:
        if not p_cust["curve"].empty:
            st.plotly_chart(px.line(p_cust["curve"], x="customer_rank_pct", y="cumulative_revenue_pct", title="Concentration curve"), use_container_width=True)
    with pc2:
        st.plotly_chart(px.bar(p_cat.head(8), x="product_category", y="revenue", title="Category Pareto"), use_container_width=True)

    bs = basket_stats(df)
    b1, b2, b3 = st.columns(3)
    b1.metric("Avg units / order", bs["avg_units_per_order"])
    b2.metric("Avg lines / order", bs["avg_lines_per_order"])
    b3.metric("Pricing gap", f"${bs['total_discount_gap']:,.0f}")

with tabs[2]:
    by_age, cross = demographics_summary(df)
    d1, d2 = st.columns(2)
    with d1:
        if not by_age.empty:
            st.plotly_chart(px.bar(by_age, x="age_band", y="revenue", title="Revenue by age"), use_container_width=True)
    with d2:
        if "gender" in df.columns:
            gsum = df.groupby("gender")["amount"].sum().reset_index()
            st.plotly_chart(px.pie(gsum, names="gender", values="amount", hole=0.4), use_container_width=True)
    if not cross.empty:
        pivot = cross.pivot(index="gender", columns="product_category", values="amount").fillna(0)
        st.plotly_chart(px.imshow(pivot, labels=dict(color="Revenue"), aspect="auto"), use_container_width=True)

with tabs[3]:
    rfm = rfm_segments(df)
    col_a, col_b = st.columns(2)
    with col_a:
        seg = rfm["segment"].value_counts().reset_index()
        seg.columns = ["segment", "count"]
        st.plotly_chart(px.pie(seg, names="segment", values="count", hole=0.45), use_container_width=True)
    with col_b:
        st.plotly_chart(px.scatter(rfm, x="frequency", y="monetary", color="segment", size="recency", hover_data=["playbook"]), use_container_width=True)

    summary = rfm.groupby("segment").agg(customers=("customer_id", "count"), avg_spend=("monetary", "mean")).round(2).reset_index()
    summary["recommended_action"] = summary["segment"].map(SEGMENT_PLAYBOOKS)
    st.dataframe(summary, use_container_width=True, hide_index=True)

    seg_pick = st.selectbox("Export segment", sorted(rfm["segment"].unique()))
    seg_df = rfm[rfm["segment"] == seg_pick][["customer_id", "recency", "frequency", "monetary", "segment", "playbook"]]
    st.download_button(f"Download {seg_pick}", seg_df.to_csv(index=False).encode(), f"segment_{seg_pick.lower().replace(' ', '_')}.csv")

with tabs[4]:
    if fc_meta.get("mape") is not None:
        st.metric("Backtest MAPE", f"{fc_meta['mape']:.1f}%")
    if fc_err:
        st.info(fc_err)
    elif not fc.empty:
        fig = go.Figure()
        hist = df.groupby(df["purchase_date"].dt.date)["amount"].sum().reset_index()
        fig.add_trace(go.Scatter(x=hist["purchase_date"], y=hist["amount"], mode="lines", name="Actual"))
        fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat"], mode="lines", name="Forecast"))
        fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat_upper"], fill=None, mode="lines", line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat_lower"], fill="tonexty", name="Band"))
        fig.update_layout(title=f"{forecast_days}-day forecast", height=450, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    cat_fc = forecast_by_category(df, periods=min(30, forecast_days))
    if not cat_fc.empty:
        st.plotly_chart(px.line(cat_fc, x="ds", y="yhat", color="category"), use_container_width=True)

with tabs[5]:
    st.dataframe(product_leaderboard(df), use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        cohort = cohort_retention(df)
        if not cohort.empty:
            st.dataframe(cohort.style.background_gradient(cmap="Blues", axis=None), use_container_width=True)
    with c2:
        rev_cohort = cohort_revenue(df)
        if not rev_cohort.empty:
            st.dataframe(rev_cohort.style.background_gradient(cmap="Greens", axis=None), use_container_width=True)
    ltv = cohort_ltv_curve(df)
    if not ltv.empty:
        st.plotly_chart(px.line(ltv, x="period", y="cumulative_revenue", color="cohort", markers=True), use_container_width=True)

with tabs[6]:
    rfm = rfm_segments(df)
    roi = estimate_roi(rfm, uplift_pct=roi_uplift)
    st.metric("Projected annual uplift", f"${roi['annual_uplift']:,.0f}", help=f"At {roi_uplift}% uplift on At Risk + Potential")
    st.plotly_chart(px.bar(roi["segments"], x="segment", y="total_spend", color="targeted"), use_container_width=True)
    for seg, action in SEGMENT_PLAYBOOKS.items():
        st.markdown(f"- **{seg}:** {action}")

with tabs[7]:
    st.markdown("Inspect individual transactions for any category.")
    drill_cat = st.selectbox("Category", ["All"] + sorted(df["product_category"].unique()))
    drill_df = df if drill_cat == "All" else df[df["product_category"] == drill_cat]
    show_cols = [c for c in ["purchase_date", "order_id", "customer_id", "product_category", "quantity", "amount", "gender", "age"] if c in drill_df.columns]
    st.dataframe(drill_df[show_cols].sort_values("purchase_date", ascending=False).head(100), use_container_width=True, hide_index=True)
    st.download_button("Export drill-down (100 rows)", drill_df[show_cols].head(100).to_csv(index=False).encode(), "drill_down.csv")

st.caption(f"{APP_NAME} · Presenter guide: DEMO.md · Preview: docs/demo-preview.svg")

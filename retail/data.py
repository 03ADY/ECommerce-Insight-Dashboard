import os
from pathlib import Path

import pandas as pd
import streamlit as st

from retail.config import DEFAULT_CSV


@st.cache_data(show_spinner="Loading retail dataset…")
def load_sales(csv_path: str | Path | None = None) -> pd.DataFrame | None:
    path = Path(csv_path or os.getenv("SALES_CSV_PATH", DEFAULT_CSV))
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df.rename(columns={
        "Transaction ID": "order_id", "Date": "purchase_date",
        "Customer ID": "customer_id", "Product Category": "product_category",
        "Total Amount": "amount", "Quantity": "quantity",
        "Price per Unit": "price_per_unit", "Gender": "gender", "Age": "age",
    }, inplace=True)
    df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
    df.dropna(subset=["order_id", "customer_id", "amount", "product_category", "purchase_date"], inplace=True)
    return df


def filter_sales(
    df: pd.DataFrame,
    start,
    end,
    categories: list[str],
    genders: list[str] | None = None,
) -> pd.DataFrame:
    mask = (
        (df["purchase_date"].dt.date >= start)
        & (df["purchase_date"].dt.date <= end)
        & (df["product_category"].isin(categories))
    )
    if genders and "gender" in df.columns:
        mask &= df["gender"].isin(genders)
    return df[mask]

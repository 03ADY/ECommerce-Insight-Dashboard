# app.py
# To run this app, save it as app.py and run: streamlit run app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
from statsmodels.tsa.arima.model import ARIMA
import logging
import warnings

# Suppress warnings from statsmodels
warnings.filterwarnings("ignore")

# --- Page Configuration ---
st.set_page_config(
    page_title="E-commerce Sales Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
CSV_FILE_PATH = "retail_sales_dataset.csv"

# --- Data Loading and Caching ---
@st.cache_data
def load_and_clean_data(csv_path: str) -> pd.DataFrame:
    """Loads and preprocesses the real sales data from a CSV file."""
    try:
        logging.info(f"Loading data from {csv_path}...")
        df = pd.read_csv(csv_path)
        
        df.rename(columns={
            'Transaction ID': 'order_id', 'Date': 'purchase_date',
            'Customer ID': 'customer_id', 'Product Category': 'product_category',
            'Total Amount': 'amount', 'Quantity': 'quantity',
            'Price per Unit': 'price_per_unit', 'Gender': 'gender'
        }, inplace=True)

        df['purchase_date'] = pd.to_datetime(df['purchase_date'])
        df.dropna(subset=['order_id', 'customer_id', 'amount', 'product_category'], inplace=True)
        
        logging.info("Data loaded and cleaned successfully.")
        return df
    except FileNotFoundError:
        st.error(f"Error: The data file was not found at '{csv_path}'. Please make sure it's in the same folder as the app.")
        return None

# --- Analysis Functions ---
def perform_rfm_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Perform RFM (Recency, Frequency, Monetary) analysis."""
    if df.empty:
        return pd.DataFrame(columns=['customer_id', 'recency', 'frequency', 'monetary', 'segment'])
        
    snapshot_date = df['purchase_date'].max() + timedelta(days=1)
    
    rfm = df.groupby('customer_id').agg(
        recency=('purchase_date', lambda date: (snapshot_date - date.max()).days),
        frequency=('order_id', 'nunique'),
        monetary=('amount', 'sum')
    ).reset_index()

    kmeans = KMeans(n_clusters=4, random_state=42, n_init='auto')
    rfm['cluster'] = kmeans.fit_predict(rfm[['recency', 'frequency', 'monetary']])
    
    cluster_centers = kmeans.cluster_centers_
    ordered_clusters = sorted(range(len(cluster_centers)), key=lambda k: cluster_centers[k][2], reverse=True)
    cluster_map = {ordered_clusters[0]: 'Best Customers', ordered_clusters[1]: 'Loyal Customers', ordered_clusters[2]: 'Potential Loyalists', ordered_clusters[3]: 'At Risk'}
    rfm['segment'] = rfm['cluster'].map(cluster_map)
    return rfm

def forecast_sales(df: pd.DataFrame, periods: int = 30) -> pd.DataFrame:
    """Generate sales forecast using an ARIMA model from statsmodels."""
    if df.empty or len(df) < 10: # ARIMA needs more data points
        return pd.DataFrame(columns=['ds', 'yhat', 'yhat_lower', 'yhat_upper'])

    sales_data = df.set_index('purchase_date').resample('D')['amount'].sum().fillna(0)
    
    # Fit ARIMA model
    model = ARIMA(sales_data, order=(5,1,0)) # (p,d,q) order
    model_fit = model.fit()
    
    # Make forecast
    forecast = model_fit.get_forecast(steps=periods)
    forecast_df = forecast.summary_frame()
    
    forecast_df.reset_index(inplace=True)
    forecast_df.columns = ['ds', 'yhat', 'se', 'yhat_lower', 'yhat_upper']
    
    return forecast_df[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]


# --- Main App ---
st.title("📊 Interactive E-commerce Sales Dashboard")

# Load data
df_full = load_and_clean_data(CSV_FILE_PATH)

if df_full is not None:
    # --- Sidebar Filters ---
    st.sidebar.header("Dashboard Filters")
    
    min_date = df_full['purchase_date'].min().date()
    max_date = df_full['purchase_date'].max().date()
    start_date, end_date = st.sidebar.date_input(
        "Select Date Range",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    all_categories = df_full['product_category'].unique()
    selected_categories = st.sidebar.multiselect(
        "Select Product Categories",
        all_categories,
        default=all_categories
    )

    df_filtered = df_full[
        (df_full['purchase_date'].dt.date >= start_date) &
        (df_full['purchase_date'].dt.date <= end_date) &
        (df_full['product_category'].isin(selected_categories))
    ]

    if df_filtered.empty:
        st.warning("No data available for the selected filters. Please adjust your selection.")
    else:
        rfm_data = perform_rfm_analysis(df_filtered)
        forecast_data = forecast_sales(df_filtered, periods=90)

        total_revenue = df_filtered['amount'].sum()
        total_orders = df_filtered['order_id'].nunique()
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        unique_customers = df_filtered['customer_id'].nunique()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Revenue", f"${total_revenue:,.2f}")
        col2.metric("Total Orders", f"{total_orders:,}")
        col3.metric("Average Order Value", f"${avg_order_value:,.2f}")
        col4.metric("Unique Customers", f"{unique_customers:,}")

        st.markdown("---")

        # --- THIS IS THE CORRECTED PART ---
        # The 'specs' parameter now correctly defines which subplots are pie charts
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Daily Revenue Trend', 'Customer Segments (RFM)',
                'Top Product Categories by Revenue', 'Sales Forecast (90 Days)',
                'Sales by Day of Week', 'Gender Distribution'
            ),
            vertical_spacing=0.15,
            specs=[
                [{"type": "xy"}, {"type": "pie"}],
                [{"type": "xy"}, {"type": "xy"}],
                [{"type": "xy"}, {"type": "pie"}]
            ]
        )

        # Daily Revenue
        daily_revenue = df_filtered.groupby(df_filtered['purchase_date'].dt.date)['amount'].sum().reset_index()
        fig.add_trace(go.Scatter(x=daily_revenue['purchase_date'], y=daily_revenue['amount'], mode='lines', name='Daily Revenue'), row=1, col=1)

        # Customer Segments
        segment_data = rfm_data['segment'].value_counts()
        fig.add_trace(go.Pie(labels=segment_data.index, values=segment_data.values, name='Segments'), row=1, col=2)

        # Top Product Categories
        top_categories = df_filtered.groupby('product_category')['amount'].sum().nlargest(5).reset_index()
        fig.add_trace(go.Bar(x=top_categories['product_category'], y=top_categories['amount'], name='Revenue'), row=2, col=1)

        # Sales Forecast
        fig.add_trace(go.Scatter(x=forecast_data['ds'], y=forecast_data['yhat'], mode='lines', name='Forecast'), row=2, col=2)
        fig.add_trace(go.Scatter(x=forecast_data['ds'], y=forecast_data['yhat_upper'], fill='tonexty', mode='none', name='Upper Bound', line_color='lightgrey'), row=2, col=2)
        fig.add_trace(go.Scatter(x=forecast_data['ds'], y=forecast_data['yhat_lower'], fill='tonexty', mode='none', name='Lower Bound', line_color='lightgrey'), row=2, col=2)

        # Sales by Day of Week
        df_filtered['day_of_week'] = df_filtered['purchase_date'].dt.day_name()
        day_of_week_data = df_filtered.groupby('day_of_week')['amount'].sum().reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']).reset_index()
        fig.add_trace(go.Bar(x=day_of_week_data['day_of_week'], y=day_of_week_data['amount'], name='Revenue by Day'), row=3, col=1)

        # Gender Distribution
        gender_data = df_filtered['gender'].value_counts()
        fig.add_trace(go.Pie(labels=gender_data.index, values=gender_data.values, name='Gender'), row=3, col=2)
        
        fig.update_layout(height=1000, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Filtered Sales Data")
        st.dataframe(df_filtered.head(100))

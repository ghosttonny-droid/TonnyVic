import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Set page configuration
st.set_page_config(page_title="Error Analysis Dashboard", layout="wide")

st.title("Error Analysis Dashboard")

# Default file path
# Try to find the file in Downloads. If running locally in the folder, it might differ.
# We will use the absolute path provided in the context.
FILE_PATH = "c:/Users/mm16010130/Downloads/tickets_20260108_221513.csv"

# Load data
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None
    
    # Try reading with different encodings
    try:
        df = pd.read_csv(file_path)
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='latin1')
    
    # Process dates, handling potential errors
    df['fail_time'] = pd.to_datetime(df['fail_time'], errors='coerce')
    return df

df = load_data(FILE_PATH)

if df is None:
    st.error(f"File not found at: {FILE_PATH}. Please make sure the CSV file exists.")
    st.stop()

# Helper column for analysis
# Prefer 'error_message_nor' if available, else 'error_message'
if 'error_message_nor' in df.columns:
    df['Analyzed_Error'] = df['error_message_nor'].fillna(df['error_message'])
else:
    df['Analyzed_Error'] = df['error_message']

# Sidebar Filters
st.sidebar.header("Filters")

# Model Filter
if 'model' in df.columns:
    models = df['model'].unique().tolist()
    selected_models = st.sidebar.multiselect("Select Model", options=models, default=models)
else:
    selected_models = []

# Stage Filter
if 'stage' in df.columns:
    stages = df['stage'].unique().tolist()
    selected_stages = st.sidebar.multiselect("Select Stage", options=stages, default=stages)
else:
    selected_stages = []

# Result Filter
if 'result' in df.columns:
    results = df['result'].unique().tolist()
    selected_results = st.sidebar.multiselect("Select Result", options=results, default=results)
else:
    selected_results = []

# Time Range Filter
if 'fail_time' in df.columns and not df['fail_time'].isnull().all():
    min_date = df['fail_time'].min().date()
    max_date = df['fail_time'].max().date()
    
    if min_date and max_date:
        start_date, end_date = st.sidebar.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
else:
    start_date, end_date = None, None

# Apply Filters
df_filtered = df.copy()

if selected_models:
    df_filtered = df_filtered[df_filtered['model'].isin(selected_models)]
if selected_stages:
    df_filtered = df_filtered[df_filtered['stage'].isin(selected_stages)]
if selected_results:
    df_filtered = df_filtered[df_filtered['result'].isin(selected_results)]

if start_date and end_date:
     df_filtered = df_filtered[
        (df_filtered['fail_time'].dt.date >= start_date) & 
        (df_filtered['fail_time'].dt.date <= end_date)
    ]

# Main Dashboard
col1, col2 = st.columns(2)

with col1:
    st.header("Top Errors")
    if 'Analyzed_Error' in df_filtered.columns:
        top_errors = df_filtered['Analyzed_Error'].value_counts().head(10).reset_index()
        top_errors.columns = ['Error Message', 'Count']
        fig_errors = px.bar(top_errors, x='Count', y='Error Message', orientation='h', title="Top 10 Frequent Errors")
        fig_errors.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_errors, use_container_width=True)
    else:
        st.warning("No error message column found.")

with col2:
    st.header("Errors Over Time")
    if start_date and end_date:
        # Group by day
        errors_over_time = df_filtered.groupby(df_filtered['fail_time'].dt.date).size().reset_index(name='Count')
        errors_over_time.columns = ['Date', 'Count']
        fig_time = px.line(errors_over_time, x='Date', y='Count', title="Daily Error Frequency")
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No timeline data available (fail_time is missing or invalid).")

st.header("Result Distribution")
if 'result' in df_filtered.columns:
    result_counts = df_filtered['result'].value_counts().reset_index()
    result_counts.columns = ['Result', 'Count']
    fig_res = px.pie(result_counts, values='Count', names='Result', title="Result Distribution")
    st.plotly_chart(fig_res, use_container_width=True)

st.header("Raw Data")
st.dataframe(df_filtered)

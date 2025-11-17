import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Sensor Analysis Tool", layout="wide")
st.title("🔧 Sensor Data Analysis Tool")

# Sidebar for user input
st.sidebar.header("Configuration")

# File upload
uploaded_file = st.sidebar.file_uploader("Upload CSV file", type="csv")

if uploaded_file is None:
    st.info("👈 Please upload a CSV file to get started")
    st.stop()

# Load data
try:
    df = pd.read_csv(uploaded_file)
    st.success("✅ File uploaded successfully")
except Exception as e:
    st.error(f"❌ Error loading file: {e}")
    st.stop()

# Display data info
st.subheader("📊 Data Overview")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Rows", len(df))
with col2:
    st.metric("Columns", len(df.columns))
with col3:
    st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")

# Show column names
st.write("**Available columns:**")
st.write(df.columns.tolist())

# Display first few rows
st.subheader("📋 Data Preview")
st.dataframe(df.head(10), use_container_width=True)

# Basic statistics
st.subheader("📈 Basic Statistics")
st.dataframe(df.describe(), use_container_width=True)

# Filter by job number (if Job # column exists)
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

if numeric_cols:
    st.subheader("🔍 Data Analysis")

    # Select column to analyze
    selected_col = st.selectbox("Select column to analyze:", numeric_cols)

    if selected_col:
        # Create visualization
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=df[selected_col], nbinsx=30, name=selected_col))
        fig.update_layout(
            title=f"Distribution of {selected_col}",
            xaxis_title=selected_col,
            yaxis_title="Frequency",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Mean", f"{df[selected_col].mean():.2f}")
        with col2:
            st.metric("Median", f"{df[selected_col].median():.2f}")
        with col3:
            st.metric("Std Dev", f"{df[selected_col].std():.2f}")
        with col4:
            st.metric("Range", f"{df[selected_col].max() - df[selected_col].min():.2f}")

# Download processed data
st.subheader("💾 Export Data")
csv = df.to_csv(index=False)
st.download_button(
    label="Download CSV",
    data=csv,
    file_name="sensor_data_analysis.csv",
    mime="text/csv"
)

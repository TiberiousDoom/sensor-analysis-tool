import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Sensor Data Analysis Tool",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define threshold sets
THRESHOLDS = {
    'Standard': {
        'min_120s': 1.50,
        'max_120s': 4.9,
        'min_pct_change': -6.00,
        'max_pct_change': 30.00,
        'max_std_dev': 0.3
    },
    'High Range': {
        'min_120s': 0.55,
        'max_120s': 1.0,
        'min_pct_change': -10.00,
        'max_pct_change': 75.00,
        'max_std_dev': 0.5
    }
}

TIME_POINTS = ['0', '5', '15', '30', '60', '90', '120']
STATUS_PRIORITY = {'FL': 1, 'FH': 2, 'OT-': 3, 'TT': 4, 'OT+': 5, 'DM': 6, 'PASS': 7}

# Initialize session state
if 'df_global' not in st.session_state:
    st.session_state.df_global = pd.DataFrame()
if 'last_results' not in st.session_state:
    st.session_state.last_results = None

def load_data_from_csv(uploaded_file):
    """Load sensor data from uploaded CSV file."""
    try:
        df = pd.read_csv(uploaded_file)
        
        # Convert time point columns to numeric
        for col in TIME_POINTS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Standardize job column name
        job_col_variants = ['Job #', 'Job#', 'Job', 'job', 'job_number', 'JobNumber', 'Job Number']
        for variant in job_col_variants:
            if variant in df.columns:
                df['Job #'] = df[variant].astype(str)
                break
        
        # Standardize serial number column name
        serial_col_variants = ['Serial Number', 'Serial#', 'Serial', 'SerialNumber', 'serial_number', 'Serial #']
        for variant in serial_col_variants:
            if variant in df.columns:
                df['Serial Number'] = df[variant].astype(str)
                break
        
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame()

def calculate_metrics(df):
    """Calculate key metrics for sensor readings."""
    metrics = df.copy()
    
    if '0' in df.columns and '90' in df.columns and '120' in df.columns:
        denominator = df['90'] - df['0']
        denominator = denominator.replace(0, np.nan)
        metrics['pct_change_90_120'] = ((df['120'] - df['90']) / denominator * 100).replace([np.inf, -np.inf], np.nan)
    
    return metrics

def determine_pass_fail(df, threshold_set='Standard'):
    """Determine Pass/Fail status based on thresholds."""
    thresholds = THRESHOLDS[threshold_set]
    results = []
    
    for serial in df['Serial Number'].unique():
        serial_data = df[df['Serial Number'] == serial].copy()
        readings_120 = serial_data['120'].dropna()
        
        if len(readings_120) == 0:
            continue
        
        std_dev_120 = readings_120.std() if len(readings_120) > 1 else 0
        
        serial_row = {
            'Serial Number': serial,
            'Channel': serial_data.iloc[0].get('Channel', ''),
        }
        
        all_failure_codes = []
        
        for test_idx, (idx, row) in enumerate(serial_data.iterrows(), 1):
            test_prefix = f'T{test_idx}'
            
            serial_row[f'0s({test_prefix})'] = row.get('0', np.nan)
            serial_row[f'90s({test_prefix})'] = row.get('90', np.nan)
            serial_row[f'120s({test_prefix})'] = row.get('120', np.nan)
            
            pct_change = row.get('pct_change_90_120', np.nan)
            if pd.notna(pct_change):
                serial_row[f'%Chg({test_prefix})'] = f"{pct_change:.1f}%"
            else:
                serial_row[f'%Chg({test_prefix})'] = np.nan
            
            failure_codes = []
            reading_120 = row['120']
            
            if pd.notna(reading_120):
                if reading_120 < thresholds['min_120s']:
                    failure_codes.append('FL')
                if reading_120 > thresholds['max_120s']:
                    failure_codes.append('FH')
            else:
                failure_codes.append('DM')
            
            if pd.notna(pct_change):
                if pct_change < thresholds['min_pct_change']:
                    failure_codes.append('OT-')
                if pct_change > thresholds['max_pct_change']:
                    failure_codes.append('OT+')
            
            test_status = 'PASS' if len(failure_codes) == 0 else ','.join(sorted(set(failure_codes)))
            serial_row[f'Status({test_prefix})'] = test_status
            all_failure_codes.extend(failure_codes)
        
        if std_dev_120 > thresholds['max_std_dev']:
            all_failure_codes.append('TT')
        
        if len(all_failure_codes) == 0:
            status = 'PASS'
        else:
            unique_failures = list(set(all_failure_codes))
            unique_failures.sort(key=lambda x: STATUS_PRIORITY.get(x, 99))
            status = unique_failures[0]
        
        serial_row['Pass/Fail'] = status
        serial_row['120s(St.Dev.)'] = std_dev_120
        results.append(serial_row)
    
    results_df = pd.DataFrame(results)
    base_cols = ['Serial Number', 'Channel', 'Pass/Fail', '120s(St.Dev.)']
    test_cols = [col for col in results_df.columns if col not in base_cols]
    column_order = base_cols + test_cols
    
    return results_df[column_order]

def apply_filters(results, filters):
    """Apply display filters based on selections."""
    if results is None or len(results) == 0:
        return results
    
    filtered = results.copy()
    keep_indices = []
    
    for idx, row in filtered.iterrows():
        status = row['Pass/Fail']
        
        if status == 'PASS':
            if filters['show_passed']:
                keep_indices.append(idx)
        else:
            if filters['show_failed']:
                should_show = False
                if filters['filter_fl'] and 'FL' in status:
                    should_show = True
                if filters['filter_fh'] and 'FH' in status:
                    should_show = True
                if filters['filter_ot_minus'] and 'OT-' in status:
                    should_show = True
                if filters['filter_oot'] and 'OT+' in status:
                    should_show = True
                if filters['filter_tt'] and 'TT' in status:
                    should_show = True
                if filters['filter_dm'] and 'DM' in status:
                    should_show = True
                
                if should_show:
                    keep_indices.append(idx)
    
    return filtered.loc[keep_indices] if keep_indices else pd.DataFrame()

def get_job_data(df, job_number):
    """Get job data with flexible matching."""
    job_number_str = str(job_number).strip()
    
    # Try various matching strategies
    job_data = df[df['Job #'] == job_number_str].copy()
    
    if len(job_data) == 0:
        job_data = df[df['Job #'].str.strip() == job_number_str].copy()
    
    if len(job_data) == 0:
        job_data = df[df['Job #'].str.strip().str.startswith(job_number_str)].copy()
    
    if len(job_data) == 0:
        job_data = df[df['Job #'].str.lower().str.strip().str.startswith(job_number_str.lower())].copy()
    
    return job_data if len(job_data) > 0 else None

def analyze_job(df, job_number, threshold_set='Standard'):
    """Analyze data for a specific job number."""
    if len(df) == 0:
        st.warning("No data loaded. Please upload a CSV file first.")
        return None
    
    job_data = get_job_data(df, job_number)
    
    if job_data is None:
        st.error(f"No data found for Job # {job_number}")
        return None
    
    job_data = calculate_metrics(job_data)
    results = determine_pass_fail(job_data, threshold_set)
    
    return results

def create_job_plot(df, job_number, threshold_set='Standard'):
    """Create interactive Plotly plot for job data."""
    job_data = get_job_data(df, job_number)
    
    if job_data is None:
        return None
    
    # Aggregate data
    agg_data = []
    for time_point in TIME_POINTS:
        if time_point in job_data.columns:
            readings = job_data[time_point].dropna()
            if len(readings) > 0:
                agg_data.append({
                    'time': float(time_point),
                    'mean': readings.mean(),
                    'std': readings.std(),
                    'p5': readings.quantile(0.05),
                    'p95': readings.quantile(0.95)
                })
    
    agg_df = pd.DataFrame(agg_data)
    thresholds = THRESHOLDS[threshold_set]
    
    # Create Plotly figure
    fig = go.Figure()
    
    # Add threshold lines
    fig.add_hline(y=thresholds['min_120s'], line_dash="dot", line_color="red", 
                  annotation_text=f"Min Threshold ({thresholds['min_120s']}V)")
    fig.add_hline(y=thresholds['max_120s'], line_dash="dot", line_color="red",
                  annotation_text=f"Max Threshold ({thresholds['max_120s']}V)")
    
    # Add 5th-95th percentile band
    fig.add_trace(go.Scatter(
        x=agg_df['time'].tolist() + agg_df['time'].tolist()[::-1],
        y=agg_df['p95'].tolist() + agg_df['p5'].tolist()[::-1],
        fill='toself',
        fillcolor='rgba(0,255,0,0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        name='5th-95th Percentile'
    ))
    
    # Add std dev band
    fig.add_trace(go.Scatter(
        x=agg_df['time'].tolist() + agg_df['time'].tolist()[::-1],
        y=(agg_df['mean'] + agg_df['std']).tolist() + (agg_df['mean'] - agg_df['std']).tolist()[::-1],
        fill='toself',
        fillcolor='rgba(0,0,255,0.3)',
        line=dict(color='rgba(255,255,255,0)'),
        name='±1 Std Dev'
    ))
    
    # Add mean line
    fig.add_trace(go.Scatter(
        x=agg_df['time'],
        y=agg_df['mean'],
        mode='lines+markers',
        name='Overall Mean',
        line=dict(color='blue', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title=f'Sensor Readings Over Time - Job {job_number} ({threshold_set})',
        xaxis_title='Time (seconds)',
        yaxis_title='Sensor Reading (V)',
        yaxis=dict(range=[0, 5]),
        hovermode='x unified',
        height=500
    )
    
    return fig

def style_dataframe(df):
    """Apply styling to dataframe for display."""
    def color_status(val):
        if val == 'PASS':
            return 'background-color: #d4edda; color: #155724; font-weight: bold'
        elif val in ['OT-', 'TT', 'OT+']:
            return 'background-color: #d1ecf1; color: #0c5460; font-weight: bold'
        elif val in ['FL', 'FH']:
            return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
        elif val == 'DM':
            return 'background-color: #e9ecef; color: #495057; font-weight: bold'
        return ''
    
    # Format numeric columns
    formatted_df = df.copy()
    for col in formatted_df.columns:
        if col.startswith(('0s(', '90s(', '120s(')):
            formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else '')
        elif '120s(St.Dev.)' == col:
            formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.3f}" if pd.notna(x) else '')
    
    return formatted_df

# Main App
st.title("🔧 Sensor Data Analysis Tool")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📁 Data Management")
    
    uploaded_file = st.file_uploader("Upload CSV File", type=['csv'])
    
    if uploaded_file is not None:
        if st.button("Load Data", type="primary"):
            with st.spinner("Loading data..."):
                st.session_state.df_global = load_data_from_csv(uploaded_file)
                if len(st.session_state.df_global) > 0:
                    st.success(f"✓ Loaded {len(st.session_state.df_global)} records!")
    
    st.markdown("---")
    st.header("⚙️ Analysis Settings")
    
    threshold_set = st.radio(
        "Threshold Set",
        options=['Standard', 'High Range'],
        help="Select the threshold set for pass/fail criteria"
    )
    
    st.markdown("---")
    st.header("🔍 Display Filters")
    
    show_passed = st.checkbox("Show Passed", value=True)
    show_failed = st.checkbox("Show Failed", value=True)
    
    st.markdown("**Failure Types:**")
    filter_fl = st.checkbox("Show FL (Failed Low)", value=True)
    filter_fh = st.checkbox("Show FH (Failed High)", value=True)
    filter_ot_minus = st.checkbox("Show OT- (Out of Tol. Neg)", value=True)
    filter_oot = st.checkbox("Show OT+ (Out of Tol. Pos)", value=True)
    filter_tt = st.checkbox("Show TT (Test-to-Test)", value=True)
    filter_dm = st.checkbox("Show DM (Data Missing)", value=True)

# Main content
if len(st.session_state.df_global) == 0:
    st.info("👆 Please upload a CSV file to begin analysis")
    st.markdown("""
    ### Getting Started
    1. Upload your sensor data CSV file using the sidebar
    2. Click "Load Data" to import
    3. Enter a Job Number below to analyze
    4. View results and export as needed
    """)
else:
    # Display data summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records", len(st.session_state.df_global))
    with col2:
        unique_jobs = st.session_state.df_global['Job #'].nunique()
        st.metric("Unique Jobs", unique_jobs)
    with col3:
        unique_sensors = st.session_state.df_global['Serial Number'].nunique()
        st.metric("Unique Sensors", unique_sensors)
    
    st.markdown("---")
    
    # Analysis inputs
    tab1, tab2 = st.tabs(["📊 Job Analysis", "🔍 Sensor Analysis"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            job_number = st.text_input(
                "Job Number",
                placeholder="Enter Job Number (e.g., 258)",
                help="Enter the job number to analyze"
            )
        
        with col2:
            analyze_button = st.button("🚀 Analyze Job", type="primary", use_container_width=True)
        
        if analyze_button and job_number:
            with st.spinner("Analyzing job data..."):
                # Analyze job
                results = analyze_job(st.session_state.df_global, job_number, threshold_set)
                
                if results is not None:
                    st.session_state.last_results = results
                    
                    # Calculate statistics
                    total_sensors = len(results)
                    passed_sensors = len(results[results['Pass/Fail'].isin(['PASS', 'OT-', 'TT', 'OT+'])])
                    failed_sensors = len(results[results['Pass/Fail'].isin(['FL', 'FH'])])
                    dm_sensors = len(results[results['Pass/Fail'] == 'DM'])
                    counted_sensors = passed_sensors + failed_sensors
                    
                    pass_rate = (passed_sensors / counted_sensors * 100) if counted_sensors > 0 else 0
                    fail_rate = (failed_sensors / counted_sensors * 100) if counted_sensors > 0 else 0
                    
                    # Display summary
                    st.markdown("### 📈 Summary Statistics")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Sensors", total_sensors)
                    with col2:
                        st.metric("Passed", f"{passed_sensors} ({pass_rate:.1f}%)")
                    with col3:
                        st.metric("Failed", f"{failed_sensors} ({fail_rate:.1f}%)")
                    with col4:
                        st.metric("Data Missing", f"{dm_sensors} (excluded)")
                    
                    # Status code legend
                    with st.expander("📖 Status Code Legend"):
                        thresholds = THRESHOLDS[threshold_set]
                        st.markdown(f"""
                        - **FL**: Failed Low (< {thresholds['min_120s']}V)
                        - **FH**: Failed High (> {thresholds['max_120s']}V)
                        - **OT-**: Out of Tolerance Negative (< {thresholds['min_pct_change']}%) - PASS
                        - **TT**: Test-to-Test (> {thresholds['max_std_dev']}V) - PASS
                        - **OT+**: Out of Tolerance Positive (> {thresholds['max_pct_change']}%) - PASS
                        - **DM**: Data Missing (not counted)
                        - **PASS**: All criteria met
                        """)
                    
                    # Plot
                    st.markdown("### 📊 Sensor Readings Plot")
                    fig = create_job_plot(st.session_state.df_global, job_number, threshold_set)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Apply filters
                    filters = {
                        'show_passed': show_passed,
                        'show_failed': show_failed,
                        'filter_fl': filter_fl,
                        'filter_fh': filter_fh,
                        'filter_ot_minus': filter_ot_minus,
                        'filter_oot': filter_oot,
                        'filter_tt': filter_tt,
                        'filter_dm': filter_dm
                    }
                    
                    filtered_results = apply_filters(results, filters)
                    
                    # Display results table
                    st.markdown("### 📋 Detailed Results")
                    if len(filtered_results) < len(results):
                        st.info(f"📊 Displaying {len(filtered_results)} of {len(results)} sensors (filters applied)")
                    
                    styled_df = style_dataframe(filtered_results)
                    st.dataframe(styled_df, use_container_width=True, height=400)
                    
                    # Export button
                    if st.button("💾 Export Results to CSV"):
                        csv = results.to_csv(index=False)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"sensor_analysis_job_{job_number}_{timestamp}.csv"
                        
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv,
                            file_name=filename,
                            mime="text/csv"
                        )
    
    with tab2:
        serial_number = st.text_input(
            "Serial Number",
            placeholder="Enter Serial Number",
            help="Enter the serial number to view individual sensor data"
        )
        
        if st.button("🔍 View Sensor", type="primary") and serial_number:
            sensor_data = st.session_state.df_global[
                st.session_state.df_global['Serial Number'] == serial_number
            ]
            
            if len(sensor_data) > 0:
                st.markdown(f"### Sensor: {serial_number}")
                
                # Create individual sensor plot
                fig = go.Figure()
                
                for idx, row in sensor_data.iterrows():
                    time_vals = []
                    reading_vals = []
                    
                    for time_point in TIME_POINTS:
                        if time_point in row.index and pd.notna(row[time_point]):
                            time_vals.append(float(time_point))
                            reading_vals.append(row[time_point])
                    
                    if time_vals:
                        test_label = f"Test #{row.get('Test #', 'Unknown')}"
                        fig.add_trace(go.Scatter(
                            x=time_vals,
                            y=reading_vals,
                            mode='lines+markers',
                            name=test_label,
                            line=dict(width=2),
                            marker=dict(size=6)
                        ))
                
                fig.update_layout(
                    title=f'Sensor Readings - Serial Number {serial_number}',
                    xaxis_title='Time (seconds)',
                    yaxis_title='Sensor Reading (V)',
                    yaxis=dict(range=[0, 5]),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("### Raw Data")
                st.dataframe(sensor_data, use_container_width=True)
            else:
                st.error(f"No data found for Serial Number: {serial_number}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Sensor Data Analysis Tool v2.0 | Powered by Streamlit</p>
</div>
""", unsafe_allow_html=True)
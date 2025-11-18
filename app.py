import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
from datetime import datetime

# Page configuration with custom theme
st.set_page_config(
    page_title="Sensor Analysis Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Sensor Data Analysis Tool v2.0"
    }
)

# Custom CSS for modern UI
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background: #f8f9fa;
    }
    
    /* Header gradient */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    /* Metric cards */
    div[data-testid="metric-container"] {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border-left: 4px solid #667eea;
    }
    
    /* Status pills */
    .status-pill {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin: 2px;
    }
    
    .status-pass {
        background: #d4f4dd;
        color: #1e7e34;
    }
    
    .status-fail {
        background: #ffd6d6;
        color: #bd2130;
    }
    
    .status-warning {
        background: #fff3cd;
        color: #856404;
    }
    
    /* Improved button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.5rem;
        border-radius: 25px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar improvements */
    section[data-testid="stSidebar"] {
        background: white;
        box-shadow: 2px 0 10px rgba(0,0,0,0.05);
    }
    
    /* Success/Error messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 10px;
        padding: 1rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0px 24px;
        background-color: white;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
    }
    
    /* Data table improvements */
    .dataframe {
        font-size: 14px;
    }
    
    .dataframe tbody tr:hover {
        background-color: #f0f7ff !important;
    }
    
    /* Legend box */
    .legend-box {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        margin: 1rem 0;
    }
    
    /* Quick stats container */
    .quick-stats {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 2px 15px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

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

# Time points for analysis
TIME_POINTS = ['0', '5', '15', '30', '60', '90', '120']

# Status color mapping for visual consistency
STATUS_COLORS = {
    'PASS': '#28a745',
    'FL': '#dc3545',
    'FH': '#dc3545',
    'OT-': '#ffc107',
    'TT': '#ffc107',
    'OT+': '#ffc107',
    'DM': '#6c757d'
}

@st.cache_data
def load_data_from_db(db_path='sensor_data.db'):
    """Load sensor data from SQLite database with robust numeric conversion."""
    try:
        conn = sqlite3.connect(db_path)
        query = "SELECT * FROM sensor_readings"
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Convert time point columns to numeric
        for col in TIME_POINTS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Ensure Job # and Serial Number are strings
        if 'Job #' in df.columns:
            df['Job #'] = df['Job #'].astype(str)
        if 'Serial Number' in df.columns:
            df['Serial Number'] = df['Serial Number'].astype(str)

        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def load_data_from_csv(file):
    """Load sensor data from uploaded CSV file."""
    try:
        df = pd.read_csv(file)

        # Convert time point columns to numeric
        for col in TIME_POINTS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Ensure Job # and Serial Number are strings
        if 'Job #' in df.columns:
            df['Job #'] = df['Job #'].astype(str)
        if 'Serial Number' in df.columns:
            df['Serial Number'] = df['Serial Number'].astype(str)

        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame()

def calculate_metrics(df):
    """Calculate key metrics for sensor readings."""
    metrics = df.copy()

    # Calculate percentage change between 90s and 120s
    if '90' in df.columns and '120' in df.columns:
        metrics['pct_change_90_120'] = ((df['120'] - df['90']) / df['90'] * 100).replace([np.inf, -np.inf], np.nan)

    return metrics

def determine_pass_fail(df, threshold_set='Standard'):
    """Determine Pass/Fail status based on thresholds."""
    thresholds = THRESHOLDS[threshold_set]
    results = []

    # Define priority order for status codes
    status_priority = {'FL': 1, 'FH': 2, 'OT-': 3, 'TT': 4, 'OT+': 5, 'DM': 6, 'PASS': 7}

    for serial in df['Serial Number'].unique():
        serial_data = df[df['Serial Number'] == serial].copy()

        # Get 120s readings for this serial across all tests
        readings_120 = serial_data['120'].dropna()

        if len(readings_120) == 0:
            continue

        # Calculate standard deviation across tests
        std_dev_120 = readings_120.std() if len(readings_120) > 1 else 0

        # Start building the row with base columns
        serial_row = {
            'Serial Number': serial,
            'Channel': serial_data.iloc[0].get('Channel', ''),
        }

        # Collect all failure codes across tests
        all_failure_codes = []

        # Add data for each test
        for test_idx, (idx, row) in enumerate(serial_data.iterrows(), 1):
            test_prefix = f'T{test_idx}'

            # Add readings for this test (1 decimal place)
            serial_row[f'0s({test_prefix})'] = row.get('0', np.nan)
            serial_row[f'90s({test_prefix})'] = row.get('90', np.nan)
            serial_row[f'120s({test_prefix})'] = row.get('120', np.nan)

            # Format percentage change with % symbol (1 decimal place)
            pct_change = row.get('pct_change_90_120', np.nan)
            if pd.notna(pct_change):
                serial_row[f'%Chg({test_prefix})'] = f"{pct_change:.1f}%"
            else:
                serial_row[f'%Chg({test_prefix})'] = np.nan

            # Check failures for this test
            failure_codes = []

            # Check 120s reading range
            reading_120 = row['120']
            if pd.notna(reading_120):
                if reading_120 < thresholds['min_120s']:
                    failure_codes.append('FL')
                if reading_120 > thresholds['max_120s']:
                    failure_codes.append('FH')
            else:
                failure_codes.append('DM')

            # Check percentage change
            if pd.notna(pct_change):
                if pct_change < thresholds['min_pct_change']:
                    failure_codes.append('OT-')
                if pct_change > thresholds['max_pct_change']:
                    failure_codes.append('OT+')

            # Individual test status (without std dev check)
            test_status = 'PASS' if len(failure_codes) == 0 else ','.join(sorted(set(failure_codes)))
            serial_row[f'Status({test_prefix})'] = test_status

            all_failure_codes.extend(failure_codes)

        # Check standard deviation across tests
        if std_dev_120 > thresholds['max_std_dev']:
            all_failure_codes.append('TT')

        # Determine overall status with priority
        if len(all_failure_codes) == 0:
            status = 'PASS'
        else:
            unique_failures = list(set(all_failure_codes))
            unique_failures.sort(key=lambda x: status_priority.get(x, 99))
            status = unique_failures[0]

        # Add overall columns
        serial_row['Pass/Fail'] = status
        serial_row['120s(St.Dev.)'] = std_dev_120

        results.append(serial_row)

    # Create DataFrame and reorder columns
    results_df = pd.DataFrame(results)

    # Build desired column order
    base_cols = ['Serial Number', 'Channel', 'Pass/Fail', '120s(St.Dev.)']
    test_cols = [col for col in results_df.columns if col not in base_cols]
    column_order = base_cols + test_cols
    results_df = results_df[column_order]

    return results_df

def get_job_data(df, job_number):
    """Get data for a specific job number or all jobs starting with that number."""
    job_number_str = str(job_number).strip()

    # Try exact match first
    job_data = df[df['Job #'] == job_number_str].copy()

    # If no match, try stripping whitespace
    if len(job_data) == 0:
        job_data = df[df['Job #'].str.strip() == job_number_str].copy()

    # If still no match, try matching jobs that start with the number
    if len(job_data) == 0:
        job_data = df[df['Job #'].str.strip().str.startswith(job_number_str)].copy()

    # If still no match, try case-insensitive
    if len(job_data) == 0:
        job_data = df[df['Job #'].str.lower().str.strip().str.startswith(job_number_str.lower())].copy()

    return job_data

def create_status_badge(status):
    """Create HTML for a status badge with appropriate color."""
    if status == 'PASS':
        return f'<span class="status-pill status-pass">{status}</span>'
    elif status in ['FL', 'FH']:
        return f'<span class="status-pill status-fail">{status}</span>'
    elif status in ['OT-', 'TT', 'OT+']:
        return f'<span class="status-pill status-warning">{status}</span>'
    else:
        return f'<span class="status-pill" style="background: #e9ecef; color: #6c757d;">{status}</span>'

def create_enhanced_plot(df, job_number, threshold_set='Standard'):
    """Generate enhanced visualization for a specific job."""
    job_data = get_job_data(df, job_number)
    
    if len(job_data) == 0:
        return None
    
    matched_jobs = sorted(job_data['Job #'].unique())
    thresholds = THRESHOLDS[threshold_set]
    
    # Aggregate data
    time_data = []
    for time_point in TIME_POINTS:
        if time_point in job_data.columns:
            readings = job_data[time_point].dropna()
            if len(readings) > 0:
                time_data.append({
                    'time': float(time_point),
                    'mean': readings.mean(),
                    'std': readings.std(),
                    'p5': readings.quantile(0.05),
                    'p95': readings.quantile(0.95),
                    'p25': readings.quantile(0.25),
                    'p75': readings.quantile(0.75)
                })
    
    if not time_data:
        return None
    
    df_plot = pd.DataFrame(time_data)
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Main trend plot (left)
    ax1.fill_between(df_plot['time'], df_plot['p5'], df_plot['p95'],
                     alpha=0.15, color='#667eea', label='5th-95th Percentile')
    ax1.fill_between(df_plot['time'], df_plot['p25'], df_plot['p75'],
                     alpha=0.25, color='#764ba2', label='25th-75th Percentile')
    ax1.fill_between(df_plot['time'], df_plot['mean'] - df_plot['std'],
                     df_plot['mean'] + df_plot['std'],
                     alpha=0.3, color='#667eea', label='±1 Std Dev')
    
    # Mean line
    ax1.plot(df_plot['time'], df_plot['mean'], 'o-', color='#764ba2', 
             linewidth=3, markersize=8, label='Mean', zorder=10)
    
    # Add threshold lines
    ax1.axhline(y=thresholds['min_120s'], color='red', linestyle='--', 
                alpha=0.5, label=f'Min Threshold ({thresholds["min_120s"]}V)')
    ax1.axhline(y=thresholds['max_120s'], color='red', linestyle='--', 
                alpha=0.5, label=f'Max Threshold ({thresholds["max_120s"]}V)')
    
    # Formatting
    ax1.set_title('Sensor Readings Over Time', fontsize=14, fontweight='bold', pad=20)
    ax1.set_xlabel('Time (seconds)', fontsize=12)
    ax1.set_ylabel('Voltage (V)', fontsize=12)
    ax1.set_ylim(0, 5)
    ax1.set_xlim(-5, 125)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend(loc='best', framealpha=0.9)
    
    # Box plot for 120s readings (right)
    if '120' in job_data.columns:
        readings_120 = job_data['120'].dropna()
        bp = ax2.boxplot([readings_120], vert=True, patch_artist=True,
                         widths=0.6, showmeans=True, meanline=True)
        
        # Style the boxplot
        for patch in bp['boxes']:
            patch.set_facecolor('#667eea')
            patch.set_alpha(0.7)
        
        # Add threshold regions
        ax2.axhspan(0, thresholds['min_120s'], alpha=0.1, color='red', label='Fail Low')
        ax2.axhspan(thresholds['max_120s'], 5, alpha=0.1, color='red', label='Fail High')
        ax2.axhspan(thresholds['min_120s'], thresholds['max_120s'], alpha=0.1, 
                   color='green', label='Pass Range')
        
        ax2.set_title('120s Reading Distribution', fontsize=14, fontweight='bold', pad=20)
        ax2.set_ylabel('Voltage (V)', fontsize=12)
        ax2.set_ylim(0, 5)
        ax2.set_xticklabels(['120s'])
        ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
        ax2.legend(loc='upper right')
    
    plt.suptitle(f'Job {matched_jobs[0].split(".")[0]} Analysis', 
                fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    return fig

def analyze_job(df, job_number, threshold_set='Standard'):
    """Analyze data for a specific job number."""
    if len(df) == 0:
        st.error("No data loaded. Please load data first.")
        return None

    if 'Job #' not in df.columns:
        st.error("Error: Job # column not found in data")
        return None

    job_data = get_job_data(df, job_number)

    if len(job_data) == 0:
        st.error(f"No data found for Job # {job_number}")
        unique_jobs = df['Job #'].unique()
        st.write("Available Job Numbers in database:")
        st.write(sorted(unique_jobs)[:20])
        return None

    matched_jobs = sorted(job_data['Job #'].unique())
    thresholds = THRESHOLDS[threshold_set]

    # Calculate metrics
    job_data = calculate_metrics(job_data)

    # Determine Pass/Fail
    results = determine_pass_fail(job_data, threshold_set)

    # Calculate summary statistics
    total_sensors = len(results)
    passed_sensors = len(results[results['Pass/Fail'].isin(['PASS', 'OT-', 'TT', 'OT+'])])
    failed_sensors = len(results[results['Pass/Fail'].isin(['FL', 'FH'])])
    dm_sensors = len(results[results['Pass/Fail'] == 'DM'])
    counted_sensors = passed_sensors + failed_sensors

    pass_rate = (passed_sensors / counted_sensors * 100) if counted_sensors > 0 else 0
    fail_rate = (failed_sensors / counted_sensors * 100) if counted_sensors > 0 else 0

    # Count each status code
    status_counts = {'FL': 0, 'FH': 0, 'OT-': 0, 'TT': 0, 'OT+': 0, 'DM': 0, 'PASS': 0}
    for idx, row in results.iterrows():
        status = row['Pass/Fail']
        if status in status_counts:
            status_counts[status] += 1

    # Store analysis info
    analysis_info = {
        'matched_jobs': matched_jobs,
        'thresholds': thresholds,
        'threshold_set': threshold_set,
        'total_sensors': total_sensors,
        'passed_sensors': passed_sensors,
        'failed_sensors': failed_sensors,
        'dm_sensors': dm_sensors,
        'pass_rate': pass_rate,
        'fail_rate': fail_rate,
        'status_counts': status_counts,
        'results': results
    }

    return analysis_info

# Main app
st.markdown("""
<div class="main-header">
    <h1 style="color: white; margin: 0;">🔬 Sensor Analysis Dashboard</h1>
    <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem; font-size: 1.1rem;">
        Advanced sensor data analysis with real-time insights
    </p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'current_job' not in st.session_state:
    st.session_state.current_job = None
if 'current_threshold' not in st.session_state:
    st.session_state.current_threshold = 'Standard'

# Sidebar for data loading
with st.sidebar:
    st.markdown("### 📁 Data Source")
    
    data_source = st.radio(
        "Select input method:",
        ["📤 Upload CSV", "💾 Use Database"],
        label_visibility="collapsed"
    )
    
    df = pd.DataFrame()
    
    if data_source == "📤 Upload CSV":
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=['csv'],
            help="Upload your sensor data CSV file"
        )
        if uploaded_file is not None:
            with st.spinner("Loading data..."):
                df = load_data_from_csv(uploaded_file)
                if len(df) > 0:
                    st.success(f"✅ Loaded {len(df):,} records")
    else:
        if st.button("🔄 Load Database", use_container_width=True):
            with st.spinner("Connecting to database..."):
                df = load_data_from_db('sensor_data.db')
                if len(df) > 0:
                    st.success(f"✅ Loaded {len(df):,} records")
    
    if len(df) > 0:
        st.markdown("---")
        st.markdown("### ⚙️ Analysis Settings")
        
        with st.form(key="analysis_form"):
            job_number = st.text_input(
                "Job Number:",
                placeholder="Enter job number...",
                help="Enter the job number to analyze"
            )
            
            threshold_set = st.radio(
                "Threshold Set:",
                ["Standard", "High Range"],
                help="Select the threshold criteria set"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit_button = st.form_submit_button(
                    "🔍 Analyze",
                    use_container_width=True
                )
            with col2:
                export_button = st.form_submit_button(
                    "📊 Export",
                    use_container_width=True
                )

# Main content area
if len(df) > 0:
    # Process analysis if submitted
    if submit_button and job_number:
        with st.spinner("Analyzing data..."):
            analysis_info = analyze_job(df, job_number, threshold_set)
            if analysis_info:
                st.session_state.analysis_results = analysis_info
                st.session_state.current_job = job_number
                st.session_state.current_threshold = threshold_set
    
    # Display results if available
    if st.session_state.analysis_results:
        info = st.session_state.analysis_results
        
        # Quick Summary Cards
        st.markdown("### 📊 Quick Summary")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="Total Sensors",
                value=f"{info['total_sensors']:,}",
                delta=None
            )
        
        with col2:
            st.metric(
                label="Pass Rate",
                value=f"{info['pass_rate']:.1f}%",
                delta=f"{info['passed_sensors']} passed"
            )
        
        with col3:
            st.metric(
                label="Fail Rate",
                value=f"{info['fail_rate']:.1f}%",
                delta=f"{info['failed_sensors']} failed"
            )
        
        with col4:
            st.metric(
                label="Data Missing",
                value=f"{info['dm_sensors']}",
                delta="Not counted"
            )
        
        with col5:
            st.metric(
                label="Job(s)",
                value=len(info['matched_jobs']),
                delta=info['matched_jobs'][0].split('.')[0]
            )
        
        st.markdown("---")
        
        # Create tabs for organized view
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Visualization", "📋 Data Table", "📊 Status Breakdown", "ℹ️ Thresholds"])
        
        with tab1:
            # Enhanced visualization
            fig = create_enhanced_plot(df, st.session_state.current_job, st.session_state.current_threshold)
            if fig:
                st.pyplot(fig)
                plt.close()
        
        with tab2:
            # Data filters
            st.markdown("#### 🔍 Filters")
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            
            with col1:
                status_filter = st.multiselect(
                    "Status:",
                    options=info['results']['Pass/Fail'].unique().tolist(),
                    default=info['results']['Pass/Fail'].unique().tolist()
                )
            
            with col2:
                serial_search = st.text_input(
                    "Serial Number(s):",
                    placeholder="Comma-separated..."
                )
            
            with col3:
                channel_filter = st.selectbox(
                    "Channel:",
                    options=["All"] + sorted(info['results']['Channel'].unique().tolist()),
                    index=0
                )
            
            with col4:
                st.write("")  # Spacer
                if st.button("🔄 Reset Filters"):
                    st.rerun()
            
            # Apply filters
            filtered_data = info['results'].copy()
            
            if status_filter:
                filtered_data = filtered_data[filtered_data['Pass/Fail'].isin(status_filter)]
            
            if serial_search:
                serials = [s.strip() for s in serial_search.split(',') if s.strip()]
                if serials:
                    mask = filtered_data['Serial Number'].str.contains('|'.join(serials), case=False, na=False)
                    filtered_data = filtered_data[mask]
            
            if channel_filter != "All":
                filtered_data = filtered_data[filtered_data['Channel'] == channel_filter]
            
            # Display count
            st.info(f"Showing {len(filtered_data)} of {len(info['results'])} sensors")
            
            # Format display data
            display_data = filtered_data.copy()
            for col in display_data.columns:
                if col.startswith('0s(') or col.startswith('90s(') or col.startswith('120s('):
                    display_data[col] = display_data[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
                elif col == '120s(St.Dev.)':
                    display_data[col] = display_data[col].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
            
            # Display table with styling
            st.dataframe(
                display_data,
                use_container_width=True,
                hide_index=True,
                height=400
            )
        
        with tab3:
            # Status breakdown with visual chart
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("#### Status Distribution")
                for status, count in info['status_counts'].items():
                    if count > 0:
                        pct = (count / info['total_sensors'] * 100)
                        badge_html = create_status_badge(status)
                        st.markdown(f"{badge_html} **{count}** ({pct:.1f}%)", unsafe_allow_html=True)
            
            with col2:
                # Create pie chart for status distribution
                fig, ax = plt.subplots(figsize=(8, 6))
                
                # Filter out zero counts
                plot_labels = []
                plot_sizes = []
                plot_colors = []
                
                for status, count in info['status_counts'].items():
                    if count > 0:
                        plot_labels.append(f"{status} ({count})")
                        plot_sizes.append(count)
                        plot_colors.append(STATUS_COLORS.get(status, '#6c757d'))
                
                if plot_sizes:
                    ax.pie(plot_sizes, labels=plot_labels, colors=plot_colors, 
                          autopct='%1.1f%%', startangle=90)
                    ax.set_title('Status Distribution', fontsize=14, fontweight='bold', pad=20)
                    st.pyplot(fig)
                    plt.close()
        
        with tab4:
            # Threshold information
            st.markdown("#### Current Threshold Settings")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Threshold Set:** {info['threshold_set']}")
                st.markdown(f"**120s Voltage Range:** {info['thresholds']['min_120s']} - {info['thresholds']['max_120s']}V")
                st.markdown(f"**Max Std Dev:** {info['thresholds']['max_std_dev']}V")
            
            with col2:
                st.markdown(f"**% Change Range:** {info['thresholds']['min_pct_change']}% to {info['thresholds']['max_pct_change']}%")
                st.markdown(f"**Applied to:** {info['total_sensors']} sensors")
            
            # Legend
            st.markdown("---")
            st.markdown("#### 📋 Status Code Reference")
            
            legend_data = {
                'Code': ['FL', 'FH', 'OT-', 'TT', 'OT+', 'DM', 'PASS'],
                'Description': [
                    'Failed Low (< min voltage)',
                    'Failed High (> max voltage)',
                    'Out of Tolerance Negative (< min % change)',
                    'Test-to-Test Variability (> max std dev)',
                    'Out of Tolerance Positive (> max % change)',
                    'Data Missing (not counted)',
                    'All criteria met'
                ],
                'Category': ['FAIL', 'FAIL', 'PASS*', 'PASS*', 'PASS*', 'N/A', 'PASS']
            }
            
            legend_df = pd.DataFrame(legend_data)
            st.table(legend_df)
            st.caption("*OT-, TT, and OT+ are counted as PASS in statistics")

else:
    # Welcome screen when no data is loaded
    st.info("👈 Please load data using the sidebar to begin analysis")
    
    # Show sample instructions
    with st.expander("📖 How to use this tool"):
        st.markdown("""
        1. **Load your data** using the sidebar (CSV upload or database)
        2. **Enter a Job Number** to analyze
        3. **Select threshold criteria** (Standard or High Range)
        4. **Click Analyze** to generate results
        5. **Explore the tabs** for different views of your data
        
        The tool will automatically:
        - Calculate pass/fail rates
        - Show status breakdowns
        - Generate visualizations
        - Allow filtering and searching
        """)

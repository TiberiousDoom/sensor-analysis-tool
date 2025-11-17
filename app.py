import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# Page configuration
st.set_page_config(page_title="Sensor Analysis Tool", layout="wide")

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

    # Define priority order for status codes: FL > FH > OT- > TT > OT+ > DM > PASS
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

        # Determine overall status with priority - show only the highest priority code
        if len(all_failure_codes) == 0:
            status = 'PASS'
        else:
            # Sort by priority and take only the highest priority code
            unique_failures = list(set(all_failure_codes))
            unique_failures.sort(key=lambda x: status_priority.get(x, 99))
            status = unique_failures[0]  # Only display the highest priority status

        # Add overall columns
        serial_row['Pass/Fail'] = status
        serial_row['120s(St.Dev.)'] = std_dev_120

        results.append(serial_row)

    # Create DataFrame and reorder columns
    results_df = pd.DataFrame(results)

    # Build desired column order: Serial Number, Channel, Pass/Fail, 120s(St.Dev.), then all test columns
    base_cols = ['Serial Number', 'Channel', 'Pass/Fail', '120s(St.Dev.)']

    # Get all test columns (they're already in order from the loop)
    test_cols = [col for col in results_df.columns if col not in base_cols]

    # Reorder
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

    # Display header
    st.markdown("---")
    st.subheader(f"JOB ANALYSIS: {matched_jobs[0] if len(matched_jobs) == 1 else f'{len(matched_jobs)} entries starting with {job_number}'}")
    st.write(f"**Threshold Set:** {threshold_set} | **120s Range:** {thresholds['min_120s']}-{thresholds['max_120s']}V | " +
             f"**% Change:** {thresholds['min_pct_change']}% to {thresholds['max_pct_change']}% | " +
             f"**Max Std Dev:** {thresholds['max_std_dev']}V")

    # Display Summary, Breakdown, and Legend in columns
    col1, col2, col3 = st.columns([1, 1, 1.5])

    with col1:
        st.markdown("**SUMMARY STATISTICS**")
        st.write(f"**Total Sensors:** {total_sensors}")
        st.write(f"**Passed:** {passed_sensors} ({pass_rate:.1f}%)")
        st.write(f"**Failed:** {failed_sensors} ({fail_rate:.1f}%)")
        st.write(f"**Data Missing:** {dm_sensors} (not counted)")

    with col2:
        st.markdown("**BREAKDOWN**")
        for code in ['FL', 'FH', 'OT-', 'TT', 'OT+', 'DM', 'PASS']:
            count = status_counts[code]
            if count > 0:
                percentage = (count / total_sensors * 100)
                st.write(f"**{code}:** {count} ({percentage:.1f}%)")

    with col3:
        with st.expander("📋 STATUS CODE LEGEND", expanded=True):
            st.write(f"- **FL:** Failed Low (< {thresholds['min_120s']}V)")
            st.write(f"- **FH:** Failed High (> {thresholds['max_120s']}V)")
            st.write(f"- **OT-:** Out of Tol. Neg (< {thresholds['min_pct_change']}%) PASS")
            st.write(f"- **TT:** Test-to-Test (> {thresholds['max_std_dev']}V) PASS")
            st.write(f"- **OT+:** Out of Tol. Pos (> {thresholds['max_pct_change']}%) PASS")
            st.write(f"- **DM:** Data Missing (not counted)")
            st.write(f"- **PASS:** All criteria met")

    # Format the results for display
    display_results = results.copy()

    # Format numeric columns to 1 decimal place
    for col in display_results.columns:
        if col.startswith('0s(') or col.startswith('90s(') or col.startswith('120s('):
            display_results[col] = display_results[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else x)
        elif col == '120s(St.Dev.)':
            display_results[col] = display_results[col].apply(lambda x: f"{x:.3f}" if pd.notna(x) else x)

    return display_results

def plot_job_data(df, job_number, threshold_set='Standard'):
    """Generate plot for a specific job."""
    if len(df) == 0:
        st.error("No data loaded. Please load data first.")
        return

    job_data = get_job_data(df, job_number)

    if len(job_data) == 0:
        st.error(f"No data found for Job # {job_number}")
        return

    matched_jobs = sorted(job_data['Job #'].unique())

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
                    'all_readings': readings.tolist()
                })

    if not time_data:
        st.error("No valid data points to plot")
        return

    df_plot = pd.DataFrame(time_data)

    # Create plot
    fig, ax = plt.subplots(figsize=(12, 6))

    # Shaded areas first (so they're behind the mean line)
    ax.fill_between(df_plot['time'],
                     df_plot['p5'],
                     df_plot['p95'],
                     alpha=0.15, color='green', label='5th-95th Percentile')
    
    ax.fill_between(df_plot['time'],
                     df_plot['mean'] - df_plot['std'],
                     df_plot['mean'] + df_plot['std'],
                     alpha=0.25, color='blue', label='±1 Std Dev')

    # Plot mean line on top
    ax.plot(df_plot['time'], df_plot['mean'], 'b-', linewidth=2.5, label='Mean', zorder=10)

    # Formatting
    if len(matched_jobs) > 1:
        base_num = matched_jobs[0].split('.')[0]
        title = f"Sensor Readings Over Time - Jobs {base_num}"
    else:
        job_num_parts = matched_jobs[0].split('.')
        title = f"Sensor Readings Over Time - Job {job_num_parts[0]}"

    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Voltage (V)', fontsize=12)
    ax.set_ylim(0, 5)
    ax.set_yticks(np.arange(0, 5.5, 0.5))
    ax.grid(True, alpha=0.3, which='both')
    ax.legend(loc='best')

    st.pyplot(fig)
    plt.close()

def plot_serial_data(df, job_number, serial_numbers):
    """Generate plot for specific serial numbers."""
    if len(df) == 0 or not serial_numbers:
        return

    job_data = get_job_data(df, job_number)

    if len(job_data) == 0:
        return

    # Filter for the specific serial numbers
    serial_data = job_data[job_data['Serial Number'].isin(serial_numbers)]

    if len(serial_data) == 0:
        st.warning("No data found for the filtered serial numbers")
        return

    # Create plot
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot each serial number with a different color
    colors = plt.cm.tab10(np.linspace(0, 1, len(serial_numbers)))

    for idx, serial in enumerate(serial_numbers):
        serial_rows = serial_data[serial_data['Serial Number'] == serial]

        for row_idx, (_, row) in enumerate(serial_rows.iterrows()):
            test_readings = []
            test_times = []
            for time_point in TIME_POINTS:
                if time_point in row and pd.notna(row[time_point]):
                    test_readings.append(row[time_point])
                    test_times.append(float(time_point))

            if test_readings:
                label = f"{serial}" if row_idx == 0 else None
                ax.plot(test_times, test_readings, '-o', color=colors[idx],
                       label=label, linewidth=2, markersize=6, alpha=0.7)

    ax.set_title("Filtered Serial Number Readings Over Time", fontsize=14, fontweight='bold')
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.set_ylabel('Voltage (V)', fontsize=12)
    ax.set_ylim(0, 5)
    ax.set_yticks(np.arange(0, 5.5, 0.5))
    ax.grid(True, alpha=0.3, which='both')
    ax.legend(loc='best', fontsize=10)

    st.pyplot(fig)
    plt.close()

# Main app
st.title("🔬 Sensor Data Analysis Tool")

# Sidebar for data loading
st.sidebar.header("Data Loading")
data_source = st.sidebar.radio("Select Data Source:", ["Upload CSV", "Use Database File"])

df = pd.DataFrame()

if data_source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=['csv'])
    if uploaded_file is not None:
        df = load_data_from_csv(uploaded_file)
        if len(df) > 0:
            st.sidebar.success(f"Loaded {len(df)} records")
else:
    if st.sidebar.button("Load Database"):
        df = load_data_from_db('sensor_data.db')
        if len(df) > 0:
            st.sidebar.success(f"Loaded {len(df)} records")

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'current_job' not in st.session_state:
    st.session_state.current_job = None
if 'current_threshold' not in st.session_state:
    st.session_state.current_threshold = 'Standard'

# Main interface
if len(df) > 0:
    st.sidebar.header("Analysis Parameters")

    # Use form to allow Enter key to submit
    with st.sidebar.form(key="analysis_form"):
        job_number = st.text_input("Job Number:", "")
        threshold_set = st.radio("Threshold Set:", ["Standard", "High Range"])
        submit_button = st.form_submit_button("Analyze Job")

    if submit_button and job_number:
        results = analyze_job(df, job_number, threshold_set)
        if results is not None:
            st.session_state.analysis_results = results
            st.session_state.current_job = job_number
            st.session_state.current_threshold = threshold_set

    # Display results if they exist in session state
    if st.session_state.analysis_results is not None:
        results = st.session_state.analysis_results

        st.markdown("---")
        st.subheader("Results Table")

        # Add filtering options
        st.markdown("**Filter Results:**")
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 1, 1])

        with filter_col1:
            # Get unique Pass/Fail statuses
            all_statuses = sorted(results['Pass/Fail'].unique().tolist())
            selected_statuses = st.multiselect(
                "Filter by Status:",
                options=all_statuses,
                default=all_statuses,
                key="status_filter"
            )

        with filter_col2:
            # Serial Number search
            serial_search = st.text_input(
                "Search Serial Number:",
                "",
                key="serial_search",
                placeholder="Enter partial serial..."
            )

        with filter_col3:
            # Get unique channels
            all_channels = sorted(results['Channel'].unique().tolist())
            with st.expander("Channel", expanded=False):
                selected_channels = st.multiselect(
                    "Select:",
                    options=all_channels,
                    default=all_channels,
                    key="channel_filter",
                    label_visibility="collapsed"
                )

        with filter_col4:
            # Reset filters button
            st.write("")  # Spacing
            if st.button("🔄 Reset", key="reset_filters"):
                st.session_state.status_filter = all_statuses
                st.session_state.serial_search = ""
                st.session_state.channel_filter = all_channels
                st.rerun()

        # Apply filters
        filtered_results = results.copy()

        # Filter by status
        if selected_statuses:
            filtered_results = filtered_results[filtered_results['Pass/Fail'].isin(selected_statuses)]

        # Filter by serial number search
        if serial_search:
            filtered_results = filtered_results[
                filtered_results['Serial Number'].str.contains(serial_search, case=False, na=False)
            ]

        # Filter by channel
        if selected_channels:
            filtered_results = filtered_results[filtered_results['Channel'].isin(selected_channels)]

        # Display filtered count
        st.write(f"Showing {len(filtered_results)} of {len(results)} sensors")

        # Display filtered results
        st.dataframe(filtered_results, use_container_width=True)

        # Show serial number plot if serial search is active
        if serial_search and len(filtered_results) > 0:
            st.markdown("---")
            st.subheader("Filtered Serial Number Plot")
            filtered_serials = filtered_results['Serial Number'].unique().tolist()
            plot_serial_data(df, st.session_state.current_job, filtered_serials)

        st.markdown("---")
        st.subheader("Job Data Plot")
        plot_job_data(df, st.session_state.current_job, st.session_state.current_threshold)
else:
    st.info("👈 Please load data using the sidebar to begin analysis")

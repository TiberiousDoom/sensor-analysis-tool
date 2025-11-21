import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as path_effects
import io
import re
import json
import os
import time
from datetime import datetime
from contextlib import contextmanager

# Page configuration with custom theme
st.set_page_config(
    page_title="Sensor Analysis Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Sensor Data Analysis Tool v2.2 - Optimized Performance"
    }
)

# ==================== CONFIGURATION CONSTANTS ====================
# Anomaly Detection
ANOMALY_VOLTAGE_DELTA_THRESHOLD = 3.0  # Volts
ANOMALY_STD_DEV_MULTIPLIER = 2.0  # Times normal threshold

# Plotting
PLOT_FIGURE_SIZE = (15, 6)  # Width, Height in inches
PLOT_VOLTAGE_LIMITS = (0, 5)  # Min, Max voltage for plots

# History & Caching
MAX_JOB_HISTORY = 50  # Number of historical jobs to compare
PRINT_DIALOG_DELAY_MS = 250  # Delay before triggering print

# Data validation
MAX_JOB_NUMBER_LENGTH = 50  # Maximum characters in job number
MAX_CSV_SIZE_MB = 100  # Maximum CSV upload size

# ==================== STATUS BADGE CLASS ====================
class StatusBadge:
    """Centralized status badge management."""
    
    STYLES = {
        'PASS': {'class': 'status-pass', 'icon': '✓', 'color': '#10b981'},
        'FL': {'class': 'status-fail', 'icon': '✗', 'color': '#ef4444'},
        'FH': {'class': 'status-fail', 'icon': '✗', 'color': '#dc2626'},
        'OT-': {'class': 'status-warning', 'icon': '⚠', 'color': '#f59e0b'},
        'TT': {'class': 'status-warning', 'icon': '⚠', 'color': '#eab308'},
        'OT+': {'class': 'status-warning', 'icon': '⚠', 'color': '#fb923c'},
        'DM': {'class': 'status-info', 'icon': '•', 'color': '#6b7280'},
    }
    
    @classmethod
    def get_html(cls, status, include_icon=True):
        """Generate HTML badge for status."""
        style = cls.STYLES.get(status, cls.STYLES['DM'])
        icon = f"{style['icon']} " if include_icon else ""
        return f'<span class="status-pill {style["class"]}">{icon}{status}</span>'
    
    @classmethod
    def get_color(cls, status):
        """Get color for status."""
        return cls.STYLES.get(status, cls.STYLES['DM'])['color']

# ==================== CONTEXT MANAGER FOR PLOTS ====================
@contextmanager
def create_plot(*args, **kwargs):
    """Context manager for matplotlib figures to prevent memory leaks."""
    fig = plt.figure(*args, **kwargs)
    try:
        yield fig
    finally:
        plt.close(fig)

# ==================== TUTORIAL SYSTEM ====================

class TutorialSystem:
    """Interactive tutorial system for the Sensor Analysis Dashboard"""
    
    def __init__(self):
        self.tutorial_steps = [
            {
                'id': 'welcome',
                'title': '👋 Welcome to Sensor Analysis Dashboard!',
                'content': """
                This tutorial will guide you through analyzing your sensor data in just a few minutes.
                
                **You'll learn how to:**
                - 📁 Load your sensor data
                - 🔍 Analyze a specific job
                - 📊 Navigate and interpret results
                - 💾 Export your findings
                
                **Estimated time:** 3-4 minutes
                
                Click **Next** to begin!
                """,
                'action_required': None,
                'completion_check': None
            },
            {
                'id': 'load_data',
                'title': '📁 Step 1: Load Your Data',
                'content': """
                First, let's load some sensor data.
                
                **Look at the sidebar on the left** ⬅️
                
                You have two options:
                1. **📤 Upload CSV** - Upload your own sensor data file
                2. **💾 Use Database** - Load from the sample database
                
                **For this tutorial:** Select "Use Database" and click the **"Load Database"** button.
                
                Once you see "✅ Loaded" message, click **Next** to continue.
                
                **Note:** You can skip ahead if you prefer to explore on your own!
                """,
                'action_required': None,  # Changed from 'data_loaded' to allow progression
                'completion_check': None  # Removed check to allow clicking Next
            },
            {
                'id': 'enter_job',
                'title': '🔍 Step 2: Enter a Job Number',
                'content': """
                Great! Your data is loaded.
                
                **In the sidebar,** find the "Job Number" input field under **⚙️ Analysis Settings**.
                
                **Try this:** Type `258` in the Job Number field.
                
                💡 **Tip:** The system supports prefix matching, so "258" will find all jobs starting with 258 (like 258.1, 258.2, etc.)
                
                After entering the job number, click **Next**.
                """,
                'action_required': 'job_entered',
                'completion_check': None
            },
            {
                'id': 'analyze',
                'title': '▶️ Step 3: Run Analysis',
                'content': """
                Perfect! Now let's analyze the data.
                
                **In the sidebar,** you'll see:
                - **Threshold Set:** Choose "Standard" (default) or "High Range"
                - **🔍 Analyze button:** Click this to process the data
                
                The analysis will:
                - Calculate pass/fail rates for each sensor
                - Identify any issues or anomalies
                - Generate visualizations and statistics
                
                **Click the "🔍 Analyze" button** in the sidebar, then click **Next** here.
                
                **Note:** If you haven't loaded data yet, you can skip ahead and come back later!
                """,
                'action_required': None,  # Changed from 'analysis_complete'
                'completion_check': None  # Removed strict check
            },
            {
                'id': 'summary',
                'title': '📊 Step 4: Understanding the Summary',
                'content': """
                Excellent! Your analysis is complete.
                
                **Look at the Quick Summary cards** at the top of the page:
                
                - **Total Sensors** - Number of sensors analyzed
                - **Pass Rate** - Percentage that passed (🟢 Green is good!)
                - **Fail Rate** - Percentage that failed (🔴 Red needs attention)
                - **Data Missing** - Sensors with incomplete readings
                - **Job(s)** - Number of job records found
                
                **Color coding:**
                - 🟢 **Green metrics** = Good performance
                - 🔴 **Red metrics** = Issues detected
                
                Take a moment to review these numbers, then click **Next**.
                """,
                'action_required': None,
                'completion_check': None
            },
            {
                'id': 'data_table',
                'title': '📋 Step 5: Exploring the Data Table',
                'content': """
                Now let's look at the detailed results.
                
                **Click on the "📋 Data Table" tab** (if not already selected).
                
                You'll see:
                - **Serial Number** - Unique sensor identifier
                - **Pass/Fail** - Overall status for each sensor
                - **Test readings** - Voltage measurements at different time points
                - **Color-coded rows:**
                  - 🟢 Green = Passed
                  - 🔴 Red = Failed (FL/FH)
                  - 🟡 Yellow = Warnings (OT-/TT/OT+)
                  - ⚪ Gray = Missing data
                
                **Try clicking on the status pills** in the filter section to show/hide specific statuses!
                """,
                'action_required': None,
                'completion_check': None
            },
            {
                'id': 'filters',
                'title': '🔍 Step 6: Using Filters',
                'content': """
                Filters help you focus on what matters most.
                
                **At the top of the Data Table tab**, you'll see:
                
                1. **Status Pills** - Click to toggle specific statuses on/off
                   - Try clicking **"PASS"** to hide all passing sensors
                   - This shows only the problem cases!
                
                2. **Serial Number Search** - Find specific sensors
                   - Enter comma-separated serial numbers
                   - Supports partial matching
                
                **Filters apply automatically** - no need to click a button!
                
                Experiment with the filters, then click **Next**.
                """,
                'action_required': None,
                'completion_check': None
            },
            {
                'id': 'visualization',
                'title': '📈 Step 7: Visualization Tab',
                'content': """
                Visual data helps spot trends and patterns quickly.
                
                **Click the "📈 Visualization" tab** to see:
                
                **Left Plot - Sensor Readings Over Time:**
                - Shows how readings change from 0s to 120s
                - Colored bands show acceptable ranges
                - Mean line with confidence intervals
                
                **Right Plot - 120s Reading Distribution:**
                - Box plot showing the spread of final readings
                - Green zone = passing range
                - Red zones = failure thresholds
                
                Visual patterns can reveal issues that aren't obvious in tables!
                """,
                'action_required': None,
                'completion_check': None
            },
            {
                'id': 'export',
                'title': '💾 Step 8: Exporting Results',
                'content': """
                Need to share your analysis? Export it!
                
                **In the sidebar,** find the **📊 Export** button.
                
                When you click it:
                1. A download button will appear
                2. Click "📥 Download Results CSV"
                3. The file includes all your filtered data
                
                **Quick Reports** (in main area):
                - 📄 **Summary Report** - Comprehensive analysis overview
                - ❌ **Failed Sensors Report** - List of problematic sensors
                
                These reports are ready to print or share with your team!
                """,
                'action_required': None,
                'completion_check': None
            },
            {
                'id': 'advanced',
                'title': '⚡ Step 9: Advanced Features',
                'content': """
                You're almost a pro! Here are some advanced features:
                
                **⚠️ Anomaly Detection** (top of main area)
                - Automatically flags high variability
                - Detects inconsistent test results
                - Expands when issues are found
                
                **📊 Status Breakdown** tab
                - Pie chart of status distribution
                - Detailed counts and percentages
                
                **ℹ️ Thresholds** tab
                - View current threshold settings
                - Status code reference
                - Decision logic flowchart
                
                **📜 Recent Jobs** (sidebar)
                - Quick access to previously analyzed jobs
                """,
                'action_required': None,
                'completion_check': None
            },
            {
                'id': 'complete',
                'title': '🎉 Tutorial Complete!',
                'content': """
                Congratulations! You're now ready to analyze sensor data like a pro! 🚀
                
                **Quick Reference:**
                1. Load Data → 2. Enter Job → 3. Analyze → 4. Review → 5. Export
                
                **Remember:**
                - Use filters to focus on problems
                - Colors indicate status at a glance
                - Export filtered results for reporting
                - Check anomaly alerts for unusual patterns
                
                **Need help later?**
                - Click **"❓ Need Help?"** in the sidebar
                - Click **"🎓 Restart Tutorial"** anytime
                
                Click **Finish** to start analyzing your data!
                """,
                'action_required': None,
                'completion_check': None
            }
        ]
        
        # Initialize tutorial state
        if 'tutorial_state' not in st.session_state:
            st.session_state.tutorial_state = {
                'active': False,
                'current_step': 0,
                'completed_steps': [],
                'show_on_start': True,
                'first_visit': True,
                'dismissed': False
            }
    
    def should_show_tutorial(self):
        """Determine if tutorial should auto-start"""
        if st.session_state.tutorial_state['dismissed']:
            return False
        if not st.session_state.tutorial_state['show_on_start']:
            return False
        if st.session_state.tutorial_state['first_visit']:
            return True
        return False
    
    def start_tutorial(self):
        """Begin the tutorial"""
        st.session_state.tutorial_state['active'] = True
        st.session_state.tutorial_state['current_step'] = 0
        st.session_state.tutorial_state['first_visit'] = False
    
    def stop_tutorial(self):
        """End the tutorial"""
        st.session_state.tutorial_state['active'] = False
    
    def dismiss_tutorial(self):
        """Dismiss tutorial permanently for this session"""
        st.session_state.tutorial_state['dismissed'] = True
        st.session_state.tutorial_state['active'] = False
    
    def next_step(self):
        """Move to next tutorial step"""
        current = st.session_state.tutorial_state['current_step']
        if current not in st.session_state.tutorial_state['completed_steps']:
            st.session_state.tutorial_state['completed_steps'].append(current)
        
        if current < len(self.tutorial_steps) - 1:
            st.session_state.tutorial_state['current_step'] += 1
        else:
            self.stop_tutorial()
    
    def previous_step(self):
        """Go back to previous step"""
        if st.session_state.tutorial_state['current_step'] > 0:
            st.session_state.tutorial_state['current_step'] -= 1
    
    def check_step_completion(self):
        """Check if current step's action is completed"""
        current_step = self.tutorial_steps[st.session_state.tutorial_state['current_step']]
        if current_step.get('completion_check'):
            return current_step['completion_check']()
        return True
    
    def render_tutorial_dialog(self):
        """Display the current tutorial step as a dialog"""
        if not st.session_state.tutorial_state['active']:
            return
        
        current_idx = st.session_state.tutorial_state['current_step']
        current_step = self.tutorial_steps[current_idx]
        step_num = current_idx + 1
        total_steps = len(self.tutorial_steps)
        
        # Create a dialog-like experience using container
        with st.container():
            # Progress indicator
            progress = step_num / total_steps
            st.progress(progress, text=f"Step {step_num} of {total_steps}")
            
            # Tutorial card
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 2rem;
                border-radius: 15px;
                color: white;
                margin: 1rem 0;
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            ">
                <h2 style="margin: 0 0 1rem 0; color: white;">{current_step['title']}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Content
            st.markdown(current_step['content'])
            
            # Check if step is completed
            step_completed = self.check_step_completion()
            # Always allow progression - user can skip ahead if they want
            if not step_completed and current_step.get('action_required'):
                st.info(f"💡 **Tip:** Complete the action above for the full experience, or skip ahead to explore on your own!")
            
            st.markdown("---")
            
            # Navigation buttons
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
            
            with col1:
                if step_num > 1:
                    if st.button("⬅️ Previous", key="tutorial_prev", use_container_width=True):
                        self.previous_step()
                        st.rerun()
            
            with col2:
                if st.button("⏭️ Skip All", key="tutorial_skip", use_container_width=True):
                    self.dismiss_tutorial()
                    st.rerun()
            
            with col3:
                # Progress dots
                dots_html = ""
                for i in range(total_steps):
                    if i == current_idx:
                        dots_html += "🔵 "
                    elif i in st.session_state.tutorial_state['completed_steps']:
                        dots_html += "✅ "
                    else:
                        dots_html += "⚪ "
                st.markdown(f"<div style='text-align: center; padding: 0.5rem;'>{dots_html}</div>", 
                           unsafe_allow_html=True)
            
            with col4:
                # Show later checkbox
                show_again = st.checkbox(
                    "Show on startup",
                    value=st.session_state.tutorial_state['show_on_start'],
                    key="tutorial_show_again",
                    help="Toggle whether tutorial appears when you open the app"
                )
                st.session_state.tutorial_state['show_on_start'] = show_again
            
            with col5:
                if step_num < total_steps:
                    button_label = "Next ➡️"
                    if st.button(button_label, key="tutorial_next", type="primary", 
                               use_container_width=True):
                        self.next_step()
                        st.rerun()
                else:
                    if st.button("🎉 Finish", key="tutorial_finish", type="primary", 
                               use_container_width=True):
                        st.session_state.tutorial_state['completed_steps'].append(current_idx)
                        self.stop_tutorial()
                        st.balloons()
                        st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
    
    def render_help_sidebar(self):
        """Render help menu in sidebar"""
        with st.expander("🎓 Tutorial & Help", expanded=False):
            st.markdown("### Interactive Tutorial")
            
            # Tutorial controls
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Start Tutorial", use_container_width=True, key="start_tutorial_btn"):
                    self.start_tutorial()
                    st.rerun()
            
            with col2:
                if st.button("🔄 Reset Progress", use_container_width=True, key="reset_tutorial_btn"):
                    st.session_state.tutorial_state['completed_steps'] = []
                    st.session_state.tutorial_state['current_step'] = 0
                    st.session_state.tutorial_state['first_visit'] = True
                    st.session_state.tutorial_state['dismissed'] = False
                    st.success("Tutorial reset!")
            
            st.markdown("---")
            
            # Quick reference
            st.markdown("""
            ### 📚 Quick Reference
            
            **Workflow:**
            1. Load data (CSV or Database)
            2. Enter job number
            3. Click "Analyze"
            4. Review results
            5. Export as needed
            
            **Status Codes:**
            - **PASS** ✅ - All checks passed
            - **FL** ❌ - Failed Low voltage
            - **FH** ❌ - Failed High voltage
            - **OT-** ⚠️ - Out of Tolerance (Low %)
            - **TT** ⚠️ - Test-to-Test variability
            - **OT+** ⚠️ - Out of Tolerance (High %)
            - **DM** ⚪ - Data Missing
            
            **Tips:**
            - Use filters to focus on issues
            - Click status pills to toggle
            - Export includes filtered data
            - Check anomaly alerts
            """)
            
            st.markdown("---")
            
            # Keyboard shortcuts
            with st.expander("⌨️ Keyboard Shortcuts", expanded=False):
                st.markdown("""
                - **Ctrl/Cmd + P** - Print report
                - **Tab** - Navigate between fields
                - **Enter** - Submit form
                """)
            
            # Settings
            st.markdown("### ⚙️ Tutorial Settings")
            show_startup = st.checkbox(
                "Show tutorial on app startup",
                value=st.session_state.tutorial_state['show_on_start'],
                key="tutorial_settings_checkbox"
            )
            st.session_state.tutorial_state['show_on_start'] = show_startup

# Initialize tutorial system
tutorial = TutorialSystem()

# ==================== END TUTORIAL SYSTEM ====================

# Custom CSS for modern UI with dark mode support
st.markdown("""
<style>
    /* Print-specific styles - hide UI elements when printing */
    @media print {
        /* Hide Streamlit UI elements */
        header, footer, .stApp > header, .stDeployButton, 
        section[data-testid="stSidebar"], .stButton, 
        .stDownloadButton, .stTabs [data-baseweb="tab-list"] {
            display: none !important;
        }
        
        /* Hide tutorial elements */
        .tutorial-overlay, .tutorial-card {
            display: none !important;
        }
        
        /* Optimize page for printing */
        body, .main, .block-container {
            margin: 0 !important;
            padding: 10px !important;
            max-width: 100% !important;
        }
        
        /* Prevent page breaks inside tables */
        table, .dataframe {
            page-break-inside: avoid;
        }
        
        /* Better contrast for print */
        * {
            color: black !important;
            background: white !important;
        }
        
        /* Keep table borders visible */
        table, th, td {
            border: 1px solid black !important;
        }
    }
    
    /* Detect dark mode */
    @media (prefers-color-scheme: dark) {
        /* Dark mode overrides */
        .stApp {
            background-color: #1a1a1a;
        }
        
        div[data-testid="metric-container"] {
            background: #2d2d2d !important;
            border-left: 4px solid #7c8bff !important;
            color: #ffffff !important;
        }
        
        div[data-testid="metric-container"] label {
            color: #b0b0b0 !important;
        }
        
        div[data-testid="metric-container"] div[data-testid="metric-delta"] {
            color: #9ca3af !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: #2d2d2d !important;
            border: 2px solid #3d3d3d !important;
            color: #ffffff !important;
        }
        
        .dataframe {
            background-color: #2d2d2d !important;
            color: #ffffff !important;
        }
        
        .dataframe tbody tr:hover {
            background-color: #3d3d3d !important;
        }
        
        section[data-testid="stSidebar"] > div {
            background-color: #2d2d2d !important;
        }
        
        .main-header {
            background: linear-gradient(135deg, #7c8bff 0%, #9b67d6 100%) !important;
            box-shadow: 0 10px 30px rgba(124, 139, 255, 0.2) !important;
        }
        
        .status-card {
            background: #2d2d2d !important;
            border: 1px solid #3d3d3d !important;
        }
        
        .info-card {
            background: #2d2d2d !important;
            border: 1px solid #3d3d3d !important;
            color: #ffffff !important;
        }
    }
    
    /* Light mode base styles */
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
    
    /* Metric cards - improved contrast */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.95);
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    div[data-testid="metric-container"] label {
        font-weight: 600;
        font-size: 0.9rem;
        color: #4a5568;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    div[data-testid="metric-container"] > div[data-testid="metric-value"] {
        font-size: 2rem;
        font-weight: 700;
    }
    
    /* Status pills with better contrast */
    .status-pill {
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        display: inline-block;
        margin: 3px;
        letter-spacing: 0.5px;
    }
    
    .status-pass {
        background: #10b981;
        color: white;
        box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
    }
    
    .status-fail {
        background: #ef4444;
        color: white;
        box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
    }
    
    .status-warning {
        background: #f59e0b;
        color: white;
        box-shadow: 0 2px 4px rgba(245, 158, 11, 0.3);
    }
    
    .status-info {
        background: #6b7280;
        color: white;
        box-shadow: 0 2px 4px rgba(107, 114, 128, 0.3);
    }
    
    /* Enhanced button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        padding: 0.7rem 1.8rem;
        border-radius: 25px;
        font-weight: 700;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Tab styling with better contrast */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0px 24px;
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        font-weight: 700;
        transition: all 0.2s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    /* Anomaly alert styling */
    .anomaly-high {
        background-color: #fee2e2;
        border-left: 4px solid #dc2626;
        padding: 0.5rem;
        border-radius: 5px;
        margin-bottom: 0.25rem;
        color: #7f1d1d;
        font-weight: 600;
    }
    
    .anomaly-medium {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 0.5rem;
        border-radius: 5px;
        margin-bottom: 0.25rem;
        color: #78350f;
        font-weight: 600;
    }
    
    /* Data quality bar */
    .quality-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    .quality-excellent {
        background: #d1fae5;
        color: #065f46;
    }
    
    .quality-good {
        background: #dbeafe;
        color: #0c4a6e;
    }
    
    .quality-poor {
        background: #fed7aa;
        color: #92400e;
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
        'min_pct_change': 0.00,
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

# ==================== INPUT VALIDATION ====================
def validate_job_number(job_input):
    """Validate and sanitize job number input."""
    if not job_input or not job_input.strip():
        return None, "Please enter a job number"
    
    # Remove whitespace
    job_input = job_input.strip()
    
    # Check for SQL injection attempts (basic)
    dangerous_chars = [';', '--', '/*', '*/', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT']
    if any(char.upper() in job_input.upper() for char in dangerous_chars):
        return None, "Invalid characters in job number"
    
    # Validate format (alphanumeric, dots, dashes only)
    if not re.match(r'^[A-Za-z0-9.-]+$', job_input):
        return None, "Job number must contain only letters, numbers, dots, and dashes"
    
    # Check reasonable length
    if len(job_input) > MAX_JOB_NUMBER_LENGTH:
        return None, f"Job number too long (max {MAX_JOB_NUMBER_LENGTH} characters)"
    
    return job_input, None

# ==================== DATA LOADING WITH IMPROVED ERROR HANDLING ====================
@st.cache_data
def load_data_from_db(db_path='sensor_data.db'):
    """Load sensor data from SQLite database with robust error handling."""
    conn = None
    try:
        # Check if file exists first
        if not os.path.exists(db_path):
            st.error(f"❌ Database file not found: {db_path}")
            return pd.DataFrame()
        
        conn = sqlite3.connect(db_path)
        query = "SELECT * FROM sensor_readings"
        df = pd.read_sql_query(query, conn)
        
        # Validate data
        if df.empty:
            st.warning("⚠️ Database is empty")
            return pd.DataFrame()
        
        # Convert time point columns to numeric
        for col in TIME_POINTS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Ensure Job # and Serial Number are strings
        if 'Job #' in df.columns:
            df['Job #'] = df['Job #'].astype(str)
        else:
            st.error("❌ Missing required column: 'Job #'")
            return pd.DataFrame()
        
        if 'Serial Number' in df.columns:
            df['Serial Number'] = df['Serial Number'].astype(str)
        else:
            st.error("❌ Missing required column: 'Serial Number'")
            return pd.DataFrame()
        
        st.info(f"✅ Loaded {len(df):,} records from {len(df['Job #'].unique())} unique jobs")
        return df
        
    except sqlite3.DatabaseError as e:
        st.error(f"❌ Database error: {str(e)}")
        return pd.DataFrame()
    except pd.errors.DatabaseError as e:
        st.error(f"❌ Error reading database: {str(e)}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Unexpected error loading data: {str(e)}")
        return pd.DataFrame()
    finally:
        # Always close connection
        if conn is not None:
            try:
                conn.close()
            except:
                pass

def load_data_from_csv(file):
    """Load sensor data from uploaded CSV file with validation."""
    try:
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_CSV_SIZE_MB * 1024 * 1024:
            st.error(f"❌ File too large (max {MAX_CSV_SIZE_MB}MB)")
            return pd.DataFrame()
        
        df = pd.read_csv(file)
        
        # Validate required columns
        if df.empty:
            st.error("❌ CSV file is empty")
            return pd.DataFrame()
        
        # Convert time point columns to numeric
        for col in TIME_POINTS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Ensure Job # and Serial Number are strings
        if 'Job #' in df.columns:
            df['Job #'] = df['Job #'].astype(str)
        else:
            st.error("❌ Missing required column: 'Job #'")
            return pd.DataFrame()
        
        if 'Serial Number' in df.columns:
            df['Serial Number'] = df['Serial Number'].astype(str)
        else:
            st.error("❌ Missing required column: 'Serial Number'")
            return pd.DataFrame()
        
        st.success(f"✅ Loaded {len(df):,} records from CSV")
        return df
        
    except pd.errors.EmptyDataError:
        st.error("❌ CSV file is empty or invalid")
        return pd.DataFrame()
    except pd.errors.ParserError as e:
        st.error(f"❌ Error parsing CSV: {str(e)}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Unexpected error loading CSV: {str(e)}")
        return pd.DataFrame()

def calculate_metrics(df):
    """Calculate key metrics for sensor readings."""
    metrics = df.copy()

    # Calculate percentage change: (120s - 90s) / (90s - 0s) * 100
    if '0' in df.columns and '90' in df.columns and '120' in df.columns:
        denominator = df['90'] - df['0']
        # Avoid division by zero
        denominator = denominator.replace(0, np.nan)
        metrics['pct_change_90_120'] = ((df['120'] - df['90']) / denominator * 100).replace([np.inf, -np.inf], np.nan)

    return metrics

# ==================== OPTIMIZED DETERMINE_PASS_FAIL ====================
def determine_pass_fail(df, threshold_set='Standard'):
    """Optimized determination of Pass/Fail status based on thresholds."""
    thresholds = THRESHOLDS[threshold_set]
    
    # Group by serial number once
    grouped = df.groupby('Serial Number')
    
    results = []
    status_priority = {'FL': 1, 'FH': 2, 'OT-': 3, 'TT': 4, 'OT+': 5, 'DM': 6, 'PASS': 7}
    
    for serial, group in grouped:
        # Now process pre-grouped data
        readings_120 = group['120'].dropna()
        
        if len(readings_120) == 0:
            continue
            
        std_dev_120 = readings_120.std() if len(readings_120) > 1 else 0
        
        serial_row = {
            'Serial Number': serial,
            'Channel': group.iloc[0].get('Channel', ''),
        }
        
        all_failure_codes = []
        
        # Process each test
        for test_idx, (_, row) in enumerate(group.iterrows(), 1):
            test_prefix = f'T{test_idx}'
            
            # Add readings
            serial_row[f'0s({test_prefix})'] = row.get('0', np.nan)
            serial_row[f'90s({test_prefix})'] = row.get('90', np.nan)
            serial_row[f'120s({test_prefix})'] = row.get('120', np.nan)
            
            # Check failures
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
        
        # Check std dev
        if std_dev_120 > thresholds['max_std_dev']:
            all_failure_codes.append('TT')
        
        # Determine status
        if len(all_failure_codes) == 0:
            status = 'PASS'
        else:
            unique_failures = list(set(all_failure_codes))
            unique_failures.sort(key=lambda x: status_priority.get(x, 99))
            status = unique_failures[0]
        
        serial_row['Pass/Fail'] = status
        serial_row['120s(St.Dev.)'] = std_dev_120
        results.append(serial_row)
    
    # Create DataFrame
    results_df = pd.DataFrame(results)
    
    # Reorder columns
    base_cols = ['Serial Number', 'Channel', 'Pass/Fail', '120s(St.Dev.)']
    test_cols = [col for col in results_df.columns if col not in base_cols]
    results_df = results_df[base_cols + test_cols]
    
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

def detect_anomalies(results, thresholds):
    """Detect anomalies in sensor data."""
    anomalies = []
    
    for idx, row in results.iterrows():
        serial = row['Serial Number']
        
        # High variability check (using constant)
        std_dev = row['120s(St.Dev.)']
        if pd.notna(std_dev) and std_dev > thresholds['max_std_dev'] * ANOMALY_STD_DEV_MULTIPLIER:
            anomalies.append({
                'serial': serial,
                'channel': row.get('Channel', 'N/A'),
                'type': 'High Variability',
                'severity': 'High',
                'message': f'Std Dev {std_dev:.3f}V exceeds {ANOMALY_STD_DEV_MULTIPLIER}× threshold ({thresholds["max_std_dev"]*ANOMALY_STD_DEV_MULTIPLIER:.3f}V)'
            })
        
        # Check for sudden jumps in test results (using constant)
        test_cols = [col for col in results.columns if col.startswith('120s(')]
        test_values = []
        for col in test_cols:
            val = row[col]
            if pd.notna(val):
                try:
                    test_values.append(float(val))
                except:
                    pass
        
        if len(test_values) > 1:
            max_val = max(test_values)
            min_val = min(test_values)
            if (max_val - min_val) > ANOMALY_VOLTAGE_DELTA_THRESHOLD:
                anomalies.append({
                    'serial': serial,
                    'channel': row.get('Channel', 'N/A'),
                    'type': 'Large Delta',
                    'severity': 'Medium',
                    'message': f'Voltage range {min_val:.1f}V - {max_val:.1f}V exceeds {ANOMALY_VOLTAGE_DELTA_THRESHOLD}V threshold'
                })
        
        # Inconsistent test results
        status_cols = [col for col in results.columns if col.startswith('Status(')]
        if len(status_cols) > 1:
            statuses = [row[col] for col in status_cols if pd.notna(row[col])]
            if len(statuses) > 1:
                if any('PASS' in str(s) for s in statuses) and any('F' in str(s) for s in statuses):
                    anomalies.append({
                        'serial': serial,
                        'channel': row.get('Channel', 'N/A'),
                        'type': 'Inconsistent Tests',
                        'severity': 'Medium',
                        'message': f'Test results vary significantly: {", ".join(statuses)}'
                    })
    
    return anomalies

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_historical_jobs(df, current_job, num_jobs=MAX_JOB_HISTORY):
    """Get ALL available jobs from database for aggregation by whole number prefix."""
    historical_data = []
    
    try:
        # Extract ALL unique jobs from database
        unique_jobs = df['Job #'].unique()
        
        # Process each unique job
        for job_id in unique_jobs:
            try:
                job_data = get_job_data(df, job_id)
                
                if len(job_data) > 0:
                    job_data = calculate_metrics(job_data)
                    results = determine_pass_fail(job_data, 'Standard')
                    
                    # Calculate stats
                    total = len(results)
                    passed = len(results[results['Pass/Fail'].isin(['PASS', 'OT-', 'TT', 'OT+'])])
                    failed = len(results[results['Pass/Fail'].isin(['FL', 'FH'])])
                    counted = passed + failed
                    
                    pass_pct = (passed / counted * 100) if counted > 0 else 0
                    fail_pct = (failed / counted * 100) if counted > 0 else 0
                    
                    historical_data.append({
                        'job': str(job_id),
                        'total': total,
                        'passed': passed,
                        'pass_pct': pass_pct,
                        'failed': failed,
                        'fail_pct': fail_pct,
                        'is_current': str(job_id) == str(current_job)
                    })
            except:
                pass
        
        # Sort by job ID for consistency (oldest first)
        historical_data.sort(key=lambda x: (isinstance(x['job'], str), x['job']))
        
        # Limit to most recent N jobs
        historical_data = historical_data[-num_jobs:]
    
    except:
        pass
    
    return historical_data

def generate_report_summary(info, job_number, df=None):
    """Generate a complete HTML report with proper styling for printing."""
    status_counts = info['status_counts']
    
    # Build HTML report with inline CSS
    report = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sensor Analysis Report - Job {job_number}</title>
    <style>
        @page {{
            margin: 1in;
        }}
        
        body {{
            font-family: Arial, sans-serif;
            padding: 20px;
            max-width: 100%;
            margin: 0 auto;
            color: #000;
            background: #fff;
        }}
        
        h1, h2, h3 {{
            color: #333;
            page-break-after: avoid;
        }}
        
        h1 {{
            font-size: 24px;
            margin-bottom: 10px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        h2 {{
            font-size: 20px;
            margin-top: 30px;
            margin-bottom: 15px;
            color: #667eea;
        }}
        
        h3 {{
            font-size: 16px;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        
        .header-info {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        
        .section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
            page-break-inside: avoid;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-bottom: 20px;
            page-break-inside: avoid;
        }}
        
        th, td {{
            padding: 8px;
            text-align: left;
            border: 1px solid #ddd;
        }}
        
        th {{
            background-color: #f5f5f5;
            font-weight: bold;
            color: #333;
        }}
        
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        .highlight-row {{
            background-color: #fff3cd !important;
            font-weight: bold;
        }}
        
        .no-print {{
            display: none;
        }}
    </style>
</head>
<body>
    <h1>Sensor Analysis Report - Job Summary</h1>
    <p class="header-info">Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="section">
        <div>
            <h2>Job {info['matched_jobs'][0].split('.')[0]} Analysis</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Job Number</td>
                    <td>{job_number}</td>
                </tr>
                <tr>
                    <td>Total Sensors</td>
                    <td>{info['total_sensors']}</td>
                </tr>
                <tr>
                    <td>Sensors Passed</td>
                    <td>{info['passed_sensors']} ({info['pass_rate']:.1f}%)</td>
                </tr>
                <tr>
                    <td>Sensors Failed</td>
                    <td>{info['failed_sensors']} ({info['fail_rate']:.1f}%)</td>
                </tr>
                <tr>
                    <td>Data Missing</td>
                    <td>{info['dm_sensors']}</td>
                </tr>
                <tr>
                    <td>Threshold Set</td>
                    <td>{info['threshold_set']}</td>
                </tr>
            </table>
        </div>
        
        <div>
            <h2>Status Breakdown</h2>
            <table>
                <tr>
                    <th>Status Code</th>
                    <th>Count</th>
                    <th>Percentage</th>
                </tr>
"""
    
    # Add status rows
    for status in ['PASS', 'FL', 'FH', 'OT-', 'TT', 'OT+', 'DM']:
        count = status_counts.get(status, 0)
        if count > 0:
            pct = (count / info['total_sensors'] * 100)
            report += f"""                <tr>
                    <td>{status}</td>
                    <td>{count}</td>
                    <td>{pct:.1f}%</td>
                </tr>
"""
    
    report += """            </table>
        </div>
    </div>
    
    <h2>Job Analysis Comparison</h2>
    <table>
        <tr>
            <th>Job Number</th>
            <th>Total Sensors</th>
            <th>Passed Qty</th>
            <th>Passed %</th>
            <th>Failed Qty</th>
            <th>Failed %</th>
        </tr>
"""
    
    # Add historical job comparison
    if df is not None and len(df) > 0:
        historical = get_historical_jobs(df, job_number, num_jobs=MAX_JOB_HISTORY)
        
        if historical and len(historical) > 0:
            # Group jobs by whole number prefix
            job_groups = {}
            
            for job in historical:
                job_str = str(job['job']).strip()
                try:
                    if '.' in job_str:
                        prefix = job_str.split('.')[0]
                    else:
                        prefix = job_str
                except:
                    prefix = job_str
                
                if prefix not in job_groups:
                    job_groups[prefix] = {'total': 0, 'passed': 0, 'failed': 0}
                
                job_groups[prefix]['total'] += job['total']
                job_groups[prefix]['passed'] += job['passed']
                job_groups[prefix]['failed'] += job['failed']
            
            totals = {'total': 0, 'passed': 0, 'failed': 0}
            sorted_prefixes = sorted(job_groups.keys(), key=lambda x: (not x.replace('.','').isdigit(), x.replace('.','').zfill(10) if x.replace('.','').isdigit() else x))
            
            for prefix in sorted_prefixes:
                group = job_groups[prefix]
                passed_pct = (group['passed'] / group['total'] * 100) if group['total'] > 0 else 0
                failed_pct = 100 - passed_pct
                
                # Highlight current job
                row_class = ' class="highlight-row"' if prefix == str(job_number).split('.')[0] else ''
                
                report += f"""        <tr{row_class}>
            <td>{prefix}</td>
            <td>{group['total']}</td>
            <td>{group['passed']}</td>
            <td>{passed_pct:.2f}%</td>
            <td>{group['failed']}</td>
            <td>{failed_pct:.2f}%</td>
        </tr>
"""
                totals['total'] += group['total']
                totals['passed'] += group['passed']
                totals['failed'] += group['failed']
            
            # Add average row
            if len(job_groups) > 1:
                avg_pass_pct = (totals['passed'] / totals['total'] * 100) if totals['total'] > 0 else 0
                avg_fail_pct = 100 - avg_pass_pct
                report += f"""        <tr style="border-top: 2px solid #333; font-weight: bold;">
            <td>Average:</td>
            <td>{totals['total']/len(job_groups):.0f}</td>
            <td>{totals['passed']/len(job_groups):.0f}</td>
            <td>{avg_pass_pct:.2f}%</td>
            <td>{totals['failed']/len(job_groups):.0f}</td>
            <td>{avg_fail_pct:.2f}%</td>
        </tr>
"""
    
    report += """    </table>
</body>
</html>
"""
    
    return report

def create_enhanced_plot(df, job_number, threshold_set='Standard'):
    """Generate enhanced visualization for a specific job with dark mode compatibility."""
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
    
    # Set style for better visibility
    plt.style.use('dark_background' if st.get_option('theme.base') == 'dark' else 'default')
    
    # Create figure with subplots using context manager
    fig = plt.figure(figsize=PLOT_FIGURE_SIZE, facecolor='#1a1a1a' if st.get_option('theme.base') == 'dark' else 'white')
    ax1, ax2 = fig.subplots(1, 2)
    
    # Set background colors based on theme
    for ax in [ax1, ax2]:
        ax.set_facecolor('#2d2d2d' if st.get_option('theme.base') == 'dark' else '#f8f9fa')
    
    # Main trend plot (left) with vibrant colors
    ax1.fill_between(df_plot['time'], df_plot['p5'], df_plot['p95'],
                     alpha=0.2, color='#7c8bff', label='5th-95th Percentile')
    ax1.fill_between(df_plot['time'], df_plot['p25'], df_plot['p75'],
                     alpha=0.3, color='#9b67d6', label='25th-75th Percentile')
    ax1.fill_between(df_plot['time'], df_plot['mean'] - df_plot['std'],
                     df_plot['mean'] + df_plot['std'],
                     alpha=0.4, color='#667eea', label='±1 Std Dev')
    
    # Mean line with markers
    ax1.plot(df_plot['time'], df_plot['mean'], 'o-', color='#00ff88', 
             linewidth=3, markersize=8, label='Mean', zorder=10,
             markeredgecolor='white', markeredgewidth=1)
    
    # Add threshold lines
    ax1.axhline(y=thresholds['min_120s'], color='#ff4444', linestyle='--', 
                alpha=0.7, linewidth=2, label=f'Min Threshold ({thresholds["min_120s"]}V)')
    ax1.axhline(y=thresholds['max_120s'], color='#ff4444', linestyle='--', 
                alpha=0.7, linewidth=2, label=f'Max Threshold ({thresholds["max_120s"]}V)')
    
    # Formatting
    ax1.set_title('Sensor Readings Over Time', fontsize=14, fontweight='bold', pad=20, 
                  color='white' if st.get_option('theme.base') == 'dark' else 'black')
    ax1.set_xlabel('Time (seconds)', fontsize=12)
    ax1.set_ylabel('Voltage (V)', fontsize=12)
    ax1.set_ylim(PLOT_VOLTAGE_LIMITS)
    ax1.set_xlim(-5, 125)
    ax1.grid(True, alpha=0.3, linestyle='--', color='#4a4a4a' if st.get_option('theme.base') == 'dark' else '#cccccc')
    ax1.legend(loc='best', framealpha=0.9, facecolor='#2d2d2d' if st.get_option('theme.base') == 'dark' else 'white')
    
    # Box plot for 120s readings (right)
    if '120' in job_data.columns:
        readings_120 = job_data['120'].dropna()
        bp = ax2.boxplot([readings_120], vert=True, patch_artist=True,
                         widths=0.6, showmeans=True, meanline=True)
        
        # Style the boxplot with vibrant colors
        for patch in bp['boxes']:
            patch.set_facecolor('#7c8bff')
            patch.set_alpha(0.8)
            patch.set_edgecolor('white')
            patch.set_linewidth(1.5)
        
        # Style whiskers and caps
        for item in ['whiskers', 'caps']:
            plt.setp(bp[item], color='white', linewidth=1.5)
        
        # Style medians
        plt.setp(bp['medians'], color='#00ff88', linewidth=2)
        
        # Add threshold regions
        ax2.axhspan(0, thresholds['min_120s'], alpha=0.2, color='#ff4444', label='Fail Low')
        ax2.axhspan(thresholds['max_120s'], 5, alpha=0.2, color='#ff4444', label='Fail High')
        ax2.axhspan(thresholds['min_120s'], thresholds['max_120s'], alpha=0.2, 
                   color='#00ff88', label='Pass Range')
        
        ax2.set_title('120s Reading Distribution', fontsize=14, fontweight='bold', pad=20,
                     color='white' if st.get_option('theme.base') == 'dark' else 'black')
        ax2.set_ylabel('Voltage (V)', fontsize=12)
        ax2.set_ylim(PLOT_VOLTAGE_LIMITS)
        ax2.set_xticklabels(['120s'])
        ax2.grid(True, alpha=0.3, axis='y', linestyle='--', 
                color='#4a4a4a' if st.get_option('theme.base') == 'dark' else '#cccccc')
        ax2.legend(loc='upper right', framealpha=0.9, 
                  facecolor='#2d2d2d' if st.get_option('theme.base') == 'dark' else 'white')
    
    plt.suptitle(f'Job {matched_jobs[0].split(".")[0]} Analysis', 
                fontsize=16, fontweight='bold', y=1.02,
                color='white' if st.get_option('theme.base') == 'dark' else 'black')
    plt.tight_layout()
    
    return fig

def create_status_flowchart():
    """Generate the status determination logic flowchart."""
    # Color scheme
    color_start = '#667eea'
    color_process = '#4ECDC4'
    color_decision = '#FFD93D'
    color_result = '#FF6B6B'
    color_final = '#95E1D3'
    
    def draw_box(ax, x, y, width, height, text, color, fontsize=10, bold=False):
        """Draw a rounded rectangle with text"""
        from matplotlib.patches import FancyBboxPatch
        box = FancyBboxPatch((x, y), width, height, 
                              boxstyle="round,pad=0.1", 
                              edgecolor='black', 
                              facecolor=color, 
                              linewidth=2)
        ax.add_patch(box)
        weight = 'bold' if bold else 'normal'
        ax.text(x + width/2, y + height/2, text, 
                ha='center', va='center', 
                fontsize=fontsize, weight=weight,
                wrap=True)
    
    def draw_arrow(ax, x1, y1, x2, y2):
        """Draw an arrow between two points"""
        from matplotlib.patches import FancyArrowPatch
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                               arrowstyle='->', 
                               mutation_scale=20, 
                               linewidth=2,
                               color='black')
        ax.add_patch(arrow)
    
    def draw_label(ax, x, y, text, fontsize=9):
        """Draw a label at a specific position"""
        ax.text(x, y, text, fontsize=fontsize, style='italic', 
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='none', alpha=0.8))
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(14, 20))
    ax.set_xlim(0, 10)
    ax.set_ylim(-2, 21)
    ax.axis('off')
    
    # Title
    ax.text(5, 20, 'Sensor Status Determination Logic', 
            ha='center', fontsize=16, weight='bold')
    
    # Start
    draw_box(ax, 3.5, 18.5, 3, 0.8, 'START\n(Per Serial Number)', color_start, fontsize=11, bold=True)
    draw_arrow(ax, 5, 18.5, 5, 17.8)
    
    # Step 1
    draw_box(ax, 2.5, 17, 5, 0.7, 'Collect all 120s readings\nfrom all tests', color_process, fontsize=9)
    draw_arrow(ax, 5, 17, 5, 16.3)
    
    # Step 2
    draw_box(ax, 2.5, 15.5, 5, 0.7, 'Calculate std_dev_120\nacross all tests', color_process, fontsize=9)
    draw_arrow(ax, 5, 15.5, 5, 14.8)
    
    # Step 3
    draw_box(ax, 2, 14, 6, 0.7, 'FOR EACH TEST (T1, T2, T3...)', color_start, fontsize=10, bold=True)
    draw_arrow(ax, 5, 14, 5, 13.3)
    
    # Check 1
    draw_box(ax, 2.5, 12.5, 5, 0.7, '120s reading < 1.5V?', color_decision, fontsize=9)
    draw_arrow(ax, 2.5, 12.85, 1.5, 12.85)
    draw_label(ax, 2.0, 13.05, 'YES', fontsize=8)
    draw_box(ax, 0.3, 12.5, 1.1, 0.4, 'Add FL', color_result, fontsize=8)
    draw_arrow(ax, 5, 12.5, 5, 11.8)
    draw_label(ax, 5.3, 12.15, 'NO', fontsize=8)
    
    # Check 2
    draw_box(ax, 2.5, 11.0, 5, 0.7, '120s reading > 4.9V?', color_decision, fontsize=9)
    draw_arrow(ax, 2.5, 11.35, 1.5, 11.35)
    draw_label(ax, 2.0, 11.55, 'YES', fontsize=8)
    draw_box(ax, 0.3, 11.0, 1.1, 0.4, 'Add FH', color_result, fontsize=8)
    draw_arrow(ax, 5, 11.0, 5, 10.3)
    draw_label(ax, 5.3, 10.65, 'NO', fontsize=8)
    
    # Check 3
    draw_box(ax, 2.5, 9.5, 5, 0.7, '120s reading missing?', color_decision, fontsize=9)
    draw_arrow(ax, 2.5, 9.85, 1.5, 9.85)
    draw_label(ax, 2.0, 10.05, 'YES', fontsize=8)
    draw_box(ax, 0.3, 9.5, 1.1, 0.4, 'Add DM', color_result, fontsize=8)
    draw_arrow(ax, 5, 9.5, 5, 8.8)
    
    # Step 4
    draw_box(ax, 2.5, 8, 5, 0.7, 'Calculate % Change:\n(120s - 90s) / (90s - 0s) × 100', color_process, fontsize=8)
    draw_arrow(ax, 5, 8, 5, 7.3)
    
    # Check 4
    draw_box(ax, 2.5, 6.5, 5, 0.7, '% Change < -6%?', color_decision, fontsize=9)
    draw_arrow(ax, 2.5, 6.85, 1.5, 6.85)
    draw_label(ax, 2.0, 7.05, 'YES', fontsize=8)
    draw_box(ax, 0.3, 6.5, 1.1, 0.4, 'Add OT-', color_result, fontsize=8)
    draw_arrow(ax, 5, 6.5, 5, 5.8)
    draw_label(ax, 5.3, 6.15, 'NO', fontsize=8)
    
    # Check 5
    draw_box(ax, 2.5, 5.0, 5, 0.7, '% Change > 30%?', color_decision, fontsize=9)
    draw_arrow(ax, 2.5, 5.35, 1.5, 5.35)
    draw_label(ax, 2.0, 5.55, 'YES', fontsize=8)
    draw_box(ax, 0.3, 5.0, 1.1, 0.4, 'Add OT+', color_result, fontsize=8)
    draw_arrow(ax, 5, 5.0, 5, 4.3)
    
    # End of test loop
    draw_box(ax, 2.5, 3.5, 5, 0.7, 'Collect all failure codes\nfrom this test', color_process, fontsize=9)
    draw_arrow(ax, 5, 3.5, 5, 2.8)
    
    # Loop back arrow
    loop_x = 8.2
    ax.plot([loop_x, loop_x], [3.85, 13.35], 'k-', linewidth=2)
    ax.plot([loop_x, 7.9], [13.35, 13.35], 'k-', linewidth=2)
    ax.plot([loop_x, 7.9], [3.85, 3.85], 'k-', linewidth=2)
    ax.annotate('', xy=(7.9, 13.35), xytext=(loop_x, 13.35),
                arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    ax.text(8.7, 8.6, 'LOOP\nBACK', ha='center', fontsize=8, style='italic')
    
    # Step 5
    draw_box(ax, 2.5, 2.0, 5, 0.7, 'std_dev_120 > 0.3V?', color_decision, fontsize=9)
    draw_arrow(ax, 2.5, 2.35, 1.5, 2.35)
    draw_label(ax, 2.0, 2.55, 'YES', fontsize=8)
    draw_box(ax, 0.3, 2.0, 1.1, 0.4, 'Add TT', color_result, fontsize=8)
    draw_arrow(ax, 5, 2.0, 5, 1.3)
    
    # Step 6
    draw_box(ax, 2, 0.5, 6, 0.7, 'Sort all failure codes by priority:\nFL > FH > OT- > TT > OT+ > DM > PASS', color_process, fontsize=8)
    draw_arrow(ax, 5, 0.5, 5, -0.2)
    
    # Final result
    draw_box(ax, 3, -1.0, 4, 0.7, 'Pass/Fail = Highest Priority Code', color_final, fontsize=10, bold=True)
    
    # Legend
    legend_elements = [
        mpatches.Patch(color=color_start, label='Start/Loop'),
        mpatches.Patch(color=color_process, label='Process'),
        mpatches.Patch(color=color_decision, label='Decision'),
        mpatches.Patch(color=color_result, label='Status Code'),
        mpatches.Patch(color=color_final, label='Final Result')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
    
    # Example box
    example_text = """Example (Standard Thresholds):
Test 1: 120s=1.2V (FL), %Chg=5%
Test 2: 120s=1.8V, %Chg=35% (OT+)
Test 3: 120s=1.5V, %Chg=8%
std_dev=0.35V (TT triggered)

Codes: FL, OT+, TT
Result: FL (highest priority)"""
    
    draw_box(ax, 0.2, -1.8, 2.5, 2.5, example_text, '#E8F5E9', fontsize=12)
    
    plt.tight_layout()
    
    return fig

def color_rows(row):
    """Apply background color to table rows based on Pass/Fail status."""
    if row['Pass/Fail'] in ['FL', 'FH']:
        return ['background-color: #fee2e2; color: #991b1b; font-weight: 600'] * len(row)
    elif row['Pass/Fail'] == 'PASS':
        return ['background-color: #d1fae5; color: #065f46; font-weight: 600'] * len(row)
    elif row['Pass/Fail'] in ['OT-', 'TT', 'OT+']:
        return ['background-color: #fed7aa; color: #92400e; font-weight: 600'] * len(row)
    elif row['Pass/Fail'] == 'DM':
        return ['background-color: #e5e7eb; color: #1f2937; font-weight: 600'] * len(row)
    return [''] * len(row)

def analyze_job(df, job_number, threshold_set='Standard'):
    """Analyze data for a specific job number with progress tracking."""
    if len(df) == 0:
        st.error("No data loaded. Please load data first.")
        return None

    if 'Job #' not in df.columns:
        st.error("Error: Job # column not found in data")
        return None

    # Progress indicator
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Loading job data...")
        progress_bar.progress(10)
        
        job_data = get_job_data(df, job_number)

        if len(job_data) == 0:
            st.error(f"No data found for Job # {job_number}")
            unique_jobs = df['Job #'].unique()
            st.write("Available Job Numbers in database:")
            st.write(sorted(unique_jobs)[:20])
            return None

        matched_jobs = sorted(job_data['Job #'].unique())
        thresholds = THRESHOLDS[threshold_set]

        status_text.text("Calculating metrics...")
        progress_bar.progress(30)
        
        # Calculate metrics
        job_data = calculate_metrics(job_data)

        status_text.text("Determining pass/fail status...")
        progress_bar.progress(60)
        
        # Determine Pass/Fail
        results = determine_pass_fail(job_data, threshold_set)

        status_text.text("Calculating statistics...")
        progress_bar.progress(80)
        
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

        progress_bar.progress(100)
        status_text.text("Analysis complete!")
        time.sleep(0.3)
        
        # Clear progress indicators
        status_text.empty()
        progress_bar.empty()
        
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
        
    except Exception as e:
        st.error(f"❌ Error during analysis: {str(e)}")
        progress_bar.empty()
        status_text.empty()
        return None

# ==================== MAIN APP ====================

# Show tutorial dialog at the top if active
if tutorial.should_show_tutorial() and not st.session_state.tutorial_state.get('dismissed', False):
    tutorial.start_tutorial()

if st.session_state.tutorial_state['active']:
    tutorial.render_tutorial_dialog()
    st.markdown("---")

# Main app header
st.markdown("""
<div class="main-header">
    <h1 style="color: white; margin: 0;">🔬 Sensor Analysis Dashboard v2.2</h1>
    <p style="color: rgba(255,255,255,0.9); margin-top: 0.5rem; font-size: 1.1rem;">
        Advanced sensor data analysis with optimized performance
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
if 'job_history' not in st.session_state:
    st.session_state.job_history = []
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

# Sidebar for data loading
with st.sidebar:
    st.markdown("### 📁 Data Source")
    
    data_source = st.radio(
        "Select input method:",
        ["📤 Upload CSV", "💾 Use Database"],
        label_visibility="collapsed"
    )
    
    df = st.session_state.df
    
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
                    st.session_state.df = df
    else:
        if st.button("🔄 Load Database", use_container_width=True):
            with st.spinner("Connecting to database..."):
                df = load_data_from_db('sensor_data.db')
                if len(df) > 0:
                    st.session_state.df = df
    
    if len(df) > 0:
        st.markdown("---")
        st.markdown("### ⚙️ Analysis Settings")
        
        with st.form(key="analysis_form"):
            job_number_raw = st.text_input(
                "Job Number:",
                placeholder="Enter job number...",
                help="Enter the job number to analyze. Supports prefix matching (e.g., '258' matches '258.1', '258.2')"
            )
            
            threshold_set = st.radio(
                "Threshold Set:",
                ["Standard", "High Range"],
                help="Standard: Typical voltage range analysis. High Range: Extended voltage analysis"
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
        
        # Job History
        if len(st.session_state.job_history) > 0:
            st.markdown("---")
            st.markdown("### 📜 Recent Jobs")
            for idx, recent_job in enumerate(st.session_state.job_history):
                if st.button(f"🔄 Job {recent_job}", key=f"hist_{idx}", use_container_width=True):
                    analysis_info = analyze_job(df, recent_job, threshold_set)
                    if analysis_info:
                        st.session_state.analysis_results = analysis_info
                        st.session_state.current_job = recent_job
                        st.session_state.current_threshold = threshold_set
                        st.rerun()
    
    # Tutorial & Help in sidebar
    st.markdown("---")
    tutorial.render_help_sidebar()

# Main content area
if len(df) > 0:
    # Process analysis if submitted with validation
    if submit_button and job_number_raw:
        job_number, error = validate_job_number(job_number_raw)
        if error:
            st.error(f"❌ {error}")
        elif job_number:
            with st.spinner("Analyzing data..."):
                analysis_info = analyze_job(df, job_number, threshold_set)
                if analysis_info:
                    st.session_state.analysis_results = analysis_info
                    st.session_state.current_job = job_number
                    st.session_state.current_threshold = threshold_set
                    
                    # Update job history
                    if job_number not in st.session_state.job_history:
                        st.session_state.job_history.insert(0, job_number)
                        st.session_state.job_history = st.session_state.job_history[:5]
                else:
                    # Clear previous results if job not found
                    st.session_state.analysis_results = None
                    st.session_state.current_job = None
    elif submit_button:
        st.warning("⚠️ Please enter a job number.")
    
    # Handle export button - provide immediate download
    if export_button and st.session_state.analysis_results is not None:
        info = st.session_state.analysis_results
        export_df = info['results'].copy()
        csv = export_df.to_csv(index=False)
        
        st.success(f"✅ Ready to download {len(export_df)} sensor records")
        st.download_button(
            label="📥 Download Results CSV",
            data=csv,
            file_name=f"job_{st.session_state.current_job}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="download_csv_export",
            use_container_width=True
        )
    elif export_button and st.session_state.analysis_results is None:
        st.warning("⚠️ Please analyze a job first before exporting.")
    
    # Display results if available
    if st.session_state.analysis_results:
        info = st.session_state.analysis_results
        
        # Anomaly Detection
        anomalies = detect_anomalies(info['results'], info['thresholds'])
        if anomalies:
            with st.expander(f"⚠️ Anomalies Detected ({len(anomalies)})", expanded=False):
                high_severity = [a for a in anomalies if a['severity'] == 'High']
                medium_severity = [a for a in anomalies if a['severity'] == 'Medium']
                
                if high_severity:
                    st.markdown("### 🔴 High Variability")
                    for anomaly in high_severity:
                        st.markdown(f"""
                        <div class="anomaly-high">
                            <strong>{anomaly['serial']}</strong> (Channel: {anomaly['channel']}) — {anomaly['type']} — {anomaly['message']}
                        </div>
                        """, unsafe_allow_html=True)
                
                if medium_severity:
                    st.markdown("### 🟡 Medium Variability")
                    for anomaly in medium_severity:
                        st.markdown(f"""
                        <div class="anomaly-medium">
                            <strong>{anomaly['serial']}</strong> (Channel: {anomaly['channel']}) — {anomaly['type']} — {anomaly['message']}
                        </div>
                        """, unsafe_allow_html=True)
        
        # Quick Summary Cards
        st.markdown("### 📊 Quick Summary")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="Total Sensors",
                value=f"{info['total_sensors']:,}",
                delta=None,
                help="Total number of unique sensors in this job"
            )
        
        with col2:
            st.metric(
                label="Pass Rate",
                value=f"{info['pass_rate']:.1f}%",
                delta=f"{info['passed_sensors']} passed",
                help="Percentage of sensors that passed (includes PASS, OT-, TT, OT+)"
            )
        
        with col3:
            st.metric(
                label="Fail Rate",
                value=f"{info['fail_rate']:.1f}%",
                delta=f"{info['failed_sensors']} failed",
                help="Percentage of sensors that failed (FL, FH only)"
            )
        
        with col4:
            st.metric(
                label="Data Missing",
                value=f"{info['dm_sensors']}",
                delta="Not counted",
                help="Number of sensors with missing readings (not included in pass/fail calculation)"
            )
        
        with col5:
            st.metric(
                label="Job(s)",
                value=len(info['matched_jobs']),
                delta=info['matched_jobs'][0].split('.')[0],
                help="Number of matching job records found"
            )
        
        st.markdown("---")
        
        # Quick Reports
        st.markdown("### 📋 Quick Reports")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Generate Summary Report", use_container_width=True, key="report_summary"):
                # Display report in expander for printing
                with st.expander("📄 Report (Use Browser Print)", expanded=True):
                    # Display title and date
                    st.markdown(f"## Sensor Analysis Report - Job Summary")
                    st.markdown(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    st.markdown("")
                    
                    # Side-by-side columns
                    col_left, col_right = st.columns(2)
                    
                    with col_left:
                        st.markdown(f"### Job {info['matched_jobs'][0].split('.')[0]} Analysis")
                        left_data = {
                            'Metric': ['Job Number', 'Total Sensors', 'Sensors Passed', 'Sensors Failed', 'Data Missing', 'Threshold Set'],
                            'Value': [
                                str(st.session_state.current_job),
                                str(info['total_sensors']),
                                f"{info['passed_sensors']} ({info['pass_rate']:.1f}%)",
                                f"{info['failed_sensors']} ({info['fail_rate']:.1f}%)",
                                str(info['dm_sensors']),
                                info['threshold_set']
                            ]
                        }
                        st.dataframe(pd.DataFrame(left_data), use_container_width=True, hide_index=True)
                    
                    with col_right:
                        st.markdown("### Status Breakdown")
                        status_counts = info['status_counts']
                        right_data = {'Status Code': [], 'Count': [], 'Percentage': []}
                        
                        for status in ['PASS', 'FL', 'FH', 'OT-', 'TT', 'OT+', 'DM']:
                            count = status_counts.get(status, 0)
                            if count > 0:
                                right_data['Status Code'].append(status)
                                right_data['Count'].append(count)
                                right_data['Percentage'].append(f"{(count / info['total_sensors'] * 100):.1f}%")
                        
                        st.dataframe(pd.DataFrame(right_data), use_container_width=True, hide_index=True)
                    
                    st.markdown("")
                    st.markdown("### Job Analysis Comparison")
                    
                    # Get historical jobs
                    historical = get_historical_jobs(df, st.session_state.current_job, num_jobs=MAX_JOB_HISTORY)
                    
                    if historical and len(historical) > 0:
                        # Group jobs by whole number prefix
                        job_groups = {}
                        
                        for job in historical:
                            # Extract whole number prefix
                            job_str = str(job['job']).strip()
                            try:
                                # For jobs like "267.1", get "267"
                                if '.' in job_str:
                                    prefix = job_str.split('.')[0]
                                else:
                                    prefix = job_str
                            except:
                                prefix = job_str
                            
                            # Group by prefix
                            if prefix not in job_groups:
                                job_groups[prefix] = {
                                    'total': 0,
                                    'passed': 0,
                                    'failed': 0
                                }
                            
                            job_groups[prefix]['total'] += job['total']
                            job_groups[prefix]['passed'] += job['passed']
                            job_groups[prefix]['failed'] += job['failed']
                        
                        # Build comparison table
                        comparison_data = {
                            'Job Number': [],
                            'Total Sensors': [],
                            'Passed Qty': [],
                            'Passed %': [],
                            'Failed Qty': [],
                            'Failed %': []
                        }
                        
                        totals = {'total': 0, 'passed': 0, 'failed': 0}
                        
                        # Sort job groups (numeric first, then non-numeric)
                        sorted_prefixes = sorted(job_groups.keys(), key=lambda x: (not x.replace('.','').isdigit(), x.replace('.','').zfill(10) if x.replace('.','').isdigit() else x))
                        
                        for prefix in sorted_prefixes:
                            group = job_groups[prefix]
                            passed_pct = (group['passed'] / group['total'] * 100) if group['total'] > 0 else 0
                            failed_pct = 100 - passed_pct
                            
                            comparison_data['Job Number'].append(prefix)
                            comparison_data['Total Sensors'].append(group['total'])
                            comparison_data['Passed Qty'].append(group['passed'])
                            comparison_data['Passed %'].append(f"{passed_pct:.2f}%")
                            comparison_data['Failed Qty'].append(group['failed'])
                            comparison_data['Failed %'].append(f"{failed_pct:.2f}%")
                            
                            totals['total'] += group['total']
                            totals['passed'] += group['passed']
                            totals['failed'] += group['failed']
                        
                        # Add average row
                        if len(job_groups) > 1:
                            avg_pass_pct = (totals['passed'] / totals['total'] * 100) if totals['total'] > 0 else 0
                            avg_fail_pct = 100 - avg_pass_pct
                            comparison_data['Job Number'].append('Average:')
                            comparison_data['Total Sensors'].append(int(totals['total']/len(job_groups)))
                            comparison_data['Passed Qty'].append(int(totals['passed']/len(job_groups)))
                            comparison_data['Passed %'].append(f"{avg_pass_pct:.2f}%")
                            comparison_data['Failed Qty'].append(int(totals['failed']/len(job_groups)))
                            comparison_data['Failed %'].append(f"{avg_fail_pct:.2f}%")
                        
                        st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)
                    
                    # Print button - Create HTML report and print it
                    st.markdown("")
                    
                    # Generate printable HTML report
                    report_html = generate_report_summary(info, st.session_state.current_job, df)
                    
                    col_print_left, col_print_center, col_print_right = st.columns([1, 2, 1])
                    with col_print_center:
                        # Escape the HTML for JavaScript
                        escaped_html = json.dumps(report_html)
                        
                        components.html(
                            f"""
                            <button onclick="printReport()" style="
                                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                color: white;
                                border: none;
                                padding: 0.7rem 1.8rem;
                                border-radius: 25px;
                                font-weight: bold;
                                cursor: pointer;
                                font-size: 1rem;
                                width: 100%;
                                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                                transition: transform 0.2s;
                            ">
                                🖨️ Print Report (Ctrl+P)
                            </button>
                            <style>
                                button:hover {{
                                    transform: translateY(-2px);
                                    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
                                }}
                            </style>
                            <script>
                                function printReport() {{
                                    var reportContent = {escaped_html};
                                    var printWindow = window.open('', '', 'height=800,width=1000');
                                    printWindow.document.write(reportContent);
                                    printWindow.document.close();
                                    printWindow.focus();
                                    setTimeout(function() {{
                                        printWindow.print();
                                        printWindow.close();
                                    }}, {PRINT_DIALOG_DELAY_MS});
                                }}
                            </script>
                            """,
                            height=60
                        )
        
        with col2:
            if st.button("❌ Failed Sensors Report", use_container_width=True, key="report_failed"):
                failed_sensors = info['results'][info['results']['Pass/Fail'].isin(['FL', 'FH'])]
                
                if len(failed_sensors) > 0:
                    with st.expander("❌ Failed Sensors Report (Use Browser Print)", expanded=True):
                        st.markdown(f"## Failed Sensors Report")
                        st.markdown(f"**Job:** {st.session_state.current_job}")
                        st.markdown(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        st.markdown(f"**Total Failed:** {len(failed_sensors)} sensors")
                        st.markdown("")
                        
                        # Display as table
                        display_cols = ['Serial Number', 'Channel', 'Pass/Fail', '120s(St.Dev.)']
                        display_df = failed_sensors[display_cols].copy()
                        display_df['120s(St.Dev.)'] = display_df['120s(St.Dev.)'].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                        
                        st.markdown("")
                        
                        # Generate HTML for printing
                        failed_report_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Failed Sensors Report - Job {st.session_state.current_job}</title>
    <style>
        @page {{ margin: 1in; }}
        body {{ font-family: Arial, sans-serif; padding: 20px; color: #000; background: #fff; }}
        h1, h2 {{ color: #333; page-break-after: avoid; }}
        h1 {{ font-size: 24px; margin-bottom: 10px; border-bottom: 3px solid #dc2626; padding-bottom: 10px; }}
        .header-info {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 20px; page-break-inside: avoid; }}
        th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
        th {{ background-color: #fee2e2; font-weight: bold; color: #7f1d1d; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>Failed Sensors Report</h1>
    <p class="header-info">Job: {st.session_state.current_job}</p>
    <p class="header-info">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p class="header-info">Total Failed: {len(failed_sensors)} sensors</p>
    
    <table>
        <tr>
            <th>Serial Number</th>
            <th>Channel</th>
            <th>Status</th>
            <th>Std Dev</th>
        </tr>
"""
                        
                        for idx, row in failed_sensors.iterrows():
                            failed_report_html += f"""        <tr>
            <td>{row['Serial Number']}</td>
            <td>{row.get('Channel', 'N/A')}</td>
            <td>{row['Pass/Fail']}</td>
            <td>{row['120s(St.Dev.)']:.3f}</td>
        </tr>
"""
                        
                        failed_report_html += """    </table>
</body>
</html>
"""
                        
                        # Print button
                        col_print_left, col_print_center, col_print_right = st.columns([1, 2, 1])
                        with col_print_center:
                            escaped_html = json.dumps(failed_report_html)
                            
                            components.html(
                                f"""
                                <button onclick="printReport()" style="
                                    background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
                                    color: white;
                                    border: none;
                                    padding: 0.7rem 1.8rem;
                                    border-radius: 25px;
                                    font-weight: bold;
                                    cursor: pointer;
                                    font-size: 1rem;
                                    width: 100%;
                                    box-shadow: 0 4px 15px rgba(220, 38, 38, 0.3);
                                    transition: transform 0.2s;
                                ">
                                    🖨️ Print Failed Sensors Report
                                </button>
                                <style>
                                    button:hover {{
                                        transform: translateY(-2px);
                                        box-shadow: 0 6px 20px rgba(220, 38, 38, 0.4);
                                    }}
                                </style>
                                <script>
                                    function printReport() {{
                                        var reportContent = {escaped_html};
                                        var printWindow = window.open('', '', 'height=800,width=1000');
                                        printWindow.document.write(reportContent);
                                        printWindow.document.close();
                                        printWindow.focus();
                                        setTimeout(function() {{
                                            printWindow.print();
                                            printWindow.close();
                                        }}, {PRINT_DIALOG_DELAY_MS});
                                    }}
                                </script>
                                """,
                                height=60
                            )
                else:
                    st.success("✅ No failed sensors found!")
        
        st.markdown("---")
        
        # Create tabs with Data Table as the first/default tab
        tab_list = ["📋 Data Table", "📈 Visualization", "📊 Status Breakdown", "ℹ️ Thresholds"]
        tabs = st.tabs(tab_list)
        
        # Tab 1: Data Table with simple filters
        with tabs[0]:
            st.markdown("#### 🔍 Filters")
            
            # Get unique Pass/Fail statuses
            all_statuses = sorted(info['results']['Pass/Fail'].unique().tolist())
            
            # Create simple filter columns without complex state management
            col1, col2 = st.columns([3, 3])
            
            # Initialize session state for serial filter if not exists
            if 'serial_filter' not in st.session_state:
                st.session_state.serial_filter = ""
            
            with col1:
                selected_statuses = st.pills(
                    "Select Status:",
                    options=all_statuses,
                    default=all_statuses,
                    selection_mode="multi",
                    help="Filter table by status codes. PASS includes OT-, TT, OT+ statuses."
                )
            
            with col2:
                serial_text = st.text_input(
                    "Serial Number(s):",
                    value=st.session_state.serial_filter,
                    placeholder="Enter serial numbers separated by commas...",
                    help="Filter by serial numbers. Supports partial matching. Updates automatically as you type!",
                    key="serial_filter_input",
                    on_change=lambda: None  # Triggers rerun on every keystroke
                )
                # Update session state
                st.session_state.serial_filter = serial_text
            
            st.caption("💡 Filters apply automatically. Remove status pills or clear text to reset.")
            
            # Apply filters
            filtered_data = info['results'].copy()
            
            if selected_statuses:
                filtered_data = filtered_data[filtered_data['Pass/Fail'].isin(selected_statuses)]
            else:
                filtered_data = pd.DataFrame(columns=filtered_data.columns)
            
            if serial_text:
                serials = [s.strip() for s in serial_text.split(',') if s.strip()]
                if serials:
                    pattern = '|'.join([re.escape(s) for s in serials])
                    mask = filtered_data['Serial Number'].str.contains(pattern, case=False, na=False, regex=True)
                    filtered_data = filtered_data[mask]
            
            st.info(f"Showing {len(filtered_data)} of {len(info['results'])} sensors")
            
            # Format and display data
            display_data = filtered_data.copy()
            if len(display_data) > 0:
                for col in display_data.columns:
                    if col.startswith('0s(') or col.startswith('90s(') or col.startswith('120s('):
                        display_data[col] = display_data[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
                    elif col == '120s(St.Dev.)':
                        display_data[col] = display_data[col].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
                
                styled_data = display_data.style.apply(color_rows, axis=1)
                
                st.dataframe(
                    styled_data,
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
            else:
                st.warning("No data to display with current filters")
        
        # Tab 2: Visualization with proper cleanup
        with tabs[1]:
            with st.expander("📈 Sensor Trend Analysis", expanded=True):
                fig = create_enhanced_plot(df, st.session_state.current_job, st.session_state.current_threshold)
                if fig:
                    st.pyplot(fig)
                    plt.close(fig)  # Explicit cleanup
            
            # Show individual sensor plots if serial number filter is active
            if st.session_state.get('serial_filter', '').strip():
                serial_text = st.session_state.serial_filter
                serials = [s.strip() for s in serial_text.split(',') if s.strip()]
                
                if serials:
                    with st.expander(f"📊 Individual Sensor Plots ({len(serials)} filter{'s' if len(serials) > 1 else ''})", expanded=True):
                        st.markdown("**Showing detailed readings for filtered sensors:**")
                        
                        # Get filtered data
                        pattern = '|'.join([re.escape(s) for s in serials])
                        filtered_sensors = info['results'][
                            info['results']['Serial Number'].str.contains(pattern, case=False, na=False, regex=True)
                        ]
                        
                        if len(filtered_sensors) == 0:
                            st.warning("No sensors match the filter.")
                        else:
                            # Get job data for these specific sensors
                            job_data = get_job_data(df, st.session_state.current_job)
                            
                            # Create plots for each sensor
                            for idx, (_, sensor_row) in enumerate(filtered_sensors.iterrows()):
                                serial = sensor_row['Serial Number']
                                
                                # Get all test data for this sensor
                                sensor_tests = job_data[job_data['Serial Number'] == serial]
                                
                                if len(sensor_tests) > 0:
                                    # Create subplot
                                    with create_plot(figsize=(12, 4)) as fig:
                                        ax = fig.add_subplot(111)
                                        
                                        # Style based on theme
                                        fig.patch.set_facecolor('#1a1a1a' if st.get_option('theme.base') == 'dark' else 'white')
                                        ax.set_facecolor('#2d2d2d' if st.get_option('theme.base') == 'dark' else '#f8f9fa')
                                        
                                        # Get thresholds
                                        thresholds = info['thresholds']
                                        
                                        # Plot each test for this sensor
                                        colors = ['#667eea', '#764ba2', '#f59e0b', '#10b981', '#ef4444']
                                        for test_idx, (_, test_row) in enumerate(sensor_tests.iterrows()):
                                            time_points = []
                                            readings = []
                                            
                                            for tp in TIME_POINTS:
                                                if tp in test_row and pd.notna(test_row[tp]):
                                                    time_points.append(float(tp))
                                                    readings.append(test_row[tp])
                                            
                                            if len(time_points) > 0:
                                                color = colors[test_idx % len(colors)]
                                                ax.plot(time_points, readings, 'o-', 
                                                       color=color, linewidth=2, markersize=6,
                                                       label=f'Test {test_idx + 1}',
                                                       markeredgecolor='white', markeredgewidth=1)
                                        
                                        # Add threshold lines
                                        ax.axhline(y=thresholds['min_120s'], color='#ff4444', 
                                                  linestyle='--', alpha=0.7, linewidth=2,
                                                  label=f'Min Threshold ({thresholds["min_120s"]}V)')
                                        ax.axhline(y=thresholds['max_120s'], color='#ff4444',
                                                  linestyle='--', alpha=0.7, linewidth=2,
                                                  label=f'Max Threshold ({thresholds["max_120s"]}V)')
                                        
                                        # Formatting
                                        status = sensor_row['Pass/Fail']
                                        status_color = StatusBadge.get_color(status)
                                        
                                        ax.set_title(f'Serial: {serial} - Status: {status}',
                                                   fontsize=14, fontweight='bold', pad=15,
                                                   color=status_color)
                                        ax.set_xlabel('Time (seconds)', fontsize=11)
                                        ax.set_ylabel('Voltage (V)', fontsize=11)
                                        ax.set_ylim(PLOT_VOLTAGE_LIMITS)
                                        ax.grid(True, alpha=0.3, linestyle='--',
                                               color='#4a4a4a' if st.get_option('theme.base') == 'dark' else '#cccccc')
                                        ax.legend(loc='best', framealpha=0.9,
                                                facecolor='#2d2d2d' if st.get_option('theme.base') == 'dark' else 'white',
                                                fontsize=9)
                                        
                                        plt.tight_layout()
                                        st.pyplot(fig)
                                    
                                    # Show test details in compact format
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.caption(f"**Tests:** {len(sensor_tests)}")
                                    with col2:
                                        std_dev = sensor_row['120s(St.Dev.)']
                                        st.caption(f"**Std Dev:** {std_dev:.3f}V")
                                    with col3:
                                        badge_html = StatusBadge.get_html(status)
                                        st.markdown(badge_html, unsafe_allow_html=True)
                                    
                                    if idx < len(filtered_sensors) - 1:
                                        st.markdown("---")
        
        # Tab 3: Status Breakdown
        with tabs[2]:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("#### Status Distribution")
                for status, count in info['status_counts'].items():
                    if count > 0:
                        pct = (count / info['total_sensors'] * 100)
                        badge_html = StatusBadge.get_html(status)
                        st.markdown(f"{badge_html} **{count}** ({pct:.1f}%)", unsafe_allow_html=True)
            
            with col2:
                with create_plot(figsize=(10, 7)) as fig:
                    ax = fig.add_subplot(111)
                    
                    fig.patch.set_facecolor('#1a1a1a' if st.get_option('theme.base') == 'dark' else 'white')
                    ax.set_facecolor('#2d2d2d' if st.get_option('theme.base') == 'dark' else '#f8f9fa')
                    
                    plot_labels = []
                    plot_sizes = []
                    plot_colors = []
                    
                    for status, count in info['status_counts'].items():
                        if count > 0:
                            pct = (count / info['total_sensors'] * 100)
                            plot_labels.append(f"{status} ({count}) {pct:.1f}%")
                            plot_sizes.append(count)
                            plot_colors.append(StatusBadge.get_color(status))
                    
                    if plot_sizes:
                        explode = [0.05 for _ in plot_sizes]
                        
                        wedges, texts = ax.pie(
                            plot_sizes,
                            colors=plot_colors,
                            startangle=90,
                            explode=explode,
                            textprops={'weight': 'bold'}
                        )
                        
                        # Add legend with all info outside pie
                        ax.legend(plot_labels, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1), 
                                 fontsize=10, framealpha=0.95)
                        
                        ax.set_title('Status Distribution', fontsize=16, fontweight='bold', pad=20,
                                   color='white' if st.get_option('theme.base') == 'dark' else 'black')
                        
                        plt.tight_layout()
                        st.pyplot(fig)
        
        # Tab 4: Thresholds
        with tabs[3]:
            with st.expander("⚙️ Threshold Settings", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Threshold Set:** {info['threshold_set']}")
                    st.markdown(f"**120s Voltage Range:** {info['thresholds']['min_120s']} - {info['thresholds']['max_120s']}V")
                    st.markdown(f"**Max Std Dev:** {info['thresholds']['max_std_dev']}V")
                
                with col2:
                    st.markdown(f"**% Change Range:** {info['thresholds']['min_pct_change']}% to {info['thresholds']['max_pct_change']}%")
                    st.markdown(f"**Applied to:** {info['total_sensors']} sensors")
            
            with st.expander("📋 Status Code Reference", expanded=True):
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
            
            with st.expander("🔀 Decision Logic Flowchart", expanded=False):
                st.caption("Visual representation of the status determination process")
                with create_plot(figsize=(14, 20)) as flowchart_fig:
                    flowchart_fig = create_status_flowchart()
                    st.pyplot(flowchart_fig)

else:
    # Welcome screen with tutorial prompt
    st.info("👈 Please load data using the sidebar to begin analysis")
    
    # First-time user tutorial prompt
    if tutorial.should_show_tutorial():
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            color: white;
            margin: 2rem 0;
            text-align: center;
        ">
            <h2 style="color: white; margin: 0 0 1rem 0;">👋 Welcome to Sensor Analysis Dashboard!</h2>
            <p style="font-size: 1.1rem; margin-bottom: 1.5rem;">
                It looks like this is your first time here. Would you like a quick tour?
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🎓 Start Tutorial (3 minutes)", use_container_width=True, type="primary"):
                tutorial.start_tutorial()
                st.rerun()
            if st.button("⏭️ Skip for now", use_container_width=True):
                tutorial.dismiss_tutorial()
                st.rerun()
    
    with st.expander("📖 How to use this tool", expanded=True):
        st.markdown("""
        ### Quick Start Guide
        
        1. **📁 Load your data** using the sidebar (CSV upload or database)
        2. **🔍 Enter a Job Number** to analyze
        3. **⚙️ Select threshold criteria** (Standard or High Range)
        4. **▶️ Click Analyze** to generate results
        5. **📊 Explore the tabs** for different views of your data
        
        ### Key Features
        
        - 📊 **Data Quality Indicator** - See data completeness at a glance
        - ⚠️ **Anomaly Detection** - Automatic alerts for unusual patterns
        - 📄 **One-Click Reports** - Generate and download professional reports
        - 🔀 **Decision Logic** - Understand how pass/fail status is determined
        - 🎓 **Interactive Tutorial** - Learn the system step-by-step
        
        ### Color Coding
        
        - 🟢 **Green** - Passed sensors
        - 🔴 **Red** - Failed sensors (FL/FH)
        - 🟡 **Yellow** - Warnings (OT-/TT/OT+)
        - ⚪ **Gray** - Missing data
        
        **Need help?** Click the **"🎓 Tutorial & Help"** section in the sidebar!
        """)

markdown

\# 🔧 Sensor Data Analysis Tool



A powerful, interactive tool for analyzing sensor data with pass/fail criteria, statistical analysis, and visualization.



\## Features

\- 📊 Interactive data analysis and visualization

\- 🔍 Pass/fail determination based on configurable thresholds

\- 📈 Real-time plotting with Plotly

\- 💾 CSV import/export functionality

\- 🎯 Flexible filtering and search



\## How to Use

1\. Upload your sensor data CSV file

2\. Select threshold set (Standard or High Range)

3\. Enter Job Number to analyze

4\. View results and export as needed



\## CSV Format

Your CSV should include columns:

\- Job # or Job Number

\- Serial Number or Serial#

\- Channel

\- Time points: 0, 5, 15, 30, 60, 90, 120

\- Test # (optional)



\## Running Locally

```bash

pip install -r requirements.txt

streamlit run app.py

```



\## Author

Stephen + Claude ai


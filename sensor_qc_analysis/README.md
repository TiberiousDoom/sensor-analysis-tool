# Sensor Analysis Dashboard v2.1

A standalone, browser-based sensor data analysis tool with pass/fail criteria, statistical analysis, and visualization.

## Features

- Interactive data analysis and visualization
- Pass/fail determination based on configurable thresholds (Standard or High Range)
- Real-time plotting and charts
- CSV import/export functionality
- Flexible filtering and search
- Dark mode support (auto-detects system preference)
- Job Analysis Comparison table
- Summary report generation
- Works entirely offline - no server required

## How to Use

1. Open `Sensor_analysis_v2_1_offline.HTML` in any modern web browser
2. Upload your sensor data CSV file
3. Select threshold set (Standard or High Range)
4. Enter Job Number to analyze
5. View results and export as needed

## CSV Format

Your CSV should include columns:
- Job # or Job Number
- Serial Number or Serial#
- Channel
- Time points: 0, 5, 15, 30, 60, 90, 120
- Test # (optional)

## Requirements

- Any modern web browser (Chrome, Firefox, Safari, Edge)
- No installation or server setup required

## Archive

The `archive/` folder contains the previous Python/Streamlit version of this tool for reference.

## Author

Stephen + Claude AI

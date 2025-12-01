# Sensor Analysis Tool

A collection of browser-based analysis tools for sensor data evaluation, quality control, and statistical analysis.

## Overview

This repository contains three specialized analysis modules for sensor data:

| Module | Status | Description |
|--------|--------|-------------|
| [Sensor QC Analysis](./sensor_qc_analysis/) | **Available** | Pass/fail quality control analysis for sensor voltage readings |
| [EIS Analysis](./EIS_analysis/) | *Coming Soon* | Electrochemical Impedance Spectroscopy analysis |
| [Sensor Statistical Analysis](./sensor_statistical_analysis/) | *Coming Soon* | Advanced statistical analysis and trend detection |

## Sensor QC Analysis

**Status: Available**

A standalone, browser-based tool for evaluating sensor quality with pass/fail criteria based on voltage readings at specific time points (0-120 seconds).

### Key Features
- Pass/fail determination using configurable thresholds (Standard or High Range)
- Support for CSV files and SQLite databases
- Job comparison summary reports (up to 15 jobs)
- Interactive charts and data visualization
- Export to CSV and PDF
- Works entirely offline

### Quick Start
1. Open `sensor_qc_analysis/Sensor-QC-Analysis.HTML` in a web browser
2. Upload your sensor data (CSV or SQLite database)
3. Enter a job number and click "Analyze"

[View full documentation](./sensor_qc_analysis/README.md)

---

## EIS Analysis

**Status: Coming Soon**

Tools for analyzing Electrochemical Impedance Spectroscopy data.

### Planned Features
- EIS data import and parsing
- Impedance analysis and fitting
- Nyquist and Bode plot visualization
- Equivalent circuit modeling

[View documentation](./EIS_analysis/README.md)

---

## Sensor Statistical Analysis

**Status: Coming Soon**

Advanced statistical analysis tools for sensor data.

### Planned Features
- Trend analysis and forecasting
- Batch comparison statistics
- Distribution and normality testing
- Outlier detection algorithms
- Correlation analysis

[View documentation](./sensor_statistical_analysis/README.md)

---

## Requirements

- Any modern web browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- No server or installation required

## Repository Structure

```
sensor-analysis-tool/
├── sensor_qc_analysis/          # QC pass/fail analysis (available)
│   ├── Sensor-QC-Analysis.HTML
│   ├── Excel_Database_Builder.HTML
│   └── README.md
├── EIS_analysis/                # EIS analysis (coming soon)
│   └── README.md
├── sensor_statistical_analysis/ # Statistical analysis (coming soon)
│   └── README.md
└── archive/                     # Legacy Python/Streamlit version
```

## Author

Stephen + Claude AI

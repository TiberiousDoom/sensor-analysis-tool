# Sensor Analysis Tool

A collection of browser-based analysis tools for sensor data evaluation, quality control, and statistical analysis.

## Overview

This repository contains four specialized analysis modules for sensor data:

| Module | Status | Description |
|--------|--------|-------------|
| [EIS Analyzer](./EIS_analysis/) | **Available** | Electrochemical Impedance Spectroscopy analysis with circuit fitting |
| [Statistical Analysis](./sensor_statistical_analysis/) | **Available** | KPI dashboard, regression modeling, and correlation analysis |
| [QC Analysis Dashboard](./sensor_qc_analysis/) | **Available** | Pass/fail quality control analysis for sensor voltage readings |
| [Excel Database Builder](./sensor_qc_analysis/) | **Available** | Convert Excel files to SQLite databases |

## EIS Analyzer

**Status: Available**

A browser-based Electrochemical Impedance Spectroscopy analysis tool with circuit model fitting and visualization.

### Key Features
- Multiple circuit models (Randles, CPE, Warburg, multi-RC)
- Auto-fit to select best model automatically
- Nyquist and Bode plot visualization
- Frequency range filtering
- Export to JSON/CSV, session save/load

### Quick Start
1. Open `EIS_analysis/eis_analyzer.html` in a web browser
2. Upload or paste your EIS data (Frequency, Z', Z")
3. Select a circuit model or use Auto-fit
4. Click "Fit Model" to analyze

[View full documentation](./EIS_analysis/README.md)

---

## Statistical Analysis

**Status: Available**

Advanced statistical analysis tool for sensor response data with KPI calculations and regression modeling.

### Key Features
- KPI dashboard with real-time metrics
- Time series visualization
- Correlation analysis
- Multiple regression models with interpretation
- Support for CSV and Excel files

### Quick Start
1. Open `sensor_statistical_analysis/sensor_statistical_analysis.html` in a web browser
2. Upload Build Data (design parameters) and Sensor Response Data (time series)
3. Explore KPI dashboard, charts, and regression analysis

[View full documentation](./sensor_statistical_analysis/README.md)

---

## QC Analysis Dashboard

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

## Excel Database Builder

**Status: Available**

Utility tool for converting multiple Excel spreadsheets into a SQLite database for use with the QC Analysis tool.

### Quick Start
1. Open `sensor_qc_analysis/Excel_Database_Builder.HTML` in a web browser
2. Upload Excel files with sensor data
3. Export as SQLite database

---

## Requirements

- Any modern web browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- No server or installation required

## Repository Structure

```
sensor-analysis-tool/
├── index.html                   # Landing page with links to all tools
├── EIS_analysis/                # EIS analysis tool
│   ├── eis_analyzer.html
│   └── README.md
├── sensor_statistical_analysis/ # Statistical analysis tool
│   ├── sensor_statistical_analysis.html
│   └── README.md
├── sensor_qc_analysis/          # QC analysis tools
│   ├── Sensor-QC-Analysis.HTML
│   ├── Excel_Database_Builder.HTML
│   └── README.md
└── archive/                     # Legacy Python/Streamlit version
```

## Author

Stephen + Claude AI

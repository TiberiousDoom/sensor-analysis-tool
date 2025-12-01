# Sensor Analysis Dashboard v2.1

A standalone, browser-based sensor data analysis tool for evaluating sensor quality with pass/fail criteria, statistical analysis, and visualization. Designed for analyzing voltage readings from sensors at specific time points to determine quality compliance.

## Features

- **Data Import**: Support for both CSV files and SQLite databases
- **Pass/Fail Determination**: Automated analysis based on configurable voltage thresholds
- **Two Threshold Sets**: Standard and High Range configurations for different sensor types
- **Real-time Visualization**: Interactive charts with Chart.js integration
- **Summary Reports**: Job comparison reports for up to 15 jobs with cumulative statistics
- **Export Options**: Export results to CSV or generate printable PDF reports
- **Job History**: Quick access to recently analyzed jobs (stored in localStorage)
- **Database Persistence**: Auto-saves loaded database to IndexedDB for session restoration
- **Dark Mode**: Automatically adapts to system color scheme preference
- **Fully Offline**: Works entirely in-browser with no server required

## How to Use

1. Open `Sensor-QC-Analysis.HTML` in any modern web browser
2. Load your data:
   - **CSV**: Upload a CSV file with sensor readings
   - **Database**: Upload a SQLite database file (auto-saved for next session)
3. Select threshold set (Standard or High Range)
4. Enter the Job Number to analyze
5. Click "Analyze" to view results
6. Use tabs to navigate between Table, Charts, and Anomalies views
7. Export results or generate summary reports as needed

## Threshold Configurations

### Standard Thresholds
| Parameter | Min | Max |
|-----------|-----|-----|
| 120s Reading | 1.50V | 4.90V |
| Percent Change (90-120s) | -6.00% | 30.00% |
| Standard Deviation | - | 0.30V |

### High Range Thresholds
| Parameter | Min | Max |
|-----------|-----|-----|
| 120s Reading | 0.55V | 1.00V |
| Percent Change (90-120s) | 0.00% | 75.00% |
| Standard Deviation | - | 0.50V |

## Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| **PASS** | Passed | All criteria within acceptable range |
| **FL** | Failed Low | 120s reading below minimum threshold |
| **FH** | Failed High | 120s reading above maximum threshold |
| **FT-** | Failed Percent Change | Percent change below minimum threshold |
| **OT+** | Over Threshold | Percent change above maximum threshold |
| **TT** | Time Trigger | Standard deviation exceeds threshold |
| **DM** | Data Missing | Required data not available |

## Data Format

### CSV Format
Your CSV should include the following columns:
- `Job #` - Job identifier (supports decimal sub-jobs like 258.1, 258.2)
- `Serial Number` - Unique sensor identifier
- `Channel` - Channel designation
- `Test #` - Test number (optional)
- Time point columns: `0`, `5`, `15`, `30`, `60`, `90`, `120` (voltage readings)

### SQLite Database
The database should contain a `sensor_readings` table with equivalent columns.

## Analysis Logic

1. **Data Grouping**: Sensors are grouped by Serial Number
2. **Metrics Calculation**: Percent change calculated as `((V120 - V90) / (V90 - V0)) × 100`
3. **Pass/Fail Determination**:
   - Check 120s reading against min/max thresholds
   - Check percent change against min/max thresholds
   - Check standard deviation across tests
4. **Final Status**: Critical failures (FL, FH, FT-) take priority; if any test passes without critical failures, sensor passes

## Summary Report

The Summary Report feature generates a comparison table for:
- Current job and up to 14 previous jobs (by job number)
- Total sensors, passed/failed counts and percentages per job
- Cumulative totals across all included jobs

## Requirements

- Any modern web browser (Chrome, Firefox, Safari, Edge)
- No installation or server setup required
- JavaScript must be enabled

## Files

- `Sensor-QC-Analysis.HTML` - Main application (single-file, self-contained)
- `Excel_Database_Builder.HTML` - Utility for building SQLite databases from Excel data

## Author

Stephen + Claude AI

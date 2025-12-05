# Sensor Statistical Analysis

A browser-based statistical analysis tool for sensor response data with KPI calculations, time series visualization, correlation analysis, and regression modeling.

## Status

**Available** - Fully functional

## Features

### Data Import
- **Build Data**: Upload design parameters (CSV, XLSX, XLS, TXT)
- **Sensor Response Data**: Upload time series data with time in column A and sensor readings in subsequent columns
- Drag-and-drop file upload
- Automatic sensor matching between datasets

### KPI Dashboard
- Real-time calculation of key performance indicators
- Visual KPI cards with metrics
- Statistical summaries for sensor batches

### Visualization
- **Time Series Charts**: Interactive plots of sensor response over time
- **Correlation Analysis**: Visualize relationships between sensor parameters
- **Distribution Charts**: Analyze data distributions
- All charts powered by Plotly.js for interactivity

### Regression Analysis
- Multiple regression model options
- Variable selection controls
- Statistical results with interpretation
- Model fit quality metrics (R², coefficients, p-values)
- Visual interpretation highlighting (good/moderate/weak correlations)

### Additional Features
- Data preview tables with scrollable view
- Export functionality
- Dark theme interface
- Responsive design for various screen sizes
- Accessibility features (keyboard navigation, screen reader support)
- Tab-based navigation for organized analysis workflow

## How to Use

1. Open `sensor_statistical_analysis.html` in any modern web browser
2. Upload Build Data file (design parameters)
3. Upload Sensor Response Data file (time series readings)
4. Review the sensor matching status
5. Explore KPI dashboard for summary statistics
6. Navigate tabs to view charts, correlation analysis, and regression results
7. Export results as needed

## Data Format

### Build Data
CSV or Excel file containing sensor design parameters with sensor identifiers for matching.

### Sensor Response Data
Time series format with:
- **Column A**: Time values
- **Columns B+**: Sensor readings (one sensor per column)

Column headers should contain sensor identifiers for matching with build data.

## Requirements

- Any modern web browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- No installation or server required

## Related Tools

See the [Sensor QC Analysis](../sensor_qc_analysis/) folder for the voltage-based sensor quality control analysis tool with pass/fail determination.

## Author

Stephen + Claude AI

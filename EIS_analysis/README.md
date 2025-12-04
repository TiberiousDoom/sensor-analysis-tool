# EIS Analyzer

A browser-based Electrochemical Impedance Spectroscopy (EIS) analysis tool with circuit model fitting, visualization, and data export.

## Status

**Available** - Fully functional

## Features

### Data Input
- File upload with drag-and-drop (CSV, TXT, TSV formats)
- Paste data directly with auto-parsing
- Auto-detect data format: Z'/Z" (rectangular) or |Z|/Phase (polar)
- Data table view for verification

### Circuit Models
- **R** - Resistor only
- **R-C** - Series resistor-capacitor
- **R||C** - Parallel resistor-capacitor
- **R-(R||C)** - Randles circuit
- **R-(R||C)-W** - Randles with Warburg diffusion element
- **R-(R||C)-(R||C)** - Two RC time constants
- **R-(R||C)-(R||C)-(R||C)** - Three RC time constants
- **R-(R||CPE)** - Constant Phase Element model
- **R-(R||CPE)-(R||CPE)** - Two CPE model
- **R-(R||CPE)||(R||CPE)** - Parallel CPE model

### Analysis Features
- **Auto-fit**: Automatically selects the best-fitting circuit model
- **Model comparison**: Compare fit quality across all models simultaneously
- **Frequency range filtering**: Limit fitting to specific frequency ranges
- **Fit statistics**: Chi-squared, R², and per-parameter confidence

### Visualization
- **Nyquist plot**: Z' vs -Z" with experimental data and fitted curve
- **Bode plots**: Impedance magnitude and phase angle vs frequency
- **Residual plots**: Real and imaginary fit residuals vs frequency

### Additional Features
- Debug test mode with synthetic data and configurable noise levels
- Session save/load for complete analysis state preservation
- Export results to JSON or CSV
- Responsive design for desktop and mobile
- Accessibility features (keyboard navigation, screen reader support)

## How to Use

1. Open `eis_analyzer.html` in any modern web browser
2. Upload or paste your EIS data (Frequency, Z'/|Z|, Z"/Phase)
3. Select a circuit model or use "Auto (Best Fit)"
4. Click "Fit Model" to perform the analysis
5. Review results in Nyquist and Bode plots
6. Export results or save session as needed

## Data Format

Your data should contain three columns:
- **Column 1**: Frequency (Hz)
- **Column 2**: Z' (real impedance, Ω) or |Z| (magnitude, Ω)
- **Column 3**: Z" (imaginary impedance, Ω) or Phase (degrees)

Format is auto-detected based on data characteristics.

## Requirements

- Any modern web browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- No installation or server required

## Related Tools

See the [Sensor QC Analysis](../sensor_qc_analysis/) folder for the voltage-based sensor quality control analysis tool.

## Author

Stephen + Claude AI

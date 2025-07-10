# OSRM Distance Calculator

A Flask web application for batch distance calculation using OpenStreetMap Routing Machine (OSRM) with support for CSV upload and copy-paste input functionality.

## Features

- **Dual Input Methods**: Upload CSV files or paste tabular data directly
- **Data Validation**: Comprehensive validation for required columns and coordinate ranges
- **Batch Processing**: Calculate distances for multiple routes simultaneously
- **Progress Tracking**: Real-time progress indicators for batch calculations
- **Export Functionality**: Download results as CSV files
- **Responsive Design**: Modern, professional interface with Bootstrap
- **Error Handling**: Robust error handling for various failure scenarios

## Requirements

### Python Dependencies
```bash
pip install flask pandas requests numpy

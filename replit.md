# OSRM Distance Calculator

## Overview

This is a Flask-based web application for calculating distances between multiple points using OpenStreetMap Routing Machine (OSRM). The application provides a user-friendly interface for batch distance calculations through CSV file uploads or direct data input, with real-time progress tracking and CSV export functionality.

## System Architecture

### Frontend Architecture
- **Framework**: HTML/CSS/JavaScript with Bootstrap 5.1.3
- **Styling**: Custom CSS with Bootstrap components for responsive design
- **JavaScript**: Vanilla JS for file uploads, drag-and-drop, and AJAX requests
- **UI Components**: Professional interface with progress indicators and phase-based workflow

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Application Structure**: Modular design with separate route handlers and service classes
- **Request Handling**: RESTful API endpoints for file upload and distance calculations
- **Session Management**: Flask sessions for temporary data storage

### Data Processing
- **CSV Processing**: Pandas library for data manipulation and validation
- **Data Validation**: Comprehensive validation for coordinate ranges and required columns
- **Error Handling**: Robust error handling for invalid inputs and API failures

## Key Components

### Core Services
1. **OSRMService** (`osrm_service.py`): Handles communication with OSRM routing engine
2. **DataProcessor** (`data_processor.py`): Manages CSV processing and data validation
3. **Flask Routes** (`routes.py`): API endpoints for file upload and processing

### Required Data Structure
The application expects CSV files with the following columns:
- Vehicle Number
- Institute
- Point 1 latitude
- Point 1 longitude
- Point 2 latitude
- Point 2 longitude

### API Integration
- **OSRM Server**: Configurable OSRM server endpoint for route calculations
- **Distance Calculation**: Extracts distance (km) and duration (minutes) from OSRM responses

## Data Flow

1. **Input Phase**: User uploads CSV file or pastes data
2. **Validation Phase**: System validates required columns and coordinate ranges
3. **Processing Phase**: Batch distance calculations via OSRM API
4. **Results Phase**: Distance and duration results displayed with export options

## External Dependencies

### Python Libraries
- `flask`: Web framework
- `pandas`: Data processing and CSV handling
- `requests`: HTTP client for OSRM API calls
- `numpy`: Numerical operations support

### External Services
- **OSRM Server**: OpenStreetMap Routing Machine for distance calculations
- **CDN Resources**: Bootstrap CSS/JS and Font Awesome icons

### Configuration
- OSRM server endpoint configurable via environment variable
- Session secret key for security
- File upload limits (16MB max)

## Deployment Strategy

### Development
- Local development server with debug mode
- Hot reload for development changes
- Configurable host/port binding

### Production Considerations
- ProxyFix middleware for reverse proxy deployment
- Environment-based configuration
- Upload directory management
- Session security with production secret keys

### Environment Variables
- `OSRM_SERVER`: OSRM service endpoint
- `SESSION_SECRET`: Flask session encryption key

## Changelog
- July 08, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.
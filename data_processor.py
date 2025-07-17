import pandas as pd
import io
import logging
import re
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.required_columns = [ 
            'Vehicle Number', 'Institute',
            'Category', 'Route Number',
            'Driver Employee ID', 'Licensed Experience (years)',
            'Driver pt Latitude', 'Driver pt Longitude',
            'Driver pt Name', '1st Pickup pt Latitude',
            '1st Pickup pt Longitude', '1st Pickup pt Name'
        ]

    def validate_columns(self, df: pd.DataFrame) -> bool:
        missing_columns = [col for col in self.required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False
        return True
    
    def validate_coordinates(self, df: pd.DataFrame) -> Dict[str, Any]:
        issues = []
        
        coordinate_columns = [
            'Driver pt Latitude', 'Driver pt Longitude',
            '1st Pickup pt Latitude', '1st Pickup pt Longitude',
        ]
        for col in coordinate_columns:
            if col in df.columns:
                non_numeric = df[~pd.to_numeric(df[col], errors='coerce').notna()]
                if not non_numeric.empty:
                    issues.append(f"Non-numeric values in {col}: rows {non_numeric.index.tolist()}")
                
                numeric_values = pd.to_numeric(df[col], errors='coerce')
                if 'latitude' in col.lower():
                    out_of_range = numeric_values[(numeric_values < -90) | (numeric_values > 90)]
                    if not out_of_range.empty:
                        issues.append(f"Invalid latitude values in {col}: {out_of_range.index.tolist()}")
                elif 'longitude' in col.lower():
                    out_of_range = numeric_values[(numeric_values < -180) | (numeric_values > 180)]
                    if not out_of_range.empty:
                        issues.append(f"Invalid longitude values in {col}: {out_of_range.index.tolist()}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    def process_csv_file(self, file) -> pd.DataFrame:
        """Process uploaded CSV file"""
        try:
            # Read CSV file
            df = pd.read_csv(file)
            
            # Validate columns
            if not self.validate_columns(df):
                raise ValueError(f"Missing required columns. Expected: {self.required_columns}")
            
            # Validate coordinates
            validation_result = self.validate_coordinates(df)
            if not validation_result['valid']:
                raise ValueError(f"Data validation failed: {'; '.join(validation_result['issues'])}")
            
            # Clean and standardize data
            df = self.clean_data(df)
            
            logger.info(f"Successfully processed CSV file with {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            raise
    
    def process_pasted_data(self, content: str) -> pd.DataFrame:
        """Process pasted tabular data"""
        try:
            # Remove extra whitespace and empty lines
            content = content.strip()
            if not content:
                raise ValueError("No data provided")
            
            # Try to detect delimiter
            delimiter = self.detect_delimiter(content)
            
            # Parse the data
            df = pd.read_csv(io.StringIO(content), delimiter=delimiter)
            
            # Validate columns
            if not self.validate_columns(df):
                raise ValueError(f"Missing required columns. Expected: {self.required_columns}")
            
            # Validate coordinates
            validation_result = self.validate_coordinates(df)
            if not validation_result['valid']:
                raise ValueError(f"Data validation failed: {'; '.join(validation_result['issues'])}")
            
            # Clean and standardize data
            df = self.clean_data(df)
            
            logger.info(f"Successfully processed pasted data with {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Error processing pasted data: {str(e)}")
            raise
    
    def detect_delimiter(self, content: str) -> str:
        """Detect delimiter in pasted content"""
        first_line = content.split('\n')[0]
        
        # Count potential delimiters
        delimiters = {
            '\t': first_line.count('\t'),
            ',': first_line.count(','),
            ';': first_line.count(';'),
            '|': first_line.count('|')
        }
        
        # Return delimiter with highest count
        delimiter = max(delimiters, key=delimiters.get)
        
        # If no clear delimiter found, default to comma
        if delimiters[delimiter] == 0:
            delimiter = ','
        
        logger.debug(f"Detected delimiter: '{delimiter}'")
        return delimiter
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.dropna(how='all')
        string_columns = ['Vehicle Number', 'Institute']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
    
        coordinate_columns = [
            'Driver pt Latitude', 'Driver pt Longitude',
            '1st Pickup pt Latitude', '1st Pickup pt Longitude',
        ]

        for col in coordinate_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=coordinate_columns)
        df = df.reset_index(drop=True)
        
        return df
    
    def get_preview_data(self, df: pd.DataFrame, num_rows: int = 5) -> Dict[str, Any]:
        preview_df = df.head(num_rows)
        
        return {
            'columns': df.columns.tolist(),
            'rows': preview_df.values.tolist(),
            'total_rows': len(df),
            'preview_rows': len(preview_df)
        }
    
    def create_sample_data(self) -> pd.DataFrame:
        sample_data = {
            'Vehicle Number': ['KA53VH4001', 'KA53VH4002', 'KA53VH4003', 'KA53VH4004'],
            'Institute': ['Amity', 'MAHE', 'FIS', 'Nurture'],
            'Category': ['A+', 'A', 'B', 'C'],
            'Route Number': ['X1', 'X2', 'X3', 'X4'],
            'Driver Employee ID': ['BIT01994', 'BIT02767', 'TMP0204', 'TMP1121'],
            'Licensed Experience (years)': [6.6, 's', 5.0, 0.5],
            'Driver pt Latitude': [12.9875823, 13.0275876, 13.032832, 13.0910245],
            'Driver pt Longitude': [77.6009543, 77.710653, 77.609844, 77.5805965],
            'Driver pt Name': ['Shivaji Nagar', 'KR Puram', 'Shivaji Nagar', 'Goraguntepalya'],
            '1st Pickup pt Latitude': [13.02894312, 13.00877634, 12.96451233, 13.03983339],
            '1st Pickup pt Longitude': [77.56772479, 77.69236841, 77.64951354, 77.51983235],
            '1st Pickup pt Name': ['Ramaiah Hospital', 'KR Puram', 'Leela Palace Rd', 'Jalahalli']
        }
        return pd.DataFrame(sample_data)

import pandas as pd
import io
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.required_columns = [
            'Vehicle Number',
            'Institute',
            'Category',
            'Route Number',
            'Driver Employee ID',
            'Licensed Experience (years)',
            'Driver pt Latitude',
            'Driver pt Longitude',
            'Driver pt Name',
            '1st Pickup pt Latitude',
            '1st Pickup pt Longitude',
            '1st Pickup pt Name'
        ]

    def validate_columns(self, df: pd.DataFrame) -> bool:
        df.columns = df.columns.str.strip().str.replace(r'[^\x00-\x7F]+', '', regex=True)
        missing_columns = [col for col in self.required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False
        
        logger.debug(f"Actual columns: {df.columns.tolist()}")
        logger.debug(f"Expected columns: {self.required_columns}")

        return True

    def validate_coordinates(self, df: pd.DataFrame) -> Dict[str, Any]:
        issues = []

        coordinate_columns = [
            'Driver pt Latitude',
            'Driver pt Longitude',
            '1st Pickup pt Latitude',
            '1st Pickup pt Longitude'
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
                        issues.append(f"Invalid latitude values in {col}: rows {out_of_range.index.tolist()}")
                elif 'longitude' in col.lower():
                    out_of_range = numeric_values[(numeric_values < -180) | (numeric_values > 180)]
                    if not out_of_range.empty:
                        issues.append(f"Invalid longitude values in {col}: rows {out_of_range.index.tolist()}")

        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    def process_csv_file(self, file) -> pd.DataFrame:
        try:
            df = pd.read_csv(file)
            
            if not self.validate_columns(df):
                raise ValueError(f"Missing required columns. Expected: {self.required_columns}")
            
            validation_result = self.validate_coordinates(df)
            if not validation_result['valid']:
                raise ValueError(f"Data validation failed: {'; '.join(validation_result['issues'])}")
            
            df = self.clean_data(df)
            
            logger.info(f"Successfully processed CSV file with {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            raise
    
    def process_pasted_data(self, content: str) -> pd.DataFrame:
        try:
            content = content.strip()
            if not content:
                raise ValueError("No data provided")
    
            delimiter = self.detect_delimiter(content)
            df = pd.read_csv(io.StringIO(content), delimiter=delimiter)
            
            if not self.validate_columns(df):
                raise ValueError(f"Missing required columns. Expected: {self.required_columns}")
            
            validation_result = self.validate_coordinates(df)
            if not validation_result['valid']:
                raise ValueError(f"Data validation failed: {'; '.join(validation_result['issues'])}")
            
            df = self.clean_data(df)
            logger.info(f"Successfully processed pasted data with {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Error processing pasted data: {str(e)}")
            raise
    
    def detect_delimiter(self, content: str) -> str:
        
        first_line = content.split('\n')[0]
        delimiters = {
            '\t': first_line.count('\t'),
            ',': first_line.count(','),
            ';': first_line.count(';'),
            '|': first_line.count('|')
        }
        delimiter = max(delimiters, key=delimiters.get)
        if delimiters[delimiter] == 0:
            delimiter = ','
        logger.debug(f"Detected delimiter: '{delimiter}'")
        return delimiter
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df =df.dropna(how='all')
        string_columns = ['Vehicle Number', 'Institute','Category','Driver Employee ID']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        
        coordinate_columns = [
            'Driver pt Latitude',
            'Driver pt Longitude',
            '1st Pickup pt Latitude',
            '1st Pickup pt Longitude'
        ]
        for col in coordinate_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df=df.dropna(subset=coordinate_columns)
        df=df.reset_index(drop=True)
        
        return df
    
    def get_preview_data(self, df: pd.DataFrame, num_rows: int = 5) -> Dict[str, Any]:
        preview_df = df.head(num_rows)
        
        return {
            'columns': df.columns.tolist(),
            'rows': preview_df.values.tolist(),
            'total_rows':len(df),
            'preview_rows': len(preview_df)
        }
    
    def create_sample_data(self) -> pd.DataFrame:
        sample_data = {
            'Vehicle Number': ['VH001', 'VH002', 'VH003'],
            'Institute': ['Institute A', 'Institute B', 'Institute C'],
            'Category':['A+', 'A', 'B'],
            'Route Number':[2, 5, 3],
            'Driver Employee ID':['BIT2013', 'BIT0014', 'BIT2165'],
            'Licensed Experience (years)':[12.3, 4.5, 1.2],
            'Driver pt Latitude':[13.971, 12.7212, 12.966],
            'Driver pt Longitude':[77.2594, 77.5912, 77.7599],
            'Driver pt Name':['A point', 'B point', 'C point'],
            '1st Pickup pt Latitude':[13.5243, 12.1234, 13.4567],
            '1st Pickup pt Longitude':[77.4309, 77.1234, 77.5678],
            '1st Pickup pt Name':['Pickup A', 'Pickup B', 'Pickup C']
        }
        
        return pd.DataFrame(sample_data)

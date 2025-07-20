import requests
import pandas as pd
import logging
import time
from urllib.parse import urljoin
from flask import current_app
import uuid
from flask import g

progress_tracker = {}

logger = logging.getLogger(__name__)
class OSRMService:
    def __init__(self):
        self.base_url = current_app.config['OSRM_SERVER']
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'OSRM-Distance-Calculator/1.0'})

    def calculate_distance(self, lat1, lon1, lat2, lon2, *, task_id=None, index=None, total=None):
        """Calculate distance between two points using OSRM"""
        try:
            coordinates = f"{lon1},{lat1};{lon2},{lat2}"
            url = urljoin(self.base_url, f"/route/v1/driving/{coordinates}")
            params = {
                'overview': 'false',
                'alternatives': 'false',
                'steps': 'false',
                'geometries': 'polyline',
                'annotations': 'false'
            }

            logger.debug(f"OSRM request: {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if task_id is not None and index is not None and total:
                percent = int(((index + 1) / total) * 100)
                # Update progress only if it's actually changed
                if (task_id not in progress_tracker) or (progress_tracker[task_id].get('percent') != percent):
                    progress_tracker[task_id] = {
                        'percent': percent,
                        'message': f'Sending data to the server . . . .'
                    }

            if data.get('code') == 'Ok' and data.get('routes'):
                distance_m = data['routes'][0]['distance']
                duration_s = data['routes'][0]['duration']
                return {
                    'distance_km': round(distance_m / 1000, 3),
                    'duration_minutes': round(duration_s / 60, 1),
                    'status': 'success'
                }
            else:
                logger.warning(f"OSRM returned error: {data.get('message', 'Unknown error')}")
                return {
                    'distance_km': None,
                    'duration_minutes': None,
                    'status': 'error',
                    'error': data.get('message', 'No route found')
                }

        except requests.exceptions.Timeout:
            logger.error(f"OSRM request timeout for coordinates: {lat1},{lon1} to {lat2},{lon2}")
            return {
                'distance_km': None,
                'duration_minutes': None,
                'status': 'error',
                'error': 'Request timeout'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"OSRM request failed: {str(e)}")
            return {
                'distance_km': None,
                'duration_minutes': None,
                'status': 'error',
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error in OSRM calculation: {str(e)}")
            return {
                'distance_km': None,
                'duration_minutes': None,
                'status': 'error',
                'error': f'Calculation error: {str(e)}'
            }

    def calculate_batch_distances(self, df, task_id=None):
        """Calculate distances for a batch of routes"""
        logger.info(f"Starting batch distance calculation for {len(df)} routes")

        total = len(df)
        results = []
        successful_count = 0
        failed_count = 0

        for index, row in df.iterrows():
            try:
                lat1 = float(row['Driver pt Latitude'])
                lon1 = float(row['Driver pt Longitude'])
                lat2 = float(row['1st Pickup pt Latitude'])
                lon2 = float(row['1st Pickup pt Longitude'])

                result = self.calculate_distance(
                    lat1, lon1, lat2, lon2,
                    task_id=task_id, index=index, total=total
                )

                result_row = row.to_dict()
                result_row['Distance_km'] = result['distance_km']
                result_row['Duration_minutes'] = result['duration_minutes']
                result_row['Calculation_status'] = result['status']

                if result['status'] == 'error':
                    result_row['Error_message'] = result['error']
                    failed_count += 1
                else:
                    successful_count += 1

                results.append(result_row)

                time.sleep(0.1)  # Optional: throttle for OSRM stability

            except Exception as e:
                logger.error(f"Error processing row {index}: {str(e)}")
                result_row = row.to_dict()
                result_row['Distance_km'] = None
                result_row['Duration_minutes'] = None
                result_row['Calculation_status'] = 'error'
                result_row['Error_message'] = f'Processing error: {str(e)}'
                results.append(result_row)
                failed_count += 1

        logger.info(f"Batch calculation completed: {successful_count} successful, {failed_count} failed")

        if task_id:
            progress_tracker[task_id] = {
                'percent': 100,
                'message': 'Completed!'
            }

        return pd.DataFrame(results)

    def test_connection(self):
        """Test connection to OSRM server"""
        try:
            test_coords = "-74.0059,40.7128;-74.0060,40.7129"
            url = urljoin(self.base_url, f"/route/v1/driving/{test_coords}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('code') == 'Ok'
            
        except Exception as e:
            logger.error(f"OSRM connection test failed: {str(e)}")
            return False
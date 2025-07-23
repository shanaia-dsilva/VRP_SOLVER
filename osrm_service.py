
import requests
import pandas as pd
import numpy as np
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
        self.session.headers.update({'User-Agent': 'OSRM-VRP-Optimizer/1.0'})

    def osrm_distance(self, lat1, lon1, lat2, lon2):
        coords = f"{lon1},{lat1};{lon2},{lat2}"
        url = urljoin(self.base_url, f"/route/v1/driving/{coords}")
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('code') == 'Ok':
                return data['routes'][0]['distance'] / 1000  # km
            return float('inf')
        except Exception as e:
            logger.warning(f"OSRM error ({lat1},{lon1} to {lat2},{lon2}): {e}")
            return float('inf')

    def optimize_routes_vrp(self, df, task_id=None):
        driver_df = df[['Vehicle Number', 'Route Number', 'Driver pt Latitude', 'Driver pt Longitude', 'Driver pt Name',
                        'Institute', 'Licensed Experience (years)', 'Category']].rename(columns={
            'Vehicle Number': 'bus', 'Route Number': 'route',
            'Driver pt Latitude': 'dlat', 'Driver pt Longitude': 'dlon',
            'Driver pt Name': 'dname', 'Institute': 'cname',
            'Licensed Experience (years)': 'dexp', 'Category': 'category'
        }).set_index('bus')

        pickup_df = df[['Vehicle Number', 'Route Number', '1st Pickup pt Latitude', '1st Pickup pt Longitude',
                        '1st Pickup pt Name', 'Institute', 'Category']].rename(columns={
            'Vehicle Number': 'bus', 'Route Number': 'route',
            '1st Pickup pt Latitude': 'plat', '1st Pickup pt Longitude': 'plon',
            '1st Pickup pt Name': 'pname', 'Institute': 'cname',
            'Category': 'category'
        }).set_index('bus')

        # Depot filtering logic
        depot_names = ['MAHE', 'Kannamangla village Edify World School']
        shared_depots = {'MAHE': ['MAHE'], 'Amara Jyothi Public School': ['Amar Jyothi Public School & Pre-University College']}
        min_driver_exp = {'A+': 10, 'A': 3, 'B': 0, 'C': 0}

        driver_df['is_depot'] = driver_df['dname'].isin(depot_names)
        driver_df['allowed_institutes'] = driver_df.apply(
            lambda row: shared_depots.get(row['dname'], [row['cname']]) if row['is_depot'] else [], axis=1
        )
        
        # Construct matrix
        buses = driver_df.index
        matrix = pd.DataFrame(index=buses, columns=buses, dtype=float)
        cache = {}

        total = len(buses)

        for idx, bus in enumerate(buses):
            dlat, dlon = driver_df.loc[bus, ['dlat', 'dlon']]
            key = (dlat, dlon)
            if key in cache:
                matrix.loc[bus] = cache[key]
                continue
            distances = {}
            for target in buses:
                plat, plon = pickup_df.loc[target, ['plat', 'plon']]
                distances[target] = self.osrm_distance(dlat, dlon, plat, plon)
                if task_id:
                    percent = int(((idx + 1) / total) * 100)
                    if task_id not in progress_tracker or progress_tracker[task_id]['percent'] != percent:
                        progress_tracker[task_id] = {
                            'percent': percent,
                            'message': f'Building matrix... ({percent}%)'
                        }

            matrix.loc[bus] = distances
            cache[key] = distances

        # Apply institute and experience constraints
        for dbus in matrix.index:
            drow = driver_df.loc[dbus]
            driver_exp = float(drow['dexp'])  
            if drow['is_depot']:
                for pbus in matrix.columns:
                    pinc = pickup_df.loc[pbus, 'cname']
                    if pinc not in drow['allowed_institutes']:
                        matrix.loc[dbus, pbus] = float('inf')
            for pbus in matrix.columns:
                pcat = pickup_df.loc[pbus, 'category']
                try:
                    driver_exp = float(drow['dexp'])  # Ensure it's a number
                    required_exp = float(min_driver_exp.get(pcat, 0))
                    if driver_exp < required_exp:
                        matrix.loc[dbus, pbus] = float('inf')
                except Exception as e:
                    logger.warning(f"Experience check failed for driver {dbus} → pickup {pbus}: {e}")
                    matrix.loc[dbus, pbus] = float('inf')
        # Catch ∞ rows
        row_inf_mask = matrix.map(np.isinf).all(axis=1)
        problematic = matrix.index[row_inf_mask]
        if not problematic.empty:
            logger.warning(f"Drivers with no viable pickups: {list(problematic)}")

        # Solve assignment
        if matrix.applymap(np.isinf).all(axis=1).any():
            problematic_drivers = matrix.index[matrix.applymap(np.isinf).all(axis=1)]
            raise ValueError(f"Drivers with no valid pickups: {list(problematic_drivers)}")

        from scipy.optimize import linear_sum_assignment
        from solver import find_changed_chains

        optim_drivers, optim_pickups = linear_sum_assignment(matrix.to_numpy())
        driver_ids = matrix.index[optim_drivers]
        pickup_ids = matrix.columns[optim_pickups]

        result_df = pd.DataFrame({
            'From Bus': driver_ids,
            'Driver Site': driver_df.loc[driver_ids, 'cname'].values,
            'Driver pt lat': driver_df.loc[driver_ids, 'dlat'].values,
            'Driver pt long': driver_df.loc[driver_ids, 'dlon'].values,
            'Driver pt name': driver_df.loc[driver_ids, 'dname'].values,
            'Driver Route': driver_df.loc[driver_ids, 'route'].values,
            'Driver Experience': driver_df.loc[driver_ids, 'dexp'].values,
            'To Bus': pickup_ids,
            'Pickup Site': pickup_df.loc[pickup_ids, 'cname'].values,
            'Pickup Category': pickup_df.loc[pickup_ids, 'category'].values,
            'Pickup Route': pickup_df.loc[pickup_ids, 'route'].values,
            'Pickup pt name': pickup_df.loc[pickup_ids, 'pname'].values,
            'Pickup pt lat': pickup_df.loc[pickup_ids, 'plat'].values,
            'Pickup pt long': pickup_df.loc[pickup_ids, 'plon'].values,
            'Original dead km': [matrix.at[b, b] if b in matrix.columns else None for b in driver_ids],
            'Optimized dead km': [matrix.at[d, p] for d, p in zip(driver_ids, pickup_ids)]
        })

        if task_id:
            progress_tracker[task_id] = {'percent': 100, 'message': 'Optimization complete.'}

        chains = find_changed_chains(result_df['From Bus'].tolist(), result_df['To Bus'].tolist())
        logger.info(f"Optimized {len(result_df)} routes. Detected {len(chains)} swap chains.")

        # Calculate insight metrics
        total_routes = len(result_df)
        total_dead_km = result_df['Optimized dead km'].sum()
        original_dead_km = result_df['Original dead km'].sum()
        total_minimized = original_dead_km - total_dead_km
        total_swaps = sum(result_df['From Bus'] != result_df['To Bus'])
        inter_institute = sum(
            result_df['Driver Site'] != result_df['Pickup Site']
        )
        intra_institute = total_swaps - inter_institute

        return {
            'success': True,
            'results': result_df.to_dict('records'),
            'summary': {
                'total_routes': total_routes,
                'original_dead_km': round(original_dead_km, 2),
                'total_dead_km': round(total_dead_km, 2),
                'total_minimized': round(total_minimized, 2),
                'total_swaps': total_swaps,
                'inter_institute': inter_institute,
                'intra_institute': intra_institute
            },
            'chains': chains
        }

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

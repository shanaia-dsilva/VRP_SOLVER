from flask import Blueprint, request, jsonify, render_template, send_from_directory
import pandas as pd
import os
import uuid
import logging
from werkzeug.utils import secure_filename
from scipy.optimize import linear_sum_assignment
import numpy as np

from osrm_service import OSRMService
from data_processor import DataProcessor

routes = Blueprint('routes', __name__)
UPLOAD_FOLDER = "uploads"
EXPORT_FOLDER = "exports"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

@routes.route('/')
def index():
    return render_template('index.html')

@routes.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Empty filename'}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        processor = DataProcessor()
        df = processor.process_csv_file(filepath)

        preview = df.head().to_dict(orient="records")
        return jsonify({
            'success': True,
            'row_count': len(df),
            'preview': preview,
            'full_data': df.to_dict(orient="records"),
            'filename': filename,
            'message': f'Successfully uploaded {filename}'
        })
    except Exception as e:
        logging.error(f"Upload error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@routes.route('/process_depots', methods=['POST'])
def process_depots():
    data = request.get_json()
    if not data or 'depots' not in data:
        return jsonify({'success': False, 'message': 'Invalid input'}), 400

    lines = [line.strip() for line in data['depots'].split('\n') if line.strip()]
    df = pd.DataFrame({'Depot Name': lines})
    preview = df.head().to_dict(orient="records")

    return jsonify({
        'success': True,
        'row_count': len(df),
        'preview': preview,
        'full_data': df.to_dict(orient="records"),
        'message': f'Successfully processed {len(df)} depots'
    })

@routes.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        if not data or 'data' not in data or 'hubCapacities' not in data:
            return jsonify({'success': False, 'message': 'Missing required data'}), 400

        df = pd.DataFrame(data['data'])
        hub_capacities = data['hubCapacities']

        osrm = OSRMService()

        # Separate driver and pickup points
        driver_df = df[df['type'] == 'driver'].copy()
        pickup_df = df[df['type'] == 'pickup'].copy()

        # Expand hubs (which are drivers) based on their capacity
        expanded_driver_rows = []
        for _, row in driver_df.iterrows():
            hub_name = row['cname']
            capacity = int(hub_capacities.get(hub_name, 1))  # Default capacity 1
            for _ in range(capacity):
                expanded_driver_rows.append(row.copy())
        expanded_driver_df = pd.DataFrame(expanded_driver_rows).reset_index(drop=True)

        # Calculate distance matrix between expanded drivers and pickups
        distance_matrix = osrm.calculate_matrix(expanded_driver_df, pickup_df)

        # Pad to square matrix if needed (Hungarian needs square matrix)
        num_drivers, num_pickups = distance_matrix.shape
        if num_drivers > num_pickups:
            dummy_count = num_drivers - num_pickups
            dummy_columns = np.full((num_drivers, dummy_count), 9999.0)
            distance_matrix = np.hstack((distance_matrix, dummy_columns))
        elif num_pickups > num_drivers:
            dummy_rows = np.full((num_pickups - num_drivers, num_pickups), 9999.0)
            distance_matrix = np.vstack((distance_matrix, dummy_rows))

        # Apply Hungarian algorithm
        row_ind, col_ind = linear_sum_assignment(distance_matrix)
        result_rows = []
        for r, c in zip(row_ind, col_ind):
            if r < len(expanded_driver_df) and c < len(pickup_df):
                driver = expanded_driver_df.iloc[r]
                pickup = pickup_df.iloc[c]
                result_rows.append({
                    "From Bus": driver['vno'],
                    "Driver Site": driver['cname'],
                    "Driver lat": driver['dlat'],
                    "Driver lon": driver['dlon'],
                    "Pickup Site": pickup['cname'],
                    "Pickup lat": pickup['plat'],
                    "Pickup lon": pickup['plon'],
                    "Distance (m)": round(distance_matrix[r][c], 2)
                })

        result_df = pd.DataFrame(result_rows)
        csv_name = f"assignment_result_{uuid.uuid4().hex[:8]}.csv"
        csv_path = os.path.join(EXPORT_FOLDER, csv_name)
        result_df.to_csv(csv_path, index=False)

        return jsonify({
            'success': True,
            'row_count': len(result_df),
            'preview': result_df.head().to_dict(orient="records"),
            'csv_path': f'/exports/{csv_name}',
            'message': 'Optimized assignments completed.'
        })

    except Exception as e:
        logging.error(f"Calculation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@routes.route('/exports/<filename>')
def download_export(filename):
    return send_from_directory(EXPORT_FOLDER, filename, as_attachment=True)

@routes.route('/sample')
def download_sample():
    return send_from_directory('static', 'sample_distance_generator.csv', as_attachment=True)

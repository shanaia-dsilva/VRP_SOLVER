import os
import json
import logging
from flask import render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import pandas as pd
import io
from app import app
from osrm_service import OSRMService, progress_tracker
from data_processor import DataProcessor
from solver import run_deadkm_optimization


logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')
import uuid


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename.lower().endswith('.csv'):
            processor = DataProcessor()
            try:
                df = processor.process_csv_file(file)
                preview_data = processor.get_preview_data(df)

                task_id = str(uuid.uuid4()) 

                return jsonify({
                    'success': True,
                    'task_id': task_id, 
                    'preview': preview_data,
                    'full_data': df.values.tolist(),
                    'columns': df.columns.tolist(),
                    'row_count': len(df),
                    'message': f'Successfully loaded {len(df)} rows'
                })

            except Exception as e:
                logger.error(f"Error processing CSV: {str(e)}")
                return jsonify({'error': f'Error processing CSV: {str(e)}'}), 400
        else:
            return jsonify({'error': 'Invalid file format. Please upload a CSV file.'}), 400
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'An error occurred during upload'}), 500

@app.route('/process_paste', methods=['POST'])
def process_paste():
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'No data provided'}), 400
        
        content = data['content']
        processor = DataProcessor()
        
        try:
            df = processor.process_pasted_data(content)
            preview_data = processor.get_preview_data(df)
            

            return jsonify({
                'success': True,
                'preview': preview_data,
                'full_data': df.values.tolist(),
                'row_count': len(df),
                'message': f'Successfully processed {len(df)} rows'
            })

        except Exception as e:
            logger.error(f"Error processing pasted data: {str(e)}")
            return jsonify({'error': f'Error processing data: {str(e)}'}), 400
    
    except Exception as e:
        logger.error(f"Process paste error: {str(e)}")
        return jsonify({'error': 'An error occurred processing the data'}), 500
@app.route('/calculate', methods=['POST'])
def calculate_distances():
    try:
        data = request.get_json()
        if not data or 'data' not in data:
            return jsonify({'error': 'No data provided for calculation'}), 400

        df = pd.DataFrame(data['data'], columns=data.get('columns'))
        df.columns = df.columns.str.strip()
        task_id = data.get('task_id')

        processor = DataProcessor()
        if not processor.validate_columns(df):
            return jsonify({'error': 'Invalid data format. Please check required columns.'}), 400

        osrm_service = OSRMService()
        try:
            results_df = osrm_service.optimize_routes_vrp(df, task_id=task_id)

            results = {
                'success': True,
                'results': results_df.to_dict('records'),
                'summary': {
                    'total_routes': len(results_df),
                    'successful_calculations': len(results_df[results_df['Optimized dead km'].notna()]),
                    'failed_calculations': len(results_df[results_df['Optimized dead km'].isna()])
                }
            }

            return jsonify(results)

        except Exception as e:
            logger.error(f"Dead KM optimization error: {str(e)}")
            return jsonify({'error': f'Error during dead km optimization: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Calculate route error: {str(e)}")
        return jsonify({'error': 'An error occurred during calculation'}), 500
@app.route('/export/optimized', methods=['POST'])
def export_optimized():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400

        df = pd.DataFrame(data)

        ordered_columns = [
            'From Bus', 'Driver Site', 'Driver pt lat', 'Driver pt long',
            'Driver pt name', 'Driver Route', 'Driver Experience',
            'To Bus', 'Pickup Site', 'Pickup Category', 'Pickup Route',
            'Pickup pt name', 'Pickup pt lat', 'Pickup pt long',
            'Original dead km', 'Optimized dead km'
        ]
        df = df[[col for col in ordered_columns if col in df.columns]]

        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='optimized_assignments.csv'
        )
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': 'Export failed'}), 500

@app.route('/download-sample')
def download_sample():
    try:
        return send_file(
            'static/sample_distance_generator.csv',
            mimetype='text/csv',
            as_attachment=True,
            download_name='sample_distance_generator.csv'
        )
    except Exception as e:
        logger.error(f"Sample download error: {str(e)}")
        return jsonify({'error': 'Error downloading sample file'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.route('/progress/<task_id>')
def get_progress(task_id):
    progress = progress_tracker.get(task_id)
    if progress:
        return jsonify(progress)
    return jsonify({'percent': 0, 'message': 'Starting...'})
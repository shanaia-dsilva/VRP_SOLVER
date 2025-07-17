import os
import json
import logging
from flask import render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import pandas as pd
import io
from app import app
from osrm_service import OSRMService
from data_processor import DataProcessor

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename.lower().endswith('.csv'):
            # Process CSV file
            processor = DataProcessor()
            try:
                df = processor.process_csv_file(file)
                preview_data = processor.get_preview_data(df)
                
                # Store the dataframe in session or temporary storage
                # For simplicity, we'll return the preview and let frontend handle the calculation
                # return jsonify({
                #     'success': True,
                #     'preview': preview_data,
                #     'row_count': len(df),
                #     'message': f'Successfully loaded {len(df)} rows'
                # })

                return jsonify({
                    'success': True,
                    'preview': preview_data,
                    'full_data': df.values.tolist(),  
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


@app.route('/process_depots', methods=['POST'])
def process_depots():
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'No data provided'}), 400

        content = data['content']
        lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
        
        if not lines:
            return jsonify({'error': 'No depot names provided'}), 400

        df = pd.DataFrame({'Depot Name': lines})
        preview = df.head().to_dict(orient="records")
        
        return jsonify({
            'success': True,
            'row_count': len(df),
            'preview': preview,
            'full_data': df.to_dict(orient="records"),
            'message': f'Successfully processed {len(df)} depots'
        })

    except Exception as e:
        logger.error(f"Error processing depots: {str(e)}")
        return jsonify({'error': 'An error occurred while processing depot list'}), 500

# @app.route('/process_paste', methods=['POST'])
# def process_paste():
#     try:
#         data = request.get_json()
#         if not data or 'content' not in data:
#             return jsonify({'error': 'No data provided'}), 400
        
#         content = data['content']
#         processor = DataProcessor()
        
#         try:
#             df = processor.process_pasted_data(content)
#             preview_data = processor.get_preview_data(df)
            
#             # return jsonify({
#             #     'success': True,
#             #     'preview': preview_data,
#             #     'row_count': len(df),
#             #     'message': f'Successfully processed {len(df)} rows'
#             # })

#             return jsonify({
#                 'success': True,
#                 'preview': preview_data,
#                 'full_data': df.values.tolist(),
#                 'row_count': len(df),
#                 'message': f'Successfully processed {len(df)} rows'
#             })

#         except Exception as e:
#             logger.error(f"Error processing pasted data: {str(e)}")
#             return jsonify({'error': f'Error processing data: {str(e)}'}), 400
    
#     except Exception as e:
#         logger.error(f"Process paste error: {str(e)}")
#         return jsonify({'error': 'An error occurred processing the data'}), 500

@app.route('/calculate', methods=['POST'])
def calculate_distances():
    try:
        data = request.get_json()
        if not data or 'data' not in data:
            return jsonify({'error': 'No data provided for calculation'}), 400
        
        # Convert data back to DataFrame
        df = pd.DataFrame(data['data'])
        
        # Validate required columns
        processor = DataProcessor()
        if not processor.validate_columns(df):
            return jsonify({'error': 'Invalid data format. Please check required columns.'}), 400
        
        # Calculate distances using OSRM
        osrm_service = OSRMService()
        try:
            results_df = osrm_service.calculate_batch_distances(df)
            ordered_columns = [
                'Institute', 'Vehicle Number',
                'Point 1 latitude', 'Point 1 longitude',
                'Point 2 latitude', 'Point 2 longitude',
                'Distance_km', 'Duration_minutes','Calculation_status'
            ]

            results_df = results_df[ordered_columns]

            # Convert results to JSON for frontend
            results = {
                'success': True,
                'results': results_df.to_dict('records'),
                'summary': {
                    'total_routes': len(results_df),
                    'successful_calculations': len(results_df[results_df['Distance_km'].notna()]),
                    'failed_calculations': len(results_df[results_df['Distance_km'].isna()])
                }
            }
            
            return jsonify(results)
        
        except Exception as e:
            logger.error(f"OSRM calculation error: {str(e)}")
            return jsonify({'error': f'Error calculating distances: {str(e)}'}), 500
    
    except Exception as e:
        logger.error(f"Calculate error: {str(e)}")
        return jsonify({'error': 'An error occurred during calculation'}), 500

@app.route('/export/<format>')
def export_results(format):
    try:
        # Get results from request args or session
        data = request.args.get('data')
        if not data:
            return jsonify({'error': 'No data to export'}), 400
        
        results = json.loads(data)
        df = pd.DataFrame(results)

        ordered_columns = [
                'Institute', 'Vehicle Number',
                'Point 1 latitude', 'Point 1 longitude',
                'Point 2 latitude', 'Point 2 longitude',
                'Distance_km', 'Duration_minutes','Calculation_status'
            ]
        
        df = df[ordered_columns] 

        
        if format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            csv_data = io.BytesIO()
            csv_data.write(output.getvalue().encode('utf-8'))
            csv_data.seek(0)
            
            return send_file(
                csv_data,
                mimetype='text/csv',
                as_attachment=True,
                download_name='distance_results.csv'
            )
        else:
            return jsonify({'error': 'Unsupported export format'}), 400
    
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': 'An error occurred during export'}), 500

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

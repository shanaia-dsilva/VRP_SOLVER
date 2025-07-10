import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from flask import send_from_directory

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-key-Shanaia_Baghirathi!@#$")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OSRM_SERVER'] = os.environ.get('OSRM_SERVER', 'http://localhost:5000')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


from routes import *

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

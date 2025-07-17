import os
import logging
from flask import Flask, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from routes import routes  
from config import Config

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

app.register_blueprint(routes)

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

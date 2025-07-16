import os

class Config:
    SECRET_KEY=os.environ.get("SESSION_SECRET", "shanaia-dev-key-Baghirathi!@#$!#^@%^%#$&")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  
    UPLOAD_FOLDER = 'uploads'
    OSRM_SERVER = os.environ.get('OSRM_SERVER', 'http://localhost:5000')


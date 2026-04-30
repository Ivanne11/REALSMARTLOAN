import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'smartloan-secret-key-2024-very-secure-random-string'
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'Ivanne032125')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'smartloan_db')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes session timeout
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload folders
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

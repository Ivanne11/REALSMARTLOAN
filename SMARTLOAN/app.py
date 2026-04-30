"""
SmartLoan - Loan Management System
Main Application File
"""
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from datetime import timedelta
import os

from config import Config
from models import init_db
from decorators import login_required, admin_required

# Import blueprints
from auth import auth_bp
from admin import admin_bp
from borrower import borrower_bp
from loan import loan_bp
from payment import payment_bp
from reports import reports_bp
from dashboard import dashboard_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Session configuration
    app.permanent_session_lifetime = timedelta(seconds=Config.PERMANENT_SESSION_LIFETIME)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(borrower_bp, url_prefix='/borrower')
    app.register_blueprint(loan_bp, url_prefix='/loan')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
    # Ensure upload folder exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    
    # Initialize database tables
    with app.app_context():
        init_db()
    
    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('dashboard.home'))
        return redirect(url_for('auth.login'))
    
    @app.route('/home')
    @login_required
    def home_redirect():
        return redirect(url_for('dashboard.home'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        if request.is_json:
            return jsonify({'success': False, 'message': 'Page not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if request.is_json:
            return jsonify({'success': False, 'message': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)


from functools import wraps
from flask import session, redirect, url_for, flash, request
from datetime import datetime, timedelta

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check session expiration
        if 'last_activity' in session:
            last_activity = session['last_activity']
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity)
            
            if datetime.now() - last_activity > timedelta(minutes=30):
                session.clear()
                flash('Your session has expired. Please log in again.', 'warning')
                return redirect(url_for('auth.login'))
        
        # Update last activity
        session['last_activity'] = datetime.now().isoformat()
        session.modified = True
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if session.get('role') != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard.home'))
        
        # Update last activity
        session['last_activity'] = datetime.now().isoformat()
        session.modified = True
        
        return f(*args, **kwargs)
    return decorated_function

def prevent_authenticated(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            return redirect(url_for('dashboard.home'))
        return f(*args, **kwargs)
    return decorated_function


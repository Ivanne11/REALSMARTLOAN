"""
Authentication Blueprint - Login, Logout, Password Management
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime

from models import get_db_connection
from utils import (validate_username, validate_password, validate_required,
                   hash_password, verify_password, log_activity)
from decorators import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard.home'))
    
    if request.method == 'POST':
        # Handle both form and JSON requests
        if request.is_json:
            data = request.get_json()
            username = data.get('username', '')
            password = data.get('password', '')
        else:
            username = request.form.get('username', '')
            password = request.form.get('password', '')
        
        # Server-side validation
        is_valid, msg = validate_required(username, "Username")
        if not is_valid:
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'error')
            return render_template('auth/login.html')
        
        is_valid, msg = validate_required(password, "Password")
        if not is_valid:
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'error')
            return render_template('auth/login.html')
        
        # Trim and sanitize
        username = username.strip()
        password = password.strip()
        
        # Check credentials
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s AND status = 'active'", (username,))
            user = cursor.fetchone()
        except ConnectionError as ce:
            # DB not available - show friendly message
            msg = 'Database connection error. Please try again later.'
            print(f"DB connection error during login: {ce}")
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 503
            flash(msg, 'error')
            return render_template('auth/login.html')
        except Exception as e:
            # Unexpected error
            print(f"Unexpected DB error during login: {e}")
            if request.is_json:
                return jsonify({'success': False, 'message': 'Internal server error'}), 500
            flash('Internal server error. Please contact the administrator.', 'error')
            return render_template('auth/login.html')
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        
        if user and verify_password(password, user['password_hash']):
            # Set session
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            session['login_time'] = datetime.now().isoformat()
            
            # Update last login
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
                conn.commit()
            except Exception as e:
                # Fail silently for last_login update but log for debugging
                print(f"Warning: failed to update last_login: {e}")
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
            
            # Log activity
            log_activity(user['id'], 'LOGIN', f"User {user['username']} logged in", request.remote_addr)
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Login successful', 'redirect': url_for('dashboard.home')})
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard.home'))
        else:
            # Log failed attempt
            if user:
                log_activity(user['id'], 'LOGIN_FAILED', f"Failed login attempt for {username}", request.remote_addr)
            
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid username or password.'}), 401
            flash('Invalid username or password.', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')
    
    # Log activity before clearing session
    log_activity(user_id, 'LOGOUT', f"User {username} logged out", request.remote_addr)
    
    # Clear session completely
    session.clear()
    
    response = redirect(url_for('auth.login'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    flash('You have been logged out successfully.', 'success')
    return response

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    user_id = session.get('user_id')
    data = request.get_json() if request.is_json else request.form
    
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    
    # Validation
    is_valid, msg = validate_required(current_password, "Current password")
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    is_valid, msg = validate_password(new_password)
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': 'New passwords do not match.'}), 400
    
    # Verify current password
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user or not verify_password(current_password, user['password_hash']):
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 400
    
    # Update password
    new_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s", (new_hash, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    log_activity(user_id, 'PASSWORD_CHANGED', "User changed their password", request.remote_addr)
    
    return jsonify({'success': True, 'message': 'Password changed successfully.'})


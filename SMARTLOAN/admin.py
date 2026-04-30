"""
Admin Blueprint - User Management, Loan Types, Loan Plans, Activity Logs
"""
from flask import Blueprint, render_template, request, jsonify, session
from mysql.connector import Error

from models import get_db_connection
from utils import (validate_username, validate_password, validate_email, validate_name,
                   validate_required, hash_password, log_activity, sanitize_input)
from decorators import login_required, admin_required

admin_bp = Blueprint('admin', __name__)
ALLOWED_ROLES = {'admin', 'user'}
ALLOWED_STATUSES = {'active', 'inactive'}

# ==================== USER MANAGEMENT ====================

@admin_bp.route('/users')
@login_required
@admin_required
def users_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, full_name, email, role, status, last_login, created_at FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    data = request.get_json() if request.is_json else request.form
    
    username = sanitize_input(data.get('username', ''))
    full_name = sanitize_input(data.get('full_name', ''))
    email = sanitize_input(data.get('email', ''))
    password = data.get('password', '').strip()
    role = sanitize_input(data.get('role', 'user'))
    status = sanitize_input(data.get('status', 'active'))
    
    # Validation
    is_valid, msg = validate_username(username)
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    is_valid, msg = validate_name(full_name, "Full name")
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    is_valid, msg = validate_email(email)
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    is_valid, msg = validate_password(password)
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    if role not in ALLOWED_ROLES:
        return jsonify({'success': False, 'message': 'Invalid role.'}), 400
    if status not in ALLOWED_STATUSES:
        return jsonify({'success': False, 'message': 'Invalid status.'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check for duplicate username or email
    cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Username or email already exists.'}), 400
    
    # Create user
    password_hash = hash_password(password)
    cursor.execute(
        "INSERT INTO users (username, full_name, email, password_hash, role, status) VALUES (%s, %s, %s, %s, %s, %s)",
        (username, full_name, email, password_hash, role, status)
    )
    conn.commit()
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()
    
    log_activity(session.get('user_id'), 'USER_CREATED', f"Created user: {username}", request.remote_addr)
    
    return jsonify({'success': True, 'message': 'User created successfully.', 'user_id': user_id})

@admin_bp.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
@admin_required
def update_user(user_id):
    data = request.get_json() if request.is_json else request.form
    
    full_name = sanitize_input(data.get('full_name', ''))
    email = sanitize_input(data.get('email', ''))
    role = sanitize_input(data.get('role', ''))
    status = sanitize_input(data.get('status', ''))
    
    is_valid, msg = validate_name(full_name, "Full name")
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    is_valid, msg = validate_email(email)
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400

    if role not in ALLOWED_ROLES:
        return jsonify({'success': False, 'message': 'Invalid role.'}), 400
    if status not in ALLOWED_STATUSES:
        return jsonify({'success': False, 'message': 'Invalid status.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check for duplicate email
    cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, user_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Email already in use.'}), 400
    
    cursor.execute(
        "UPDATE users SET full_name = %s, email = %s, role = %s, status = %s, updated_at = NOW() WHERE id = %s",
        (full_name, email, role, status, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
    log_activity(session.get('user_id'), 'USER_UPDATED', f"Updated user ID: {user_id}", request.remote_addr)
    
    return jsonify({'success': True, 'message': 'User updated successfully.'})

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    # Prevent self-deletion
    if user_id == session.get('user_id'):
        return jsonify({'success': False, 'message': 'You cannot delete your own account.'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'User not found.'}), 404
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    
    log_activity(session.get('user_id'), 'USER_DELETED', f"Deleted user ID: {user_id}", request.remote_addr)
    
    return jsonify({'success': True, 'message': 'User deleted successfully.'})

# ==================== LOAN TYPES ====================

@admin_bp.route('/loan-types')
@login_required
@admin_required
def loan_types():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM loan_types ORDER BY name")
    types = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/loan_types.html', loan_types=types)

@admin_bp.route('/loan-types/create', methods=['POST'])
@login_required
@admin_required
def create_loan_type():
    data = request.get_json() if request.is_json else request.form
    
    name = sanitize_input(data.get('name', ''))
    description = sanitize_input(data.get('description', ''))
    
    is_valid, msg = validate_required(name, "Loan type name")
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM loan_types WHERE name = %s", (name,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Loan type already exists.'}), 400
    cursor.execute("INSERT INTO loan_types (name, description) VALUES (%s, %s)", (name, description))
    conn.commit()
    type_id = cursor.lastrowid
    cursor.close()
    conn.close()
    
    log_activity(session.get('user_id'), 'LOAN_TYPE_CREATED', f"Created loan type: {name}", request.remote_addr)
    return jsonify({'success': True, 'message': 'Loan type created.', 'id': type_id})

@admin_bp.route('/loan-types/<int:type_id>/update', methods=['POST'])
@login_required
@admin_required
def update_loan_type(type_id):
    data = request.get_json() if request.is_json else request.form
    
    name = sanitize_input(data.get('name', ''))
    description = sanitize_input(data.get('description', ''))
    
    is_valid, msg = validate_required(name, "Loan type name")
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM loan_types WHERE name = %s AND id != %s", (name, type_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Loan type already exists.'}), 400
    cursor.execute("UPDATE loan_types SET name = %s, description = %s WHERE id = %s", (name, description, type_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    log_activity(session.get('user_id'), 'LOAN_TYPE_UPDATED', f"Updated loan type ID: {type_id}", request.remote_addr)
    return jsonify({'success': True, 'message': 'Loan type updated.'})

@admin_bp.route('/loan-types/<int:type_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_loan_type(type_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM loan_types WHERE id = %s", (type_id,))
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Loan type not found.'}), 404
        conn.commit()
    except Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Unable to delete loan type: {err.msg}'}), 400
    finally:
        cursor.close()
        conn.close()
    
    log_activity(session.get('user_id'), 'LOAN_TYPE_DELETED', f"Deleted loan type ID: {type_id}", request.remote_addr)
    return jsonify({'success': True, 'message': 'Loan type deleted.'})

# ==================== LOAN PLANS ====================

@admin_bp.route('/loan-plans')
@login_required
@admin_required
def loan_plans():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM loan_plans ORDER BY months ASC")
    plans = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/loan_plans.html', loan_plans=plans)

@admin_bp.route('/loan-plans/create', methods=['POST'])
@login_required
@admin_required
def create_loan_plan():
    data = request.get_json() if request.is_json else request.form
    
    plan_name = sanitize_input(data.get('plan_name', ''))
    try:
        months = int(data.get('months', 0))
        interest_rate = float(data.get('interest_rate', 0))
        penalty_rate = float(data.get('penalty_rate', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid numeric values.'}), 400
    
    is_valid, msg = validate_required(plan_name, "Plan name")
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    
    if months < 1:
        return jsonify({'success': False, 'message': 'Months must be at least 1.'}), 400
    if interest_rate < 0 or interest_rate > 100:
        return jsonify({'success': False, 'message': 'Interest rate must be between 0 and 100.'}), 400
    if penalty_rate < 0 or penalty_rate > 100:
        return jsonify({'success': False, 'message': 'Penalty rate must be between 0 and 100.'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM loan_plans WHERE plan_name = %s", (plan_name,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Loan plan already exists.'}), 400
    cursor.execute(
        "INSERT INTO loan_plans (plan_name, months, interest_rate, penalty_rate) VALUES (%s, %s, %s, %s)",
        (plan_name, months, interest_rate, penalty_rate)
    )
    conn.commit()
    plan_id = cursor.lastrowid
    cursor.close()
    conn.close()
    
    log_activity(session.get('user_id'), 'LOAN_PLAN_CREATED', f"Created loan plan: {plan_name}", request.remote_addr)
    return jsonify({'success': True, 'message': 'Loan plan created.', 'id': plan_id})

@admin_bp.route('/loan-plans/<int:plan_id>/update', methods=['POST'])
@login_required
@admin_required
def update_loan_plan(plan_id):
    data = request.get_json() if request.is_json else request.form
    
    plan_name = sanitize_input(data.get('plan_name', ''))
    try:
        months = int(data.get('months', 0))
        interest_rate = float(data.get('interest_rate', 0))
        penalty_rate = float(data.get('penalty_rate', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid numeric values.'}), 400
    
    is_valid, msg = validate_required(plan_name, "Plan name")
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    if months < 1:
        return jsonify({'success': False, 'message': 'Months must be at least 1.'}), 400
    if interest_rate < 0 or interest_rate > 100:
        return jsonify({'success': False, 'message': 'Interest rate must be between 0 and 100.'}), 400
    if penalty_rate < 0 or penalty_rate > 100:
        return jsonify({'success': False, 'message': 'Penalty rate must be between 0 and 100.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM loan_plans WHERE plan_name = %s AND id != %s", (plan_name, plan_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Loan plan already exists.'}), 400
    cursor.execute(
        "UPDATE loan_plans SET plan_name = %s, months = %s, interest_rate = %s, penalty_rate = %s WHERE id = %s",
        (plan_name, months, interest_rate, penalty_rate, plan_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
    log_activity(session.get('user_id'), 'LOAN_PLAN_UPDATED', f"Updated loan plan ID: {plan_id}", request.remote_addr)
    return jsonify({'success': True, 'message': 'Loan plan updated.'})

@admin_bp.route('/loan-plans/<int:plan_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_loan_plan(plan_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM loan_plans WHERE id = %s", (plan_id,))
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Loan plan not found.'}), 404
        conn.commit()
    except Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Unable to delete loan plan: {err.msg}'}), 400
    finally:
        cursor.close()
        conn.close()
    
    log_activity(session.get('user_id'), 'LOAN_PLAN_DELETED', f"Deleted loan plan ID: {plan_id}", request.remote_addr)
    return jsonify({'success': True, 'message': 'Loan plan deleted.'})

# ==================== ACTIVITY LOGS ====================

@admin_bp.route('/activity-logs')
@login_required
@admin_required
def activity_logs():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT al.*, u.username, u.full_name 
        FROM activity_logs al 
        LEFT JOIN users u ON al.user_id = u.id 
        ORDER BY al.created_at DESC 
        LIMIT 500
    """)
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin/activity_logs.html', logs=logs)


"""
Borrower Blueprint - Borrower Management
"""
from flask import Blueprint, render_template, request, jsonify, session
from mysql.connector import Error

from models import get_db_connection
from utils import (
    validate_required,
    validate_name,
    validate_email,
    validate_phone,
    validate_numeric,
    validate_date,
    sanitize_input,
    calculate_credit_score,
    log_activity,
    serialize_record,
)
from decorators import login_required

borrower_bp = Blueprint('borrower', __name__)

ALLOWED_GENDERS = {'Male', 'Female', 'Other'}
ALLOWED_EMPLOYMENT_STATUSES = {
    'Employed',
    'Self-Employed',
    'Contract',
    'Unemployed',
    'Retired'
}


def _validate_optional_email(email):
    email = sanitize_input(email)
    if not email:
        return True, None
    return validate_email(email)


def _validate_optional_date(date_value, field_name):
    cleaned = sanitize_input(date_value)
    if not cleaned:
        return True, None
    return validate_date(cleaned, field_name)


def _prepare_borrower_payload(data, require_address=True):
    first_name = sanitize_input(data.get('first_name', ''))
    last_name = sanitize_input(data.get('last_name', ''))
    middle_name = sanitize_input(data.get('middle_name', '')) or None
    email = data.get('email', '')
    phone = sanitize_input(data.get('phone', ''))
    address = sanitize_input(data.get('address', ''))
    date_of_birth = data.get('date_of_birth', '')
    gender = sanitize_input(data.get('gender', '')) or None
    employment_status = sanitize_input(data.get('employment_status', 'Employed')) or 'Employed'
    employer = sanitize_input(data.get('employer', '')) or None
    monthly_income = data.get('monthly_income', 0)

    is_valid, result = validate_name(first_name, "First name")
    if not is_valid:
        return False, result
    first_name = result

    is_valid, result = validate_name(last_name, "Last name")
    if not is_valid:
        return False, result
    last_name = result

    is_valid, result = _validate_optional_email(email)
    if not is_valid:
        return False, result
    email = result

    is_valid, result = validate_phone(phone)
    if not is_valid:
        return False, result
    phone = result

    if require_address:
        is_valid, result = validate_required(address, "Address")
        if not is_valid:
            return False, result
        address = result

    is_valid, result = _validate_optional_date(date_of_birth, "Date of birth")
    if not is_valid:
        return False, result
    date_of_birth = result

    if gender and gender not in ALLOWED_GENDERS:
        return False, 'Invalid gender selected.'

    if employment_status not in ALLOWED_EMPLOYMENT_STATUSES:
        return False, 'Invalid employment status selected.'

    is_valid, result = validate_numeric(monthly_income, "Monthly income", min_val=0)
    if not is_valid:
        return False, result
    monthly_income = result

    credit_score, risk_level = calculate_credit_score({
        'monthly_income': monthly_income,
        'employment_status': employment_status,
        'active_loans': 0,
    })

    return True, {
        'first_name': first_name,
        'last_name': last_name,
        'middle_name': middle_name,
        'email': email,
        'phone': phone,
        'address': address,
        'date_of_birth': date_of_birth,
        'gender': gender,
        'employment_status': employment_status,
        'employer': employer,
        'monthly_income': monthly_income,
        'credit_score': credit_score,
        'risk_level': risk_level,
    }


def _log_risk_assessment(cursor, borrower_id, credit_score, risk_level, notes):
    cursor.execute(
        """
        INSERT INTO risk_assessments (borrower_id, credit_score, risk_level, assessed_by, notes)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (borrower_id, credit_score, risk_level, session.get('user_id'), notes)
    )


@borrower_bp.route('/list')
@login_required
def borrower_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT b.*,
               COUNT(DISTINCT l.id) AS total_loans,
               SUM(CASE WHEN l.status = 'active' THEN 1 ELSE 0 END) AS active_loans
        FROM borrowers b
        LEFT JOIN loans l ON b.id = l.borrower_id
        GROUP BY b.id
        ORDER BY b.created_at DESC
        """
    )
    borrowers = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('borrower/list.html', borrowers=borrowers)


@borrower_bp.route('/create', methods=['POST'])
@login_required
def create_borrower():
    data = request.get_json() if request.is_json else request.form

    is_valid, payload = _prepare_borrower_payload(data)
    if not is_valid:
        return jsonify({'success': False, 'message': payload}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if payload['email']:
            cursor.execute("SELECT id FROM borrowers WHERE email = %s", (payload['email'],))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Email already registered.'}), 400

        cursor.execute(
            """
            INSERT INTO borrowers (
                first_name, last_name, middle_name, email, phone, address, date_of_birth,
                gender, credit_score, risk_level, monthly_income, employment_status,
                employer, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                payload['first_name'],
                payload['last_name'],
                payload['middle_name'],
                payload['email'],
                payload['phone'],
                payload['address'],
                payload['date_of_birth'],
                payload['gender'],
                payload['credit_score'],
                payload['risk_level'],
                payload['monthly_income'],
                payload['employment_status'],
                payload['employer'],
                session.get('user_id'),
            )
        )

        borrower_id = cursor.lastrowid
        _log_risk_assessment(
            cursor,
            borrower_id,
            payload['credit_score'],
            payload['risk_level'],
            'Initial borrower assessment'
        )

        conn.commit()
    finally:
        cursor.close()
        conn.close()

    log_activity(
        session.get('user_id'),
        'BORROWER_CREATED',
        f"Created borrower: {payload['first_name']} {payload['last_name']}",
        request.remote_addr
    )

    return jsonify({'success': True, 'message': 'Borrower created successfully.', 'borrower_id': borrower_id})


@borrower_bp.route('/<int:borrower_id>')
@login_required
def get_borrower(borrower_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM borrowers WHERE id = %s", (borrower_id,))
    borrower = cursor.fetchone()

    if not borrower:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Borrower not found.'}), 404

    cursor.execute(
        """
        SELECT l.*, lt.name AS loan_type_name, lp.plan_name, lp.months
        FROM loans l
        JOIN loan_types lt ON l.loan_type_id = lt.id
        JOIN loan_plans lp ON l.loan_plan_id = lp.id
        WHERE l.borrower_id = %s
        ORDER BY l.created_at DESC
        """,
        (borrower_id,)
    )
    loans = cursor.fetchall()

    borrower_data = {
        'monthly_income': borrower['monthly_income'],
        'employment_status': borrower['employment_status'],
        'active_loans': sum(1 for loan in loans if loan['status'] == 'active')
    }
    credit_score, risk_level = calculate_credit_score(borrower_data)

    cursor.close()
    conn.close()

    return jsonify({
        'success': True,
        'borrower': serialize_record(borrower),
        'loans': [serialize_record(loan) for loan in loans],
        'credit_score': credit_score,
        'risk_level': risk_level
    })


@borrower_bp.route('/<int:borrower_id>/update', methods=['POST'])
@login_required
def update_borrower(borrower_id):
    data = request.get_json() if request.is_json else request.form

    is_valid, payload = _prepare_borrower_payload(data)
    if not is_valid:
        return jsonify({'success': False, 'message': payload}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if payload['email']:
            cursor.execute("SELECT id FROM borrowers WHERE email = %s AND id != %s", (payload['email'], borrower_id))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Email already in use.'}), 400

        cursor.execute(
            """
            UPDATE borrowers
            SET first_name = %s,
                last_name = %s,
                middle_name = %s,
                email = %s,
                phone = %s,
                address = %s,
                date_of_birth = %s,
                gender = %s,
                credit_score = %s,
                risk_level = %s,
                employment_status = %s,
                employer = %s,
                monthly_income = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                payload['first_name'],
                payload['last_name'],
                payload['middle_name'],
                payload['email'],
                payload['phone'],
                payload['address'],
                payload['date_of_birth'],
                payload['gender'],
                payload['credit_score'],
                payload['risk_level'],
                payload['employment_status'],
                payload['employer'],
                payload['monthly_income'],
                borrower_id,
            )
        )

        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Borrower not found.'}), 404

        _log_risk_assessment(
            cursor,
            borrower_id,
            payload['credit_score'],
            payload['risk_level'],
            'Borrower details updated'
        )

        conn.commit()
    finally:
        cursor.close()
        conn.close()

    log_activity(session.get('user_id'), 'BORROWER_UPDATED', f"Updated borrower ID: {borrower_id}", request.remote_addr)

    return jsonify({'success': True, 'message': 'Borrower updated successfully.'})


@borrower_bp.route('/<int:borrower_id>/delete', methods=['POST'])
@login_required
def delete_borrower(borrower_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM loans WHERE borrower_id = %s LIMIT 1", (borrower_id,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Cannot delete borrower with existing loan records.'}), 400

        cursor.execute("DELETE FROM borrowers WHERE id = %s", (borrower_id,))
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Borrower not found.'}), 404

        conn.commit()
    except Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Unable to delete borrower: {err.msg}'}), 400
    finally:
        cursor.close()
        conn.close()

    log_activity(session.get('user_id'), 'BORROWER_DELETED', f"Deleted borrower ID: {borrower_id}", request.remote_addr)

    return jsonify({'success': True, 'message': 'Borrower deleted successfully.'})

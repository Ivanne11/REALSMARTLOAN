"""
Loan Blueprint - Loan Management, Calculator, Amortization
"""
from flask import Blueprint, render_template, request, jsonify, session
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from models import get_db_connection
from utils import (validate_required, validate_numeric, validate_date, 
                   sanitize_input, format_currency, log_activity, serialize_record, serialize_records)
from decorators import login_required

loan_bp = Blueprint('loan', __name__)

@loan_bp.route('/list')
@login_required
def loan_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT l.*, 
               b.first_name, b.last_name, b.email, b.phone,
               lt.name as loan_type_name,
               lp.plan_name, lp.months as plan_months, lp.interest_rate, lp.penalty_rate
        FROM loans l
        JOIN borrowers b ON l.borrower_id = b.id
        JOIN loan_types lt ON l.loan_type_id = lt.id
        JOIN loan_plans lp ON l.loan_plan_id = lp.id
        ORDER BY l.created_at DESC
    """)
    loans = cursor.fetchall()
    
    # Get lookup data
    cursor.execute("SELECT * FROM loan_types ORDER BY name")
    loan_types = cursor.fetchall()
    cursor.execute("SELECT * FROM loan_plans ORDER BY plan_name")
    loan_plans = cursor.fetchall()
    cursor.execute("SELECT id, first_name, last_name, email FROM borrowers ORDER BY last_name")
    borrowers = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('loan/list.html', loans=loans, loan_types=loan_types, 
                          loan_plans=loan_plans, borrowers=borrowers)

@loan_bp.route('/create', methods=['POST'])
@login_required
def create_loan():
    data = request.get_json() if request.is_json else request.form
    
    borrower_id = data.get('borrower_id')
    loan_type_id = data.get('loan_type_id')
    loan_plan_id = data.get('loan_plan_id')
    amount = data.get('amount')
    purpose = sanitize_input(data.get('purpose', ''))
    release_date = sanitize_input(data.get('release_date', ''))
    
    # Validation
    is_valid, msg = validate_numeric(borrower_id, "Borrower", allow_float=False, min_val=1)
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    borrower_id = int(msg)
    
    is_valid, msg = validate_numeric(loan_type_id, "Loan type", allow_float=False, min_val=1)
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    loan_type_id = int(msg)
    
    is_valid, msg = validate_numeric(loan_plan_id, "Loan plan", allow_float=False, min_val=1)
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    loan_plan_id = int(msg)
    
    is_valid, msg = validate_numeric(amount, "Loan amount", min_val=100)
    if not is_valid:
        return jsonify({'success': False, 'message': msg}), 400
    amount = float(msg)
    
    is_valid, rel_date = validate_date(release_date, "Release date")
    if not is_valid:
        return jsonify({'success': False, 'message': rel_date}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get plan details
    cursor.execute("SELECT * FROM loan_plans WHERE id = %s", (loan_plan_id,))
    plan = cursor.fetchone()
    if not plan:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Loan plan not found.'}), 404

    cursor.execute("SELECT id FROM borrowers WHERE id = %s", (borrower_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Borrower not found.'}), 404

    cursor.execute("SELECT id FROM loan_types WHERE id = %s", (loan_type_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Loan type not found.'}), 404
    
    # Calculate loan details
    months = plan['months']
    interest_rate = float(plan['interest_rate'])
    penalty_rate = float(plan['penalty_rate'])
    
    # Monthly payment calculation (simple interest)
    total_interest = amount * (interest_rate / 100)
    total_amount = amount + total_interest
    monthly_payment = total_amount / months
    monthly_penalty = monthly_payment * (penalty_rate / 100)
    
    # Calculate maturity date
    release_dt = datetime.strptime(rel_date, '%Y-%m-%d')
    maturity_date = (release_dt + relativedelta(months=months)).strftime('%Y-%m-%d')
    
    cursor.execute("""
        INSERT INTO loans (borrower_id, loan_type_id, loan_plan_id, amount, purpose,
                           interest_rate, penalty_rate, total_interest, total_amount,
                           monthly_payment, monthly_penalty, release_date, maturity_date,
                           status, remaining_balance, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (borrower_id, loan_type_id, loan_plan_id, amount, purpose,
          interest_rate, penalty_rate, total_interest, total_amount,
          monthly_payment, monthly_penalty, rel_date, maturity_date,
          'active', total_amount, session.get('user_id')))
    
    conn.commit()
    loan_id = cursor.lastrowid
    cursor.close()
    conn.close()
    
    log_activity(session.get('user_id'), 'LOAN_CREATED', f"Created loan ID: {loan_id} for borrower ID: {borrower_id}", request.remote_addr)
    
    return jsonify({
        'success': True, 
        'message': 'Loan created successfully.',
        'loan_id': loan_id,
        'monthly_payment': round(monthly_payment, 2),
        'total_amount': round(total_amount, 2),
        'monthly_penalty': round(monthly_penalty, 2)
    })

@loan_bp.route('/<int:loan_id>')
@login_required
def get_loan(loan_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT l.*, 
               b.first_name, b.last_name, b.email, b.phone, b.address,
               lt.name as loan_type_name,
               lp.plan_name, lp.months as plan_months
        FROM loans l
        JOIN borrowers b ON l.borrower_id = b.id
        JOIN loan_types lt ON l.loan_type_id = lt.id
        JOIN loan_plans lp ON l.loan_plan_id = lp.id
        WHERE l.id = %s
    """, (loan_id,))
    loan = cursor.fetchone()
    
    if not loan:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Loan not found.'}), 404
    
    # Get payments
    cursor.execute("""
        SELECT * FROM loan_payments 
        WHERE loan_id = %s 
        ORDER BY payment_date DESC
    """, (loan_id,))
    payments = cursor.fetchall()
    
    # Get amortization schedule
    amortization = generate_amortization(loan)
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'loan': serialize_record(loan),
        'payments': serialize_records(payments),
        'amortization': amortization
    })

@loan_bp.route('/<int:loan_id>/update-status', methods=['POST'])
@login_required
def update_loan_status(loan_id):
    data = request.get_json() if request.is_json else request.form
    status = sanitize_input(data.get('status', ''))
    
    if status not in ['active', 'paid', 'defaulted', 'cancelled', 'pending']:
        return jsonify({'success': False, 'message': 'Invalid status.'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE loans SET status = %s, updated_at = NOW() WHERE id = %s", (status, loan_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    log_activity(session.get('user_id'), 'LOAN_STATUS_UPDATED', f"Updated loan ID: {loan_id} to status: {status}", request.remote_addr)
    
    return jsonify({'success': True, 'message': 'Loan status updated.'})

@loan_bp.route('/<int:loan_id>/delete', methods=['POST'])
@login_required
def delete_loan(loan_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if loan has payments
    cursor.execute("SELECT id FROM loan_payments WHERE loan_id = %s", (loan_id,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Cannot delete loan with payments.'}), 400
    
    cursor.execute("DELETE FROM loans WHERE id = %s", (loan_id,))
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Loan not found.'}), 404
    conn.commit()
    cursor.close()
    conn.close()
    
    log_activity(session.get('user_id'), 'LOAN_DELETED', f"Deleted loan ID: {loan_id}", request.remote_addr)
    
    return jsonify({'success': True, 'message': 'Loan deleted.'})

# ==================== CALCULATOR ====================

@loan_bp.route('/calculate', methods=['POST'])
@login_required
def calculate_loan():
    data = request.get_json() if request.is_json else request.form
    
    try:
        amount = float(data.get('amount', 0))
        months = int(data.get('months', 0))
        interest_rate = float(data.get('interest_rate', 0))
        penalty_rate = float(data.get('penalty_rate', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid numeric values.'}), 400
    
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Amount must be greater than 0.'}), 400
    if months <= 0:
        return jsonify({'success': False, 'message': 'Months must be greater than 0.'}), 400
    if interest_rate < 0 or interest_rate > 100:
        return jsonify({'success': False, 'message': 'Interest rate must be between 0 and 100.'}), 400
    
    # Simple interest calculation
    total_interest = amount * (interest_rate / 100)
    total_amount = amount + total_interest
    monthly_payment = total_amount / months
    monthly_penalty = monthly_payment * (penalty_rate / 100) if penalty_rate > 0 else 0
    
    # Generate amortization schedule
    schedule = []
    balance = total_amount
    payment_date = datetime.now()
    
    for month in range(1, months + 1):
        interest_portion = (amount * (interest_rate / 100)) / months
        principal_portion = monthly_payment - interest_portion
        balance -= monthly_payment
        
        payment_date = payment_date + relativedelta(months=1)
        
        schedule.append({
            'month': month,
            'payment_date': payment_date.strftime('%Y-%m-%d'),
            'monthly_payment': round(monthly_payment, 2),
            'principal': round(principal_portion, 2),
            'interest': round(interest_portion, 2),
            'balance': round(max(0, balance), 2)
        })
    
    return jsonify({
        'success': True,
        'amount': amount,
        'months': months,
        'interest_rate': interest_rate,
        'total_interest': round(total_interest, 2),
        'total_amount': round(total_amount, 2),
        'monthly_payment': round(monthly_payment, 2),
        'monthly_penalty': round(monthly_penalty, 2),
        'amortization_schedule': schedule
    })

def generate_amortization(loan):
    """Generate amortization schedule for an existing loan"""
    schedule = []
    amount = float(loan['amount'])
    months = int(loan.get('plan_months', 12))
    interest_rate = float(loan['interest_rate'])
    monthly_payment = float(loan['monthly_payment'])
    total_amount = float(loan['total_amount'])
    
    release_date = loan['release_date']
    if isinstance(release_date, str):
        current_date = datetime.strptime(release_date, '%Y-%m-%d')
    else:
        current_date = release_date
    
    balance = total_amount
    
    for month in range(1, months + 1):
        interest_portion = (amount * (interest_rate / 100)) / months
        principal_portion = monthly_payment - interest_portion
        balance -= monthly_payment
        
        current_date = current_date + relativedelta(months=1)
        
        schedule.append({
            'month': month,
            'payment_date': current_date.strftime('%Y-%m-%d'),
            'monthly_payment': round(monthly_payment, 2),
            'principal': round(principal_portion, 2),
            'interest': round(interest_portion, 2),
            'balance': round(max(0, balance), 2)
        })
    
    return schedule

@loan_bp.route('/calculate-early-payment', methods=['POST'])
@login_required
def calculate_early_payment():
    data = request.get_json() if request.is_json else request.form
    
    try:
        loan_id = int(data.get('loan_id', 0))
        extra_payment = float(data.get('extra_payment', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid values.'}), 400
    
    if extra_payment <= 0:
        return jsonify({'success': False, 'message': 'Extra payment must be greater than 0.'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM loans WHERE id = %s", (loan_id,))
    loan = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not loan:
        return jsonify({'success': False, 'message': 'Loan not found.'}), 404
    
    remaining = float(loan['remaining_balance'])
    monthly_payment = float(loan['monthly_payment'])
    
    new_balance = max(0, remaining - extra_payment)
    remaining_months = int(new_balance / monthly_payment) if monthly_payment > 0 else 0
    
    interest_saved = 0  # Simplified - would need full amortization recalculation
    
    return jsonify({
        'success': True,
        'original_balance': round(remaining, 2),
        'extra_payment': round(extra_payment, 2),
        'new_balance': round(new_balance, 2),
        'estimated_remaining_months': remaining_months,
        'interest_saved': round(interest_saved, 2)
    })


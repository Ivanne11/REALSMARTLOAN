"""
Payment Blueprint - Payment Processing, Penalty Computation
"""
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, session

from models import get_db_connection
from utils import validate_numeric, validate_date, sanitize_input, log_activity, format_currency
from decorators import login_required

payment_bp = Blueprint('payment', __name__)

ALLOWED_PAYMENT_METHODS = {'cash', 'check', 'bank_transfer', 'online'}


@payment_bp.route('/list')
@login_required
def payment_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT p.*,
               l.amount AS loan_amount, l.monthly_payment, l.monthly_penalty,
               b.first_name, b.last_name,
               u.full_name AS processed_by_name
        FROM loan_payments p
        JOIN loans l ON p.loan_id = l.id
        JOIN borrowers b ON l.borrower_id = b.id
        LEFT JOIN users u ON p.processed_by = u.id
        ORDER BY p.payment_date DESC, p.created_at DESC
        LIMIT 200
        """
    )
    payments = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('payment/list.html', payments=payments)


@payment_bp.route('/create', methods=['POST'])
@login_required
def create_payment():
    data = request.get_json() if request.is_json else request.form

    loan_id = data.get('loan_id')
    amount = data.get('amount')
    payment_date = sanitize_input(data.get('payment_date', ''))
    payment_method = sanitize_input(data.get('payment_method', 'cash'))
    notes = sanitize_input(data.get('notes', ''))

    is_valid, result = validate_numeric(loan_id, "Loan", allow_float=False, min_val=1)
    if not is_valid:
        return jsonify({'success': False, 'message': result}), 400
    loan_id = int(result)

    is_valid, result = validate_numeric(amount, "Amount", min_val=1)
    if not is_valid:
        return jsonify({'success': False, 'message': result}), 400
    amount = float(result)

    is_valid, result = validate_date(payment_date, "Payment date")
    if not is_valid:
        return jsonify({'success': False, 'message': result}), 400
    payment_date = result
    payment_dt = datetime.strptime(payment_date, '%Y-%m-%d').date()

    if payment_method not in ALLOWED_PAYMENT_METHODS:
        return jsonify({'success': False, 'message': 'Invalid payment method.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT l.*, lp.penalty_rate
        FROM loans l
        JOIN loan_plans lp ON l.loan_plan_id = lp.id
        WHERE l.id = %s
        """,
        (loan_id,)
    )
    loan = cursor.fetchone()

    if not loan:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Loan not found.'}), 404

    if loan['status'] != 'active':
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Loan is not active.'}), 400

    remaining_balance = float(loan['remaining_balance'])
    if amount > remaining_balance:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Payment amount cannot exceed the remaining balance.'}), 400

    maturity_date = loan['maturity_date']
    if isinstance(maturity_date, str):
        maturity_date = datetime.strptime(maturity_date, '%Y-%m-%d').date()

    penalty_amount = 0.0
    if payment_dt > maturity_date:
        days_overdue = (payment_dt - maturity_date).days
        penalty_rate = float(loan['penalty_rate']) / 100
        penalty_amount = round(float(loan['monthly_payment']) * penalty_rate * (days_overdue / 30), 2)

    total_payment = amount + penalty_amount
    new_balance = max(0.0, remaining_balance - amount)
    new_status = 'paid' if new_balance <= 0 else 'active'

    cursor.execute(
        """
        INSERT INTO loan_payments (
            loan_id, amount, penalty_amount, total_payment, payment_date,
            payment_method, notes, processed_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (loan_id, amount, penalty_amount, total_payment, payment_date, payment_method, notes, session.get('user_id'))
    )
    payment_id = cursor.lastrowid

    cursor.execute(
        """
        UPDATE loans
        SET remaining_balance = %s,
            total_paid = COALESCE(total_paid, 0) + %s,
            total_penalty = COALESCE(total_penalty, 0) + %s,
            last_payment_date = %s,
            status = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (new_balance, amount, penalty_amount, payment_date, new_status, loan_id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    log_activity(
        session.get('user_id'),
        'PAYMENT_CREATED',
        f"Payment of {format_currency(amount)} for loan ID: {loan_id}",
        request.remote_addr
    )

    return jsonify({
        'success': True,
        'message': 'Payment recorded successfully.',
        'payment_id': payment_id,
        'penalty_amount': penalty_amount,
        'new_balance': round(new_balance, 2),
        'status': new_status
    })


@payment_bp.route('/overdue-alerts')
@login_required
def overdue_alerts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute(
        """
        SELECT l.*,
               b.first_name, b.last_name, b.email, b.phone,
               lt.name AS loan_type_name,
               lp.plan_name, lp.penalty_rate,
               DATEDIFF(%s, l.maturity_date) AS days_overdue
        FROM loans l
        JOIN borrowers b ON l.borrower_id = b.id
        JOIN loan_types lt ON l.loan_type_id = lt.id
        JOIN loan_plans lp ON l.loan_plan_id = lp.id
        WHERE l.status = 'active'
          AND l.maturity_date < %s
          AND l.remaining_balance > 0
        ORDER BY l.maturity_date ASC
        """,
        (today, today)
    )

    overdue_loans = cursor.fetchall()

    for loan in overdue_loans:
        days_overdue = loan.get('days_overdue', 0)
        penalty_rate = float(loan['penalty_rate']) / 100
        loan['calculated_penalty'] = round(float(loan['monthly_payment']) * penalty_rate * (days_overdue / 30), 2)

    cursor.close()
    conn.close()
    return render_template('payment/overdue.html', overdue_loans=overdue_loans)


@payment_bp.route('/<int:payment_id>/reverse', methods=['POST'])
@login_required
def reverse_payment(payment_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT p.*, l.remaining_balance, l.status
        FROM loan_payments p
        JOIN loans l ON p.loan_id = l.id
        WHERE p.id = %s
        """,
        (payment_id,)
    )
    payment = cursor.fetchone()

    if not payment:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Payment not found.'}), 404

    new_balance = float(payment['remaining_balance']) + float(payment['amount'])

    cursor.execute("DELETE FROM loan_payments WHERE id = %s", (payment_id,))

    cursor.execute(
        """
        SELECT MAX(payment_date) AS last_payment_date
        FROM loan_payments
        WHERE loan_id = %s
        """,
        (payment['loan_id'],)
    )
    latest_payment = cursor.fetchone()
    last_payment_date = latest_payment['last_payment_date'] if latest_payment else None

    cursor.execute(
        """
        UPDATE loans
        SET remaining_balance = %s,
            total_paid = GREATEST(0, COALESCE(total_paid, 0) - %s),
            total_penalty = GREATEST(0, COALESCE(total_penalty, 0) - %s),
            last_payment_date = %s,
            status = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (
            new_balance,
            float(payment['amount']),
            float(payment['penalty_amount'] or 0),
            last_payment_date,
            'active' if new_balance > 0 else 'paid',
            payment['loan_id'],
        )
    )

    conn.commit()
    cursor.close()
    conn.close()

    log_activity(
        session.get('user_id'),
        'PAYMENT_REVERSED',
        f"Reversed payment ID: {payment_id}",
        request.remote_addr
    )

    return jsonify({'success': True, 'message': 'Payment reversed successfully.'})

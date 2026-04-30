"""
Dashboard Blueprint - Home Page, Analytics, Financial Metrics
"""
from flask import Blueprint, render_template, jsonify, session
from datetime import datetime, timedelta

from models import get_db_connection
from decorators import login_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/home')
@login_required
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Summary statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_loans,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_loans,
            SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_loans,
            SUM(CASE WHEN status = 'defaulted' THEN 1 ELSE 0 END) as defaulted_loans,
            SUM(total_interest) as total_interest_earned,
            SUM(total_amount - remaining_balance) as total_revenue,
            SUM(remaining_balance) as total_outstanding
        FROM loans
    """)
    summary = cursor.fetchone()
    
    # Monthly revenue for chart
    cursor.execute("""
        SELECT DATE_FORMAT(p.payment_date, '%Y-%m') as month,
               SUM(p.amount) as revenue,
               COUNT(*) as payment_count
        FROM loan_payments p
        WHERE p.payment_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(p.payment_date, '%Y-%m')
        ORDER BY month
    """)
    monthly_revenue = cursor.fetchall()
    
    # Recent loans
    cursor.execute("""
        SELECT l.*, b.first_name, b.last_name, lt.name as loan_type_name
        FROM loans l
        JOIN borrowers b ON l.borrower_id = b.id
        JOIN loan_types lt ON l.loan_type_id = lt.id
        ORDER BY l.created_at DESC
        LIMIT 5
    """)
    recent_loans = cursor.fetchall()
    
    # Recent payments
    cursor.execute("""
        SELECT p.*, b.first_name, b.last_name, lt.name as loan_type_name
        FROM loan_payments p
        JOIN loans l ON p.loan_id = l.id
        JOIN borrowers b ON l.borrower_id = b.id
        JOIN loan_types lt ON l.loan_type_id = lt.id
        ORDER BY p.payment_date DESC
        LIMIT 5
    """)
    recent_payments = cursor.fetchall()
    
    # Overdue loans count
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("""
        SELECT COUNT(*) as overdue_count
        FROM loans
        WHERE status = 'active' AND maturity_date < %s AND remaining_balance > 0
    """, (today,))
    overdue = cursor.fetchone()
    
    # Total borrowers
    cursor.execute("SELECT COUNT(*) as total_borrowers FROM borrowers")
    borrowers_count = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard/home.html',
                          summary=summary,
                          monthly_revenue=monthly_revenue,
                          recent_loans=recent_loans,
                          recent_payments=recent_payments,
                          overdue_count=overdue['overdue_count'],
                          borrowers_count=borrowers_count['total_borrowers'],
                          user_role=session.get('role'))

@dashboard_bp.route('/api/analytics')
@login_required
def analytics_api():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Loan status distribution
    cursor.execute("""
        SELECT status, COUNT(*) as count, SUM(amount) as total_amount
        FROM loans
        GROUP BY status
    """)
    status_distribution = cursor.fetchall()
    
    # Monthly loan creation vs payments
    cursor.execute("""
        SELECT DATE_FORMAT(created_at, '%Y-%m') as month,
               COUNT(*) as loans_created,
               SUM(amount) as amount_disbursed
        FROM loans
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(created_at, '%Y-%m')
        ORDER BY month
    """)
    monthly_loans = cursor.fetchall()
    
    # Default rate analytics
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'defaulted' THEN 1 ELSE 0 END) as defaulted,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid
        FROM loans
    """)
    default_stats = cursor.fetchone()
    
    total = default_stats['total'] or 1
    default_rate = (default_stats['defaulted'] / total) * 100
    
    # Risk level distribution
    cursor.execute("""
        SELECT risk_level, COUNT(*) as count
        FROM risk_assessments
        GROUP BY risk_level
    """)
    risk_distribution = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'status_distribution': status_distribution,
        'monthly_loans': monthly_loans,
        'default_rate': round(default_rate, 2),
        'default_stats': default_stats,
        'risk_distribution': risk_distribution
    })

@dashboard_bp.route('/api/notifications')
@login_required
def notifications_api():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Overdue alerts
    cursor.execute("""
        SELECT l.id, l.amount, l.maturity_date,
               b.first_name, b.last_name,
               DATEDIFF(%s, l.maturity_date) as days_overdue
        FROM loans l
        JOIN borrowers b ON l.borrower_id = b.id
        WHERE l.status = 'active' 
          AND l.maturity_date < %s
          AND l.remaining_balance > 0
        ORDER BY l.maturity_date ASC
        LIMIT 10
    """, (today, today))
    overdue = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'overdue_alerts': overdue
    })


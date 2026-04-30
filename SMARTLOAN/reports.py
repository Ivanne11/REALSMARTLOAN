"""
Reports Blueprint - PDF Generation, Performance Reports, Payment History
"""
from flask import Blueprint, render_template, request, jsonify, session, make_response
from io import BytesIO
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from models import get_db_connection
from utils import log_activity, format_currency
from decorators import login_required

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def reports_index():
    return render_template('reports/index.html')

@reports_bp.route('/amortization/<int:loan_id>/pdf')
@login_required
def export_amortization_pdf(loan_id):
    if not REPORTLAB_AVAILABLE:
        return jsonify({'success': False, 'message': 'PDF generation is not available. Please install reportlab: pip install reportlab'}), 503

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT l.*, b.first_name, b.last_name, b.email, b.phone,
               lt.name as loan_type_name, lp.plan_name, lp.months as plan_months
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

    # Generate amortization schedule
    from loan import generate_amortization
    schedule = generate_amortization(loan)

    cursor.close()
    conn.close()

    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=20)
    elements.append(Paragraph("AMORTIZATION SCHEDULE", title_style))
    elements.append(Spacer(1, 0.2*inch))

    # Loan details
    elements.append(Paragraph(f"<b>Borrower:</b> {loan['first_name']} {loan['last_name']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Loan Type:</b> {loan['loan_type_name']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Plan:</b> {loan['plan_name']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Amount:</b> {format_currency(loan['amount'])}", styles['Normal']))
    elements.append(Paragraph(f"<b>Interest Rate:</b> {loan['interest_rate']}%", styles['Normal']))
    elements.append(Paragraph(f"<b>Monthly Payment:</b> {format_currency(loan['monthly_payment'])}", styles['Normal']))
    elements.append(Paragraph(f"<b>Total Amount:</b> {format_currency(loan['total_amount'])}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))

    # Table data
    table_data = [['Month', 'Payment Date', 'Payment', 'Principal', 'Interest', 'Balance']]
    for row in schedule:
        table_data.append([
            str(row['month']),
            row['payment_date'],
            format_currency(row['monthly_payment']),
            format_currency(row['principal']),
            format_currency(row['interest']),
            format_currency(row['balance'])
        ])

    table = Table(table_data, colWidths=[0.8*inch, 1.3*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')])
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(f"<i>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    log_activity(session.get('user_id'), 'PDF_EXPORTED', f"Exported amortization PDF for loan ID: {loan_id}", request.remote_addr)

    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=amortization_loan_{loan_id}.pdf'
    return response

@reports_bp.route('/loan-performance')
@login_required
def loan_performance():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            COUNT(*) as total_loans,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_loans,
            SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_loans,
            SUM(CASE WHEN status = 'defaulted' THEN 1 ELSE 0 END) as defaulted_loans,
            SUM(amount) as total_amount_disbursed,
            SUM(total_interest) as total_interest_earned,
            SUM(total_amount - remaining_balance) as total_collected,
            SUM(remaining_balance) as total_outstanding
        FROM loans
    """)
    summary = cursor.fetchone()

    cursor.execute("""
        SELECT lt.name as loan_type_name,
               COUNT(l.id) as loan_count,
               SUM(l.amount) as total_amount,
               AVG(l.interest_rate) as avg_interest_rate
        FROM loans l
        JOIN loan_types lt ON l.loan_type_id = lt.id
        GROUP BY lt.id, lt.name
        ORDER BY loan_count DESC
    """)
    by_type = cursor.fetchall()

    cursor.execute("""
        SELECT DATE_FORMAT(created_at, '%Y-%m') as month,
               COUNT(*) as loans_created,
               SUM(amount) as amount_disbursed
        FROM loans
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(created_at, '%Y-%m')
        ORDER BY month
    """)
    monthly_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('reports/loan_performance.html', summary=summary, by_type=by_type, monthly_data=monthly_data)

@reports_bp.route('/borrower-payment-history/<int:borrower_id>')
@login_required
def borrower_payment_history(borrower_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM borrowers WHERE id = %s", (borrower_id,))
    borrower = cursor.fetchone()

    if not borrower:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Borrower not found.'}), 404

    cursor.execute("""
        SELECT l.id as loan_id, l.amount, l.monthly_payment, l.status, l.created_at as loan_date,
               lt.name as loan_type_name,
               SUM(p.amount) as total_paid,
               COUNT(p.id) as payment_count
        FROM loans l
        JOIN loan_types lt ON l.loan_type_id = lt.id
        LEFT JOIN loan_payments p ON l.id = p.loan_id
        WHERE l.borrower_id = %s
        GROUP BY l.id
        ORDER BY l.created_at DESC
    """, (borrower_id,))
    loans = cursor.fetchall()

    cursor.execute("""
        SELECT p.*, l.id as loan_id, lt.name as loan_type_name
        FROM loan_payments p
        JOIN loans l ON p.loan_id = l.id
        JOIN loan_types lt ON l.loan_type_id = lt.id
        WHERE l.borrower_id = %s
        ORDER BY p.payment_date DESC
    """, (borrower_id,))
    payments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('reports/borrower_history.html', borrower=borrower, loans=loans, payments=payments)


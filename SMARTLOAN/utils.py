"""
Utility functions for validation, encryption, and logging
"""
import re
import bcrypt
from datetime import date, datetime
from models import get_db_connection

# ==================== VALIDATION FUNCTIONS ====================

def validate_required(value, field_name="Field"):
    """Check if value is not empty or whitespace only"""
    if value is None:
        return False, f"{field_name} is required."
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False, f"{field_name} is required."
        return True, stripped
    return True, value

def validate_min_length(value, min_len, field_name="Field"):
    """Check minimum length"""
    if not isinstance(value, str):
        return False, f"{field_name} must be text."
    if len(value.strip()) < min_len:
        return False, f"{field_name} must be at least {min_len} characters."
    return True, value.strip()

def validate_max_length(value, max_len, field_name="Field"):
    """Check maximum length"""
    if not isinstance(value, str):
        return True, value
    if len(value.strip()) > max_len:
        return False, f"{field_name} must not exceed {max_len} characters."
    return True, value.strip()

def validate_username(username):
    """Validate username: 4-20 chars, alphanumeric and underscore only"""
    is_valid, msg = validate_required(username, "Username")
    if not is_valid:
        return False, msg
    is_valid, msg = validate_min_length(username, 4, "Username")
    if not is_valid:
        return False, msg
    is_valid, msg = validate_max_length(username, 20, "Username")
    if not is_valid:
        return False, msg
    if not re.match(r'^[a-zA-Z0-9_]+$', username.strip()):
        return False, "Username can only contain letters, numbers, and underscores."
    return True, username.strip()

def validate_password(password):
    """Validate password: minimum 8 chars, at least 1 uppercase, 1 lowercase, 1 number"""
    is_valid, msg = validate_required(password, "Password")
    if not is_valid:
        return False, msg
    is_valid, msg = validate_min_length(password, 8, "Password")
    if not is_valid:
        return False, msg
    pwd = password.strip()
    if not re.search(r'[A-Z]', pwd):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', pwd):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', pwd):
        return False, "Password must contain at least one number."
    return True, pwd

def validate_email(email):
    """Validate email format"""
    is_valid, msg = validate_required(email, "Email")
    if not is_valid:
        return False, msg
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email.strip()):
        return False, "Please enter a valid email address."
    return True, email.strip().lower()

def validate_name(name, field_name="Name"):
    """Validate name: letters, spaces, hyphens, apostrophes only"""
    is_valid, msg = validate_required(name, field_name)
    if not is_valid:
        return False, msg
    is_valid, msg = validate_min_length(name, 2, field_name)
    if not is_valid:
        return False, msg
    cleaned = name.strip()
    if not re.match(r"^[a-zA-Z\s'-]+$", cleaned):
        return False, f"{field_name} can only contain letters, spaces, hyphens, and apostrophes."
    return True, cleaned

def validate_phone(phone):
    """Validate phone number"""
    is_valid, msg = validate_required(phone, "Phone number")
    if not is_valid:
        return False, msg
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone.strip())
    if not re.match(r'^\+?[0-9]{7,15}$', cleaned):
        return False, "Please enter a valid phone number (7-15 digits)."
    return True, cleaned

def validate_numeric(value, field_name="Field", allow_float=True, min_val=None, max_val=None):
    """Validate numeric value"""
    is_valid, msg = validate_required(str(value), field_name)
    if not is_valid:
        return False, msg
    try:
        if allow_float:
            num = float(value)
        else:
            num = int(value)
    except ValueError:
        return False, f"{field_name} must be a valid number."
    if min_val is not None and num < min_val:
        return False, f"{field_name} must be at least {min_val}."
    if max_val is not None and num > max_val:
        return False, f"{field_name} must not exceed {max_val}."
    return True, num

def validate_date(date_str, field_name="Date"):
    """Validate date string"""
    is_valid, msg = validate_required(date_str, field_name)
    if not is_valid:
        return False, msg
    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return True, dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return False, f"{field_name} must be a valid date (YYYY-MM-DD)."

# ==================== ENCRYPTION FUNCTIONS ====================

def hash_password(password):
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def hash_sensitive_data(data):
    """Hash sensitive financial data for storage"""
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(str(data).encode('utf-8'), salt)
    return hashed.decode('utf-8')

# ==================== LOGGING FUNCTIONS ====================

def log_activity(user_id, action, details="", ip_address=""):
    """Log admin/user activity"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES (%s, %s, %s, %s)",
            (user_id, action, details, ip_address)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        # If DB is unavailable, do not raise - just log to server console
        print(f"Activity logging error: {e}")

def get_activity_logs(limit=100, user_id=None):
    """Get activity logs with optional user filter"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if user_id:
            cursor.execute("""
                SELECT al.*, u.username, u.full_name 
                FROM activity_logs al 
                LEFT JOIN users u ON al.user_id = u.id 
                WHERE al.user_id = %s 
                ORDER BY al.created_at DESC 
                LIMIT %s
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT al.*, u.username, u.full_name 
                FROM activity_logs al 
                LEFT JOIN users u ON al.user_id = u.id 
                ORDER BY al.created_at DESC 
                LIMIT %s
            """, (limit,))

        logs = cursor.fetchall()
        return logs
    except Exception as e:
        print(f"Error fetching activity logs: {e}")
        return []
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

# ==================== CREDIT SCORING ====================

def calculate_credit_score(borrower_data):
    """
    Calculate credit score based on multiple factors
    Returns score (300-850) and risk level
    """
    score = 500  # Base score
    
    # Income factor (higher income = better score)
    monthly_income = borrower_data.get('monthly_income', 0)
    if monthly_income > 100000:
        score += 100
    elif monthly_income > 50000:
        score += 60
    elif monthly_income > 25000:
        score += 30
    
    # Employment stability
    employment_status = borrower_data.get('employment_status', '').lower()
    if employment_status == 'employed':
        score += 50
    elif employment_status == 'self-employed':
        score += 30
    elif employment_status == 'contract':
        score += 15
    
    # Payment history (if exists)
    on_time_payments = borrower_data.get('on_time_payments', 0)
    total_payments = borrower_data.get('total_payments', 1)
    if total_payments > 0:
        payment_ratio = on_time_payments / total_payments
        score += int(payment_ratio * 100)
    
    # Existing loans
    active_loans = borrower_data.get('active_loans', 0)
    if active_loans == 0:
        score += 30
    elif active_loans <= 2:
        score += 10
    else:
        score -= 20 * (active_loans - 2)
    
    # Clamp score
    score = max(300, min(850, score))
    
    # Determine risk level
    if score >= 700:
        risk_level = 'Low'
    elif score >= 550:
        risk_level = 'Medium'
    else:
        risk_level = 'High'
    
    return score, risk_level

# ==================== SANITIZATION ====================

def sanitize_input(value):
    """Remove potentially dangerous characters and trim whitespace"""
    if not isinstance(value, str):
        return value
    # Trim whitespace
    cleaned = value.strip()
    # Remove null bytes
    cleaned = cleaned.replace('\x00', '')
    # Limit length
    cleaned = cleaned[:1000]
    return cleaned

def format_currency(amount):
    """Format amount as currency"""
    try:
        return "{:,.2f}".format(float(amount))
    except (ValueError, TypeError):
        return "0.00"


def serialize_value(value):
    """Convert Python date types into JSON-friendly strings."""
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    return value


def serialize_record(record):
    """Serialize a single database record dictionary."""
    return {key: serialize_value(value) for key, value in record.items()}


def serialize_records(records):
    """Serialize a list of database record dictionaries."""
    return [serialize_record(record) for record in records]


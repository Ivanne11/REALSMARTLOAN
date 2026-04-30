import os

import bcrypt
import mysql.connector
from mysql.connector import Error, errorcode

from config import Config

DEFAULT_ADMIN = {
    'username': 'admin',
    'password_hash': '$2b$10$ZA4S8DkuAeYGAa2wvztEbOTxSr99S7KhR8ZYqL9oxmOQEiWHS52C.',
    'full_name': 'System Administrator',
    'email': 'admin@smartloan.com',
    'role': 'admin',
    'status': 'active'
}

DEFAULT_LOAN_TYPES = [
    ('Personal Loan', 'For personal expenses, medical, education, etc.'),
    ('Business Loan', 'For business capital, expansion, equipment'),
    ('Home Loan', 'For home purchase, renovation, construction'),
    ('Vehicle Loan', 'For car, motorcycle, or other vehicle purchase'),
    ('Emergency Loan', 'Quick loan for urgent needs')
]

DEFAULT_LOAN_PLANS = [
    ('Short Term - 6 Months', 6, 5.00, 2.00),
    ('Standard - 12 Months', 12, 8.00, 2.00),
    ('Medium Term - 24 Months', 24, 12.00, 2.50),
    ('Long Term - 36 Months', 36, 15.00, 3.00),
    ('Extended - 48 Months', 48, 18.00, 3.00)
]

class Database:
    def __init__(self):
        self.connection = None
    
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DATABASE,
                port=Config.MYSQL_PORT,
                autocommit=False
            )
            return self.connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None
    
    def get_cursor(self, dictionary=True):
        if not self.connection or not self.connection.is_connected():
            self.connect()
        return self.connection.cursor(dictionary=dictionary)
    
    def commit(self):
        if self.connection and self.connection.is_connected():
            self.connection.commit()
    
    def rollback(self):
        if self.connection and self.connection.is_connected():
            self.connection.rollback()
    
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

db = Database()


def _get_schema_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for filename in ('workbench_schema.sql', 'database.sql'):
        candidate = os.path.join(base_dir, filename)
        if os.path.exists(candidate):
            return candidate
    return None


def _split_sql_statements(sql_text):
    return [statement.strip() for statement in sql_text.split(';') if statement.strip()]


def _seed_defaults():
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        port=Config.MYSQL_PORT,
    )
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id FROM users WHERE username = %s", (DEFAULT_ADMIN['username'],))
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, full_name, email, role, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    DEFAULT_ADMIN['username'],
                    DEFAULT_ADMIN['password_hash'],
                    DEFAULT_ADMIN['full_name'],
                    DEFAULT_ADMIN['email'],
                    DEFAULT_ADMIN['role'],
                    DEFAULT_ADMIN['status'],
                )
            )

        for name, description in DEFAULT_LOAN_TYPES:
            cursor.execute("SELECT id FROM loan_types WHERE name = %s", (name,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO loan_types (name, description) VALUES (%s, %s)",
                    (name, description)
                )

        for plan_name, months, interest_rate, penalty_rate in DEFAULT_LOAN_PLANS:
            cursor.execute("SELECT id FROM loan_plans WHERE plan_name = %s", (plan_name,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO loan_plans (plan_name, months, interest_rate, penalty_rate)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (plan_name, months, interest_rate, penalty_rate)
                )

        conn.commit()
    finally:
        cursor.close()
        conn.close()


def get_db_connection():
    """Return a raw mysql.connector connection using the shared Database helper.

    Many modules in the project expect a plain connection object from
    get_db_connection() so we return the raw connection created by
    Database.connect(). If the connection cannot be established, None is
    returned.
    """
    conn = db.connect()
    # If connection failed, db.connect() returns None. Raise a clear exception
    # so callers can handle it explicitly (instead of dereferencing None).
    if conn is None:
        raise ConnectionError("Could not connect to MySQL. Check your configuration and that the server is running.")
    return conn


def init_db():
    """Initialize the database schema and seed required lookup data."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            port=Config.MYSQL_PORT,
        )
        cursor = conn.cursor()
        schema_path = _get_schema_path()

        if not schema_path:
            print("No schema SQL file found. Expected workbench_schema.sql or database.sql.")
            return

        with open(schema_path, 'r', encoding='utf-8') as schema_file:
            for statement in _split_sql_statements(schema_file.read()):
                cursor.execute(statement)

        conn.commit()
        _seed_defaults()
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("MySQL access denied: check MYSQL_USER/MYSQL_PASSWORD in config.py")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist and could not be created.")
        else:
            print(f"init_db error: {err}")
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()

# Password hashing utilities
def hash_password(password):
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8') if isinstance(hashed, str) else hashed)

# User management
def get_user_by_username(username):
    cursor = db.get_cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()
    except Error as e:
        print(f"Error fetching user: {e}")
        return None
    finally:
        cursor.close()

def get_user_by_id(user_id):
    cursor = db.get_cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    except Error as e:
        print(f"Error fetching user: {e}")
        return None
    finally:
        cursor.close()

def create_user(username, password, full_name, email, role='user', status='active'):
    cursor = db.get_cursor()
    try:
        hashed_pwd = hash_password(password)
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, full_name, email, role, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (username, hashed_pwd, full_name, email, role, status)
        )
        db.commit()
        return cursor.lastrowid
    except Error as e:
        db.rollback()
        print(f"Error creating user: {e}")
        return None
    finally:
        cursor.close()
   

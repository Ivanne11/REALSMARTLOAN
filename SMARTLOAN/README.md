# SmartLoan - Loan Management System

A comprehensive Loan Management System built with Python Flask, JavaScript, MySQL, and Bootstrap.

## Features

- **Role-based Access**: Admin and User roles with different permissions
- **Loan Types Management**: Create and manage loan categories
- **Loan Plans Management**: Define repayment terms, interest rates, penalties
- **Borrowers Management**: Track borrower profiles and credit scores
- **Loans Management**: Create loans with automatic calculations
- **Payment Management**: Record payments with automatic penalty computation
- **Advanced Loan Calculator**: Amortization schedules, early payment recalculation
- **Financial Analytics Dashboard**: Charts, metrics, and reports
- **Risk Management**: Credit scoring, risk level tagging, overdue alerts
- **PDF Reports**: Export amortization schedules
- **Security**: Input validation, SQL injection prevention, session management, activity logs

## Prerequisites

1. **XAMPP** installed with Apache and MySQL running
2. **Python 3.9+** installed
3. MySQL running on localhost:3306 with root user (no password by default)

## Setup Instructions

### 1. Clone/Extract Project
Place the project folder in your desired directory.

### 2. Set up Database
1. Open XAMPP Control Panel
2. Start **Apache** and **MySQL**
3. Open **phpMyAdmin** (http://localhost/phpmyadmin)
4. Create a database named `smartloan_db` (or import the SQL file)
5. Import `database.sql` or create the database manually

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install Flask mysql-connector-python bcrypt reportlab python-dateutil Werkzeug
```

### 4. Run the Application
```bash
python app.py
```

### 5. Access the System
Open your browser and go to: **http://localhost:5000**

### Default Login Credentials
- **Username**: `admin`
- **Password**: `Admin1234`

## Database Configuration

If your MySQL setup is different, modify `config.py`:

```python
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''  # Your MySQL password
MYSQL_DATABASE = 'smartloan_db'
MYSQL_PORT = 3306
```

## Project Structure

```
SMARTLOAN/
├── app.py                 # Main application
├── config.py              # Configuration settings
├── models.py              # Database connection
├── utils.py               # Validation, encryption, utilities
├── decorators.py          # Authentication decorators
├── auth.py                # Authentication routes
├── admin.py               # Admin management routes
├── borrower.py            # Borrower management routes
├── loan.py                # Loan management & calculator
├── payment.py             # Payment processing routes
├── reports.py             # Reports & PDF generation
├── dashboard.py           # Dashboard & analytics
├── database.sql           # Database schema
├── requirements.txt       # Python dependencies
├── static/                # Static files (CSS, JS)
│   ├── css/style.css
│   └── js/
│       ├── validation.js
│       └── app.js
└── templates/             # HTML templates
    ├── base.html
    ├── auth/login.html
    ├── dashboard/home.html
    ├── admin/
    │   ├── users.html
    │   ├── loan_types.html
    │   ├── loan_plans.html
    │   └── activity_logs.html
    ├── borrower/list.html
    ├── loan/list.html
    ├── payment/
    │   ├── list.html
    │   └── overdue.html
    ├── reports/
    │   ├── index.html
    │   ├── loan_performance.html
    │   └── borrower_history.html
    └── errors/
        ├── 404.html
        └── 500.html
```

## Security Features

- **Input Validation**: Frontend (JavaScript) and backend (Python) validation
- **Password Hashing**: Bcrypt with salt rounds
- **SQL Injection Prevention**: Parameterized queries
- **Session Management**: 30-minute timeout, secure cookies
- **Activity Logging**: All actions tracked
- **Role-based Access**: Admin/User permissions
- **XSS Protection**: Security headers

## Browser Support
- Chrome/Edge (Recommended)
- Firefox
- Safari

## Troubleshooting

**MySQL Connection Error**: Ensure XAMPP MySQL is running and credentials in config.py are correct.

**Port 5000 in use**: Change the port in app.py: `app.run(debug=True, port=5001)`

**Module not found**: Run `pip install -r requirements.txt` again.

## License
This project is for educational purposes.


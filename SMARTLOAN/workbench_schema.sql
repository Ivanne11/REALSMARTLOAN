CREATE DATABASE IF NOT EXISTS smartloan_db
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE smartloan_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    last_login DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_role (role),
    INDEX idx_users_status (status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS borrowers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50) NULL,
    email VARCHAR(100) NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    date_of_birth DATE NULL,
    gender ENUM('Male', 'Female', 'Other') NULL,
    credit_score INT NOT NULL DEFAULT 500,
    risk_level ENUM('Low', 'Medium', 'High') NOT NULL DEFAULT 'Medium',
    monthly_income DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    employment_status ENUM('Employed', 'Self-Employed', 'Contract', 'Unemployed', 'Retired') NOT NULL DEFAULT 'Employed',
    employer VARCHAR(100) NULL,
    created_by INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_borrowers_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_borrowers_risk_level (risk_level),
    INDEX idx_borrowers_credit_score (credit_score)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS loan_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS loan_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(100) NOT NULL UNIQUE,
    months INT NOT NULL,
    interest_rate DECIMAL(5, 2) NOT NULL DEFAULT 5.00,
    penalty_rate DECIMAL(5, 2) NOT NULL DEFAULT 2.00,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS loans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    borrower_id INT NOT NULL,
    loan_type_id INT NOT NULL,
    loan_plan_id INT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    purpose TEXT NULL,
    interest_rate DECIMAL(5, 2) NOT NULL,
    penalty_rate DECIMAL(5, 2) NOT NULL DEFAULT 2.00,
    total_interest DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    monthly_payment DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    monthly_penalty DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    release_date DATE NULL,
    maturity_date DATE NULL,
    last_payment_date DATE NULL,
    status ENUM('active', 'paid', 'defaulted', 'cancelled', 'pending') NOT NULL DEFAULT 'active',
    remaining_balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total_paid DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total_penalty DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    created_by INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_loans_borrower FOREIGN KEY (borrower_id) REFERENCES borrowers(id) ON DELETE RESTRICT,
    CONSTRAINT fk_loans_loan_type FOREIGN KEY (loan_type_id) REFERENCES loan_types(id) ON DELETE RESTRICT,
    CONSTRAINT fk_loans_loan_plan FOREIGN KEY (loan_plan_id) REFERENCES loan_plans(id) ON DELETE RESTRICT,
    CONSTRAINT fk_loans_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_loans_borrower (borrower_id),
    INDEX idx_loans_status (status),
    INDEX idx_loans_maturity (maturity_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS loan_payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loan_id INT NOT NULL,
    payment_date DATE NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    penalty_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    total_payment DECIMAL(12, 2) NOT NULL,
    payment_method ENUM('cash', 'check', 'bank_transfer', 'online') NOT NULL DEFAULT 'cash',
    notes TEXT NULL,
    processed_by INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_loan_payments_loan FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE RESTRICT,
    CONSTRAINT fk_loan_payments_processed_by FOREIGN KEY (processed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_loan_payments_loan (loan_id),
    INDEX idx_loan_payments_date (payment_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_activity_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_activity_logs_user (user_id),
    INDEX idx_activity_logs_action (action),
    INDEX idx_activity_logs_created (created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS risk_assessments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    borrower_id INT NOT NULL,
    credit_score INT NOT NULL,
    risk_level ENUM('Low', 'Medium', 'High') NOT NULL,
    assessment_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assessed_by INT NULL,
    notes TEXT NULL,
    CONSTRAINT fk_risk_assessments_borrower FOREIGN KEY (borrower_id) REFERENCES borrowers(id) ON DELETE CASCADE,
    CONSTRAINT fk_risk_assessments_assessed_by FOREIGN KEY (assessed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_risk_assessments_borrower (borrower_id)
) ENGINE=InnoDB;

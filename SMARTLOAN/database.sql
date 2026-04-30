CREATE DATABASE IF NOT EXISTS smartloan_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smartloan_db;

-- =====================================================
-- 1. USERS TABLE (Admin & User Roles)
-- =====================================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role ENUM('admin','user') DEFAULT 'user',
    status ENUM('active','inactive') DEFAULT 'active',
    last_login DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_role (role),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- =====================================================
-- 2. BORROWERS TABLE
-- =====================================================
CREATE TABLE borrowers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50) NULL,
    email VARCHAR(100) NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    date_of_birth DATE NULL,
    gender ENUM('Male','Female','Other') NULL,
    credit_score INT DEFAULT 500,
    risk_level ENUM('Low','Medium','High') DEFAULT 'Medium',
    monthly_income DECIMAL(12,2) DEFAULT 0.00,
    employment_status ENUM('Employed','Self-Employed','Contract','Unemployed','Retired') DEFAULT 'Employed',
    employer VARCHAR(100) NULL,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_risk_level (risk_level),
    INDEX idx_credit_score (credit_score)
) ENGINE=InnoDB;

-- =====================================================
-- 3. LOAN TYPES TABLE
-- =====================================================
CREATE TABLE loan_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =====================================================
-- 4. LOAN PLANS TABLE
-- =====================================================
CREATE TABLE loan_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(100) NOT NULL,
    months INT NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL DEFAULT 5.00,
    penalty_rate DECIMAL(5,2) NOT NULL DEFAULT 2.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =====================================================
-- 5. LOANS TABLE
-- =====================================================
CREATE TABLE loans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    borrower_id INT NOT NULL,
    loan_type_id INT NOT NULL,
    loan_plan_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    purpose TEXT NULL,
    interest_rate DECIMAL(5,2) NOT NULL,
    penalty_rate DECIMAL(5,2) NOT NULL DEFAULT 2.00,
    total_interest DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    monthly_payment DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    monthly_penalty DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    release_date DATE NULL,
    maturity_date DATE NULL,
    last_payment_date DATE NULL,
    status ENUM('active','paid','defaulted','cancelled','pending') DEFAULT 'active',
    remaining_balance DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    total_paid DECIMAL(12,2) DEFAULT 0.00,
    total_penalty DECIMAL(12,2) DEFAULT 0.00,
    created_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (borrower_id) REFERENCES borrowers(id) ON DELETE RESTRICT,
    FOREIGN KEY (loan_type_id) REFERENCES loan_types(id) ON DELETE RESTRICT,
    FOREIGN KEY (loan_plan_id) REFERENCES loan_plans(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_borrower (borrower_id),
    INDEX idx_status (status),
    INDEX idx_maturity (maturity_date)
) ENGINE=InnoDB;

-- =====================================================
-- 6. LOAN PAYMENTS TABLE
-- =====================================================
CREATE TABLE loan_payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loan_id INT NOT NULL,
    payment_date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    penalty_amount DECIMAL(12,2) DEFAULT 0.00,
    total_payment DECIMAL(12,2) NOT NULL,
    payment_method ENUM('cash','check','bank_transfer','online') DEFAULT 'cash',
    notes TEXT NULL,
    processed_by INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE RESTRICT,
    FOREIGN KEY (processed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_loan (loan_id),
    INDEX idx_payment_date (payment_date)
) ENGINE=InnoDB;

-- =====================================================
-- 7. ACTIVITY LOGS TABLE
-- =====================================================
CREATE TABLE activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- =====================================================
-- 8. RISK ASSESSMENTS TABLE
-- =====================================================
CREATE TABLE risk_assessments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    borrower_id INT NOT NULL,
    credit_score INT NOT NULL,
    risk_level ENUM('Low','Medium','High') NOT NULL,
    assessment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    assessed_by INT NULL,
    notes TEXT NULL,
    FOREIGN KEY (borrower_id) REFERENCES borrowers(id) ON DELETE CASCADE,
    FOREIGN KEY (assessed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_borrower (borrower_id)
) ENGINE=InnoDB;

-- =====================================================
-- DEFAULT DATA
-- =====================================================

-- Default admin user (password: Admin1234)
INSERT INTO users (username, password_hash, full_name, email, role, status) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMyzJ/I1K', 'System Administrator', 'admin@smartloan.com', 'admin', 'active');

-- Sample loan types
INSERT INTO loan_types (name, description) VALUES
('Personal Loan', 'For personal expenses, medical, education, etc.'),
('Business Loan', 'For business capital, expansion, equipment'),
('Home Loan', 'For home purchase, renovation, construction'),
('Vehicle Loan', 'For car, motorcycle, or other vehicle purchase'),
('Emergency Loan', 'Quick loan for urgent needs');

-- Sample loan plans
INSERT INTO loan_plans (plan_name, months, interest_rate, penalty_rate) VALUES
('Short Term - 6 Months', 6, 5.00, 2.00),
('Standard - 12 Months', 12, 8.00, 2.00),
('Medium Term - 24 Months', 24, 12.00, 2.50),
('Long Term - 36 Months', 36, 15.00, 3.00),
('Extended - 48 Months', 48, 18.00, 3.00);

-- Sample borrowers
INSERT INTO borrowers (first_name, last_name, email, phone, address, date_of_birth, gender, monthly_income, employment_status, employer) VALUES
('Juan', 'Dela Cruz', 'juan@email.com', '09171234567', '123 Main St, Manila', '1985-03-15', 'Male', 35000.00, 'Employed', 'ABC Corporation'),
('Maria', 'Santos', 'maria@email.com', '09187654321', '456 Oak Ave, Quezon City', '1990-07-22', 'Female', 42000.00, 'Employed', 'XYZ Company'),
('Pedro', 'Reyes', 'pedro@email.com', '09199887766', '789 Pine Rd, Makati', '1978-11-05', 'Male', 55000.00, 'Self-Employed', 'Reyes Trading'),
('Ana', 'Garcia', 'ana@email.com', '09195544332', '321 Elm St, Pasig', '1995-01-10', 'Female', 28000.00, 'Contract', 'Tech Solutions Inc.');

-- Sample loans
INSERT INTO loans (borrower_id, loan_type_id, loan_plan_id, amount, purpose, interest_rate, penalty_rate, total_interest, total_amount, monthly_payment, monthly_penalty, release_date, maturity_date, status, remaining_balance, created_by) VALUES
(1, 1, 2, 50000.00, 'Medical expenses', 8.00, 2.00, 4000.00, 54000.00, 4500.00, 90.00, '2024-01-15', '2025-01-15', 'active', 36000.00, 1),
(2, 2, 3, 100000.00, 'Business expansion', 12.00, 2.50, 12000.00, 112000.00, 4666.67, 116.67, '2024-02-01', '2026-02-01', 'active', 84000.00, 1),
(3, 1, 1, 25000.00, 'Emergency fund', 5.00, 2.00, 1250.00, 26250.00, 4375.00, 87.50, '2024-03-10', '2024-09-10', 'paid', 0.00, 1),
(4, 4, 2, 75000.00, 'Car down payment', 8.00, 2.00, 6000.00, 81000.00, 6750.00, 135.00, '2024-04-01', '2025-04-01', 'active', 54000.00, 1);

-- Sample payments
INSERT INTO loan_payments (loan_id, payment_date, amount, penalty_amount, total_payment, payment_method, notes, processed_by) VALUES
(1, '2024-02-15', 4500.00, 0.00, 4500.00, 'cash', 'First payment', 1),
(1, '2024-03-15', 4500.00, 0.00, 4500.00, 'bank_transfer', 'Second payment', 1),
(1, '2024-04-15', 4500.00, 0.00, 4500.00, 'cash', 'Third payment', 1),
(2, '2024-03-01', 4666.67, 0.00, 4666.67, 'check', 'First payment', 1),
(2, '2024-04-01', 4666.67, 0.00, 4666.67, 'bank_transfer', 'Second payment', 1),
(3, '2024-04-10', 4375.00, 0.00, 4375.00, 'cash', 'First payment', 1),
(3, '2024-05-10', 4375.00, 0.00, 4375.00, 'cash', 'Second payment', 1),
(3, '2024-06-10', 4375.00, 0.00, 4375.00, 'cash', 'Final payment', 1),
(4, '2024-05-01', 6750.00, 0.00, 6750.00, 'bank_transfer', 'First payment', 1),
(4, '2024-06-01', 6750.00, 0.00, 6750.00, 'bank_transfer', 'Second payment', 1);

-- Sample risk assessments
INSERT INTO risk_assessments (borrower_id, credit_score, risk_level, assessed_by, notes) VALUES
(1, 720, 'Low', 1, 'Stable employment, good payment history'),
(2, 650, 'Medium', 1, 'Good income, new borrower'),
(3, 780, 'Low', 1, 'Self-employed with consistent income'),
(4, 580, 'Medium', 1, 'Contract work, variable income');

-- Sample activity logs
INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES
(1, 'LOGIN', 'System initialized', '127.0.0.1'),
(1, 'USER_CREATED', 'Default admin account created', '127.0.0.1'),
(1, 'BORROWER_CREATED', 'Created borrower: Juan Dela Cruz', '127.0.0.1'),
(1, 'LOAN_CREATED', 'Created loan ID 1 for borrower ID 1', '127.0.0.1'),
(1, 'PAYMENT_CREATED', 'Payment of 4,500.00 for loan ID 1', '127.0.0.1');


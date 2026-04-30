/**
 * SmartLoan - Main Application JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        });
    }, 5000);

    if (document.querySelector('.login-page')) {
        history.pushState(null, null, location.href);
        window.addEventListener('popstate', function() {
            history.pushState(null, null, location.href);
        });
    }
});

async function apiRequest(url, options = {}) {
    const defaultHeaders = {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    };

    const merged = { ...options };
    merged.headers = { ...defaultHeaders, ...(options.headers || {}) };

    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
        merged.body = JSON.stringify(options.body);
    }

    const response = await fetch(url, merged);
    const data = await response.json();

    if (!response.ok || data.success === false) {
        throw new Error(data.message || 'Request failed');
    }

    return data;
}

function populateForm(form, data) {
    Object.keys(data).forEach(key => {
        const input = form.querySelector(`[name="${key}"]`);
        if (!input) {
            return;
        }

        if (input.type === 'checkbox') {
            input.checked = Boolean(data[key]);
        } else {
            input.value = data[key] ?? '';
        }
    });
}

function clearFormValidation(form) {
    if (!form) {
        return;
    }

    form.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
        el.classList.remove('is-valid', 'is-invalid');
    });

    form.querySelectorAll('.invalid-feedback').forEach(el => {
        el.textContent = '';
        el.style.display = 'none';
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function setupTableSearch(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) {
        return;
    }

    input.addEventListener('input', debounce(function() {
        const term = this.value.toLowerCase();
        table.querySelectorAll('tbody tr').forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(term) ? '' : 'none';
        });
    }, 300));
}

function showAlert(type, message) {
    const main = document.querySelector('main');
    if (!main) {
        return;
    }

    const wrapper = document.createElement('div');
    wrapper.className = `alert alert-${type} alert-dismissible fade show`;
    wrapper.setAttribute('role', 'alert');
    wrapper.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    main.prepend(wrapper);

    setTimeout(() => {
        const alert = bootstrap.Alert.getOrCreateInstance(wrapper);
        alert.close();
    }, 5000);
}

function setLoading(button, isLoading) {
    if (!button) {
        return;
    }

    button.disabled = isLoading;

    const spinner = button.querySelector('.spinner-border');
    const text = button.querySelector('.btn-text');

    if (spinner) {
        spinner.classList.toggle('d-none', !isLoading);
    }
    if (text) {
        text.classList.toggle('opacity-50', isLoading);
    }
}

function formatCurrency(amount) {
    const value = Number(amount || 0);
    return new Intl.NumberFormat('en-PH', {
        style: 'currency',
        currency: 'PHP',
        minimumFractionDigits: 2
    }).format(value);
}

function confirmLogout(event) {
    if (!window.confirm('Mag-logout ka na ba?')) {
        event.preventDefault();
        return false;
    }
    return true;
}

async function loadNotifications() {
    const badge = document.getElementById('overdue-badge');
    if (!badge) {
        return;
    }

    try {
        const result = await apiRequest('/dashboard/api/notifications', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const count = Array.isArray(result.overdue_alerts) ? result.overdue_alerts.length : 0;
        badge.textContent = count > 0 ? count : '';
        badge.classList.toggle('d-none', count === 0);
    } catch (error) {
        badge.textContent = '';
        badge.classList.add('d-none');
    }
}

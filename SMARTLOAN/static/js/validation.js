/**
 * SmartLoan - Form Validation Helpers
 */

const validationPatterns = {
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    username: /^[a-zA-Z0-9_]{4,20}$/,
    password: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/,
    name: /^[a-zA-Z\s'-]{2,}$/,
    phone: /^\+?[0-9]{7,15}$/
};

function getValidationMessage(input) {
    const value = typeof input.value === 'string' ? input.value.trim() : input.value;
    const validator = input.dataset.validate;

    if (input.hasAttribute('required') && !value) {
        return 'This field is required.';
    }

    if (!value) {
        return '';
    }

    if (input.dataset.minlength && value.length < Number(input.dataset.minlength)) {
        return `Minimum length is ${input.dataset.minlength} characters.`;
    }

    if (input.dataset.maxlength && value.length > Number(input.dataset.maxlength)) {
        return `Maximum length is ${input.dataset.maxlength} characters.`;
    }

    switch (validator) {
        case 'required':
            return value ? '' : 'This field is required.';
        case 'email':
            return validationPatterns.email.test(value) ? '' : 'Please enter a valid email address.';
        case 'username':
            return validationPatterns.username.test(value)
                ? ''
                : 'Username must be 4-20 characters and use letters, numbers, or underscores only.';
        case 'password':
            return validationPatterns.password.test(value)
                ? ''
                : 'Password must be at least 8 characters with uppercase, lowercase, and a number.';
        case 'name':
            return validationPatterns.name.test(value)
                ? ''
                : 'Please enter at least 2 valid letters.';
        case 'phone': {
            const compact = value.replace(/[\s().-]/g, '');
            return validationPatterns.phone.test(compact) ? '' : 'Please enter a valid phone number.';
        }
        case 'numeric': {
            const numberValue = Number(value);
            if (Number.isNaN(numberValue)) {
                return 'Please enter a valid number.';
            }
            if (input.min && numberValue < Number(input.min)) {
                return `Value must be at least ${input.min}.`;
            }
            if (input.max && numberValue > Number(input.max)) {
                return `Value must not exceed ${input.max}.`;
            }
            return '';
        }
        case 'integer': {
            const numberValue = Number(value);
            if (!Number.isInteger(numberValue)) {
                return 'Please enter a whole number.';
            }
            if (input.min && numberValue < Number(input.min)) {
                return `Value must be at least ${input.min}.`;
            }
            if (input.max && numberValue > Number(input.max)) {
                return `Value must not exceed ${input.max}.`;
            }
            return '';
        }
        default:
            return '';
    }
}

function setFieldValidationState(input, errorMessage) {
    const feedback = input.parentElement.querySelector('.invalid-feedback') || input.nextElementSibling;
    const isValid = !errorMessage;

    input.classList.toggle('is-valid', isValid && input.value.trim() !== '');
    input.classList.toggle('is-invalid', !isValid);

    if (feedback && feedback.classList.contains('invalid-feedback')) {
        feedback.textContent = errorMessage;
        feedback.style.display = errorMessage ? 'block' : 'none';
    }

    return isValid;
}

function validateField(input) {
    const errorMessage = getValidationMessage(input);
    return setFieldValidationState(input, errorMessage);
}

function validateForm(form) {
    if (!form) {
        return false;
    }

    const inputs = form.querySelectorAll('input, select, textarea');
    let isValid = true;

    inputs.forEach(input => {
        if (!validateField(input)) {
            isValid = false;
        }
    });

    return isValid;
}

function setupRealTimeValidation(form) {
    if (!form) {
        return;
    }

    form.querySelectorAll('input, select, textarea').forEach(input => {
        input.addEventListener('input', () => validateField(input));
        input.addEventListener('change', () => validateField(input));
        input.addEventListener('blur', () => validateField(input));
    });
}

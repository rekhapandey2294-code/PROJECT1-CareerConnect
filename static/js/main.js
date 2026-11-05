// CareerConnect - Main Frontend Script

document.addEventListener('DOMContentLoaded', function () {
    // 1. Initialize Bootstrap Tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 2. Auto-dismiss Alert Messages after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // 3. Delete Confirmation Dialogs
    const deleteForms = document.querySelectorAll('form.confirm-delete');
    deleteForms.forEach(function (form) {
        form.addEventListener('submit', function (e) {
            const message = form.getAttribute('data-confirm-message') || 'Are you sure you want to delete this item? This action cannot be undone.';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // 4. File Size & Type Validation for File Inputs
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function (input) {
        input.addEventListener('change', function () {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                const maxSizeBytes = 5 * 1024 * 1024; // 5 MB
                const allowedExtensions = ['pdf', 'doc', 'docx'];
                const fileExt = file.name.split('.').pop().toLowerCase();

                if (!allowedExtensions.includes(fileExt)) {
                    alert('Invalid file format! Please upload a PDF, DOC, or DOCX document.');
                    this.value = '';
                    return;
                }

                if (file.size > maxSizeBytes) {
                    alert('File is too large! Maximum allowed size is 5MB.');
                    this.value = '';
                    return;
                }
            }
        });
    });

    // 5. Signup Password Match Visual Feedback
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirm_password');
        const feedback = document.getElementById('passwordFeedback');

        function checkMatch() {
            if (!confirmPasswordInput.value) {
                feedback.textContent = '';
                return;
            }
            if (passwordInput.value === confirmPasswordInput.value) {
                feedback.textContent = '✓ Passwords match';
                feedback.className = 'form-text text-success fw-semibold';
            } else {
                feedback.textContent = '✗ Passwords do not match';
                feedback.className = 'form-text text-danger fw-semibold';
            }
        }

        passwordInput.addEventListener('input', checkMatch);
        confirmPasswordInput.addEventListener('input', checkMatch);
    }
});

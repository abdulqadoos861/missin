// Toggle password visibility
document.addEventListener('DOMContentLoaded', function() {
    const togglePassword = document.querySelectorAll('.toggle-password');
    
    togglePassword.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input');
            const icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
    
    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Add your form validation logic here
            // For demo purposes, we'll just prevent submission
            e.preventDefault();
            alert('Form submitted successfully!');
        });
    });
    
    // For crime reporting page - hide/show reporter info based on anonymous checkbox
    const anonymousCheckbox = document.getElementById('anonymous');
    if (anonymousCheckbox) {
        anonymousCheckbox.addEventListener('change', function() {
            const reporterInfo = document.getElementById('reporterInfo');
            if (this.checked) {
                reporterInfo.style.display = 'none';
            } else {
                reporterInfo.style.display = 'block';
            }
        });
    }
});
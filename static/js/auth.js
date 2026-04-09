document.addEventListener('DOMContentLoaded', () => {
    // Helper to get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrftoken = getCookie('csrftoken');

    // Validation Helpers
    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    function checkPasswordStrength(password) {
        let strength = 0;
        if (password.length >= 8) strength++;
        if (/[A-Z]/.test(password) && /[a-z]/.test(password)) strength++;
        if (/[0-9]/.test(password) || /[^A-Za-z0-9]/.test(password)) strength++;
        return strength;
    }

    function updatePasswordFeedback(password) {
        const feedback = document.getElementById('password-strength');
        if (!password) {
            feedback.classList.add('hidden');
            return;
        }
        feedback.classList.remove('hidden');
        const strength = checkPasswordStrength(password);
        if (strength <= 1) {
            feedback.innerText = 'Weak (Needs numbers/caps)';
            feedback.className = 'password-strength-text strength-weak';
        } else if (strength === 2) {
            feedback.innerText = 'Medium';
            feedback.className = 'password-strength-text strength-medium';
        } else {
            feedback.innerText = 'Strong';
            feedback.className = 'password-strength-text strength-strong';
        }
    }

    const passwordInput = document.getElementById('password');
    if (passwordInput) {
        passwordInput.addEventListener('input', (e) => updatePasswordFeedback(e.target.value));
    }

    function showFeedback(elementId, message, type) {
        const feedback = document.getElementById(elementId);
        feedback.innerText = message;
        feedback.className = `feedback feedback-${type}`;
        feedback.classList.remove('hidden');
    }

    // Handle Login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = loginForm.querySelector('button[type="submit"]');

            const formData = new FormData(loginForm);
            const data = Object.fromEntries(formData.entries());

            // Client-side validation
            if (!data.username || !data.password) {
                showFeedback('login-feedback', 'Please fill in all fields.', 'error');
                return;
            }

            try {
                submitBtn.disabled = true;
                submitBtn.innerText = 'Logging in...';
                document.getElementById('login-feedback').classList.add('hidden');

                const response = await fetch('/accounts/api/v1/login/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    localStorage.setItem('auth_token', result.token);
                    localStorage.setItem('user_role', result.role);
                    
                    showFeedback('login-feedback', 'Login successful! Redirecting...', 'success');
                    
                    setTimeout(() => {
                        window.location.href = '/'; // Redirection is handled by home view based on role
                    }, 1000);
                } else {
                    showFeedback('login-feedback', result.error || 'Invalid credentials.', 'error');
                }
            } catch (error) {
                console.error('Login error:', error);
                showFeedback('login-feedback', 'An error occurred. Please try again.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerText = 'Log in';
            }
        });
    }

    // Handle Registration
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = registerForm.querySelector('button[type="submit"]');
            const feedbackId = 'register-feedback';

            const formData = new FormData(registerForm);
            const rawData = Object.fromEntries(formData.entries());

            // Client-side validation
            if (!rawData.username || !rawData.email || !rawData.password || !rawData.confirm_password) {
                showFeedback(feedbackId, 'Username, Email, and Passwords are required.', 'error');
                return;
            }

            if (rawData.password !== rawData.confirm_password) {
                showFeedback(feedbackId, 'Passwords do not match.', 'error');
                return;
            }

            if (!validateEmail(rawData.email)) {
                showFeedback(feedbackId, 'Please enter a valid email address.', 'error');
                return;
            }

            if (rawData.password.length < 8) {
                showFeedback(feedbackId, 'Password must be at least 8 characters.', 'error');
                return;
            }

            // Role specific logic
            const isCustomer = rawData.is_customer === 'true';
            const isProducer = rawData.is_producer === 'true';

            const data = {
                username: rawData.username,
                email: rawData.email,
                password: rawData.password,
                first_name: rawData.first_name,
                last_name: rawData.last_name,
                phone_number: rawData.phone_number,
                is_customer: isCustomer,
                is_producer: isProducer,
            };

            if (isCustomer) {
                data.customer_profile = { 
                    delivery_address: rawData.delivery_address,
                    postcode: rawData.customer_postcode 
                };
            } else if (isProducer) {
                if (!rawData.business_name || !rawData.business_address) {
                    showFeedback(feedbackId, 'Producers must provide business details.', 'error');
                    return;
                }
                data.producer_profile = {
                    business_name: rawData.business_name,
                    business_address: rawData.business_address,
                    tax_id: rawData.tax_id,
                    farm_origin: rawData.farm_origin,
                    postcode: rawData.producer_postcode
                };
            }

            try {
                submitBtn.disabled = true;
                submitBtn.innerText = 'Creating account...';
                document.getElementById(feedbackId).classList.add('hidden');

                const response = await fetch('/accounts/api/v1/register/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    localStorage.setItem('auth_token', result.token);
                    localStorage.setItem('user_role', result.role);
                    
                    showFeedback(feedbackId, 'Account created! Welcome!', 'success');
                    
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1500);
                } else {
                    let errorMsg = result.error || 'Registration failed.';
                    if (result.email) {
                        errorMsg = result.email[0].includes('already exists') 
                            ? 'This email is already registered.' 
                            : result.email[0];
                    }
                    else if (result.username) {
                        errorMsg = result.username[0].includes('already exists') 
                            ? 'This username is taken.' 
                            : result.username[0];
                    }
                    
                    showFeedback(feedbackId, errorMsg, 'error');
                }
            } catch (error) {
                console.error('Registration error:', error);
                showFeedback(feedbackId, 'An error occurred. Please try again.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerText = 'Sign up';
            }
        });
    }
});

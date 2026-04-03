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

    // Handle Login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const feedback = document.getElementById('login-feedback');
            const submitBtn = loginForm.querySelector('button[type="submit"]');

            const formData = new FormData(loginForm);
            const data = Object.fromEntries(formData.entries());

            try {
                submitBtn.disabled = true;
                submitBtn.innerText = 'Logging in...';
                feedback.classList.add('hidden');

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
                    feedback.innerText = 'Login successful! Redirecting...';
                    feedback.className = 'feedback feedback-success';
                    feedback.classList.remove('hidden');
                    
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1000);
                } else {
                    feedback.innerText = result.error || 'Invalid credentials. Please try again.';
                    feedback.className = 'feedback feedback-error';
                    feedback.classList.remove('hidden');
                }
            } catch (error) {
                console.error('Login error:', error);
                feedback.innerText = 'An error occurred. Please try again later.';
                feedback.className = 'feedback feedback-error';
                feedback.classList.remove('hidden');
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
            const feedback = document.getElementById('register-feedback');
            const submitBtn = registerForm.querySelector('button[type="submit"]');

            const formData = new FormData(registerForm);
            const rawData = Object.fromEntries(formData.entries());

            // Structure the data for the backend
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
                    delivery_address: rawData.delivery_address
                };
            } else if (isProducer) {
                data.producer_profile = {
                    business_name: rawData.business_name,
                    business_address: rawData.business_address,
                    tax_id: rawData.tax_id,
                    farm_origin: rawData.farm_origin
                };
            }

            try {
                submitBtn.disabled = true;
                submitBtn.innerText = 'Creating account...';
                feedback.classList.add('hidden');

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
                    feedback.innerText = 'Registration successful! Welcome!';
                    feedback.className = 'feedback feedback-success';
                    feedback.classList.remove('hidden');
                    
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1500);
                } else {
                    // Flatten error messages if possible
                    let errorMsg = 'Registration failed. Please check your details.';
                    if (result.email) errorMsg = result.email[0];
                    if (result.username) errorMsg = result.username[0];
                    
                    feedback.innerText = errorMsg;
                    feedback.className = 'feedback feedback-error';
                    feedback.classList.remove('hidden');
                }
            } catch (error) {
                console.error('Registration error:', error);
                feedback.innerText = 'An error occurred. Please try again later.';
                feedback.className = 'feedback feedback-error';
                feedback.classList.remove('hidden');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerText = 'Sign up';
            }
        });
    }

    // Handle Logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            const token = localStorage.getItem('auth_token');
            
            try {
                const response = await fetch('/accounts/api/v1/logout/', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Token ${token}`,
                        'X-CSRFToken': csrftoken
                    }
                });

                if (response.ok || response.status === 401) {
                    localStorage.removeItem('auth_token');
                    window.location.reload();
                }
            } catch (error) {
                console.error('Logout error:', error);
                // Force logout even if API fails
                localStorage.removeItem('auth_token');
                window.location.reload();
            }
        });
    }
});

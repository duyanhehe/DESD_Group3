document.addEventListener('DOMContentLoaded', () => {
    fetchProfileData();

    document.getElementById('profile-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await updateProfile();
    });
});

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

// Lightweight toast (reusing cart.js pattern)
window.showToast = function(message, type = 'error') {
    const existing = document.getElementById('fn-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'fn-toast';
    const isSuccess = type === 'success';
    toast.className = [
        'fixed bottom-6 left-1/2 -translate-x-1/2 z-[300]',
        'px-6 py-3 rounded-full shadow-xl font-bold text-sm',
        'flex items-center gap-2 transition-all',
        isSuccess ? 'bg-emerald-700 text-white' : 'bg-zinc-900 text-white'
    ].join(' ');
    toast.innerHTML = `
        <span class="material-symbols-outlined text-base">${isSuccess ? 'check_circle' : 'error'}</span>
        ${message}
    `;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(12px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

let isCustomer = false;
let isProducer = false;

async function fetchProfileData() {
    try {
        const token = localStorage.getItem('auth_token');
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        };
        if (token) headers['Authorization'] = `Token ${token}`;

        const res = await fetch('/accounts/api/v1/profile/', { headers });
        if (!res.ok) {
            window.showToast('Failed to load profile data', 'error');
            return;
        }

        const data = await res.json();
        isCustomer = data.is_customer;
        isProducer = data.is_producer;

        // Update UI based on roles
        if (isCustomer) {
            document.getElementById('delivery-info').classList.remove('hidden');
            document.getElementById('nav-delivery-info').classList.remove('hidden');
            document.getElementById('nav-delivery-info').classList.add('flex');
            document.getElementById('profile-role-badge').textContent = "Customer Account";
        }
        
        if (isProducer) {
            document.getElementById('business-info').classList.remove('hidden');
            document.getElementById('nav-business-info').classList.remove('hidden');
            document.getElementById('nav-business-info').classList.add('flex');
            document.getElementById('profile-role-badge').textContent = "Producer Account";
        }

        // Fill basic fields
        document.getElementById('first_name').value = data.first_name || '';
        document.getElementById('last_name').value = data.last_name || '';
        document.getElementById('email').value = data.email || '';
        document.getElementById('phone_number').value = data.phone_number || '';

        // Fill Customer Fields
        if (isCustomer && data.customer_profile) {
            document.getElementById('delivery_address').value = data.customer_profile.delivery_address || '';
            document.getElementById('customer_postcode').value = data.customer_profile.postcode || '';
        }

        // Fill Producer Fields
        if (isProducer && data.producer_profile) {
            document.getElementById('business_name').value = data.producer_profile.business_name || '';
            document.getElementById('farm_origin').value = data.producer_profile.farm_origin || '';
            document.getElementById('business_address').value = data.producer_profile.business_address || '';
            document.getElementById('tax_id').value = data.producer_profile.tax_id || '';
            document.getElementById('producer_postcode').value = data.producer_profile.postcode || '';
        }

    } catch (e) {
        console.error(e);
        window.showToast('Network error loading profile', 'error');
    }
}

async function updateProfile() {
    const btn = document.getElementById('save-profile-btn');
    const originalContent = btn.innerHTML;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin text-sm">sync</span> Saving...`;
    btn.disabled = true;

    // Construct Payload
    const payload = {
        first_name: document.getElementById('first_name').value,
        last_name: document.getElementById('last_name').value,
        phone_number: document.getElementById('phone_number').value,
    };

    if (isCustomer) {
        payload.customer_profile = {
            delivery_address: document.getElementById('delivery_address').value,
            postcode: document.getElementById('customer_postcode').value,
        };
    }

    if (isProducer) {
        payload.producer_profile = {
            business_name: document.getElementById('business_name').value,
            farm_origin: document.getElementById('farm_origin').value,
            business_address: document.getElementById('business_address').value,
            tax_id: document.getElementById('tax_id').value,
            postcode: document.getElementById('producer_postcode').value,
        };
    }

    try {
        const token = localStorage.getItem('auth_token');
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        };
        if (token) headers['Authorization'] = `Token ${token}`;

        const res = await fetch('/accounts/api/v1/profile/', {
            method: 'PATCH',
            headers: headers,
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            window.showToast('Profile updated successfully!', 'success');
        } else {
            const errData = await res.json();
            console.error(errData);
            window.showToast('Error updating profile. Please check your inputs.', 'error');
        }
    } catch (e) {
        console.error(e);
        window.showToast('Network error saving profile', 'error');
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

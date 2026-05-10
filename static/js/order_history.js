document.addEventListener('DOMContentLoaded', () => {
    renderOrders();
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

const statusColors = {
    'pending': 'bg-amber-100 text-amber-700',
    'confirmed': 'bg-blue-100 text-blue-700',
    'ready': 'bg-purple-100 text-purple-700',
    'delivered': 'bg-emerald-100 text-emerald-700',
    'cancelled': 'bg-rose-100 text-rose-700',
    'refund_requested': 'bg-orange-100 text-orange-700',
    'refunded': 'bg-violet-100 text-violet-700'
};

async function renderOrders() {
    const container = document.getElementById('orders-container');
    const token = localStorage.getItem('auth_token');

    const headers = {
        'Accept': 'application/json'
    };
    
    // Only add Token if it looks like a real, non-placeholder token
    const isValidToken = token && 
                         token !== 'null' && 
                         token !== 'undefined' && 
                         token.trim().length > 20;

    if (isValidToken) {
        headers['Authorization'] = `Token ${token}`;
    }

    try {
        const res = await fetch('/orders/api/v1/', { headers });

        if (res.status === 401 && isValidToken) {
            console.warn('Stored token is invalid/expired. Clearing and retrying with session...');
            localStorage.removeItem('auth_token');
            const retryRes = await fetch('/orders/api/v1/', { 
                headers: { 'Accept': 'application/json' } 
            });
            if (retryRes.ok) {
                const orders = await retryRes.json();
                renderOrderList(orders);
                return;
            }
        }

        if (!res.ok) {
            if (res.status === 401) {
                container.innerHTML = `<div class="py-20 text-center"><p class="text-on-surface-variant font-medium">Please log in to view your order history.</p></div>`;
                return;
            }
            throw new Error('Failed to fetch orders');
        }

        const orders = await res.json();

        if (orders.length === 0) {
            container.innerHTML = `
                <div class="flex flex-col items-center justify-center py-20 text-center bg-surface-container-low rounded-[32px] border border-dashed border-outline-variant/30">
                    <span class="material-symbols-outlined text-6xl text-outline mb-6">history</span>
                    <h3 class="font-headline text-2xl font-bold mb-2">No orders yet</h3>
                    <p class="text-on-surface-variant font-medium mb-8">Your purchase history will appear here once you place an order.</p>
                    <a href="/" class="px-8 py-4 bg-primary text-on-primary rounded-full font-bold shadow-xl shadow-primary/20 hover:scale-105 transition-all">Browse Marketplace</a>
                </div>
            `;
            return;
        }

        let html = '<div class="space-y-6">';
        orders.forEach(order => {
            const date = new Date(order.created_at).toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric'
            });
            const statusClass = statusColors[order.status] || 'bg-zinc-100 text-zinc-700';

            html += `
                <div class="group bg-surface-container-lowest rounded-[32px] p-8 border border-outline-variant/10 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col md:flex-row justify-between items-start md:items-center gap-8 cursor-pointer" onclick="viewOrderDetails(${order.id})">
                    <div class="flex items-center gap-6">
                        <div class="w-16 h-16 rounded-2xl bg-surface-container flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                            📦
                        </div>
                        <div>
                            <div class="flex items-center gap-3 mb-1">
                                <h3 class="font-headline font-extrabold text-on-background uppercase text-xs tracking-widest">Order #${order.id}</h3>
                                <span class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${statusClass}">${order.status.toUpperCase()}</span>
                            </div>
                            <p class="text-sm font-medium text-on-surface-variant">Placed on ${date} • ${order.sub_orders?.length || 0} Sub-orders</p>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-12 w-full md:w-auto border-t md:border-t-0 border-outline-variant/5 pt-6 md:pt-0">
                        <div class="text-left md:text-right">
                            <p class="text-[10px] font-bold text-outline uppercase tracking-widest mb-1">Total Paid</p>
                            <span class="font-black text-on-background text-2xl">$${Number(order.total_price).toFixed(2)}</span>
                        </div>
                        <button class="ml-auto md:ml-0 p-3 rounded-2xl bg-surface-container-high text-on-surface-variant hover:bg-primary hover:text-on-primary transition-all active:scale-90">
                            <span class="material-symbols-outlined text-xl">arrow_forward</span>
                        </button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;

    } catch (e) {
        console.error(e);
        container.innerHTML = `<div class="py-20 text-center text-error"><p class="font-bold">Error loading order history. Please try again.</p></div>`;
    }
}

async function viewOrderDetails(orderId) {
    const modal = document.getElementById('order-modal');
    const content = document.getElementById('order-modal-content');
    const token = localStorage.getItem('auth_token');

    content.innerHTML = `<div class="p-20 text-center flex flex-col items-center gap-4">
        <div class="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
        <p class="text-xs font-bold uppercase tracking-widest text-outline">Loading order details...</p>
    </div>`;
    modal.classList.remove('hidden');

    const headers = {};
    if (token && token !== 'null') {
        headers['Authorization'] = `Token ${token}`;
    }

    try {
        const [orderRes, historyRes] = await Promise.all([
            fetch(`/orders/api/v1/${orderId}/`, { headers }),
            fetch(`/orders/api/v1/${orderId}/history/`, { headers })
        ]);

        if (!orderRes.ok || !historyRes.ok) throw new Error('Failed to fetch details');

        const order = await orderRes.json();
        const history = await historyRes.json();

        const date = new Date(order.created_at).toLocaleString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });

        // Master orders already have flattened items from the serializer
        const allItems = order.items || [];

        let html = `
            <div class="p-10 lg:p-12">
                <div class="flex flex-col md:flex-row justify-between items-start gap-8 mb-12">
                    <div>
                        <span class="text-[10px] font-bold text-primary uppercase tracking-[0.2em] mb-3 block">Order Confirmation</span>
                        <h2 class="font-headline text-3xl font-extrabold text-on-background mb-2 tracking-tight">Receipt #${order.id}</h2>
                        <p class="text-on-surface-variant font-medium">${date}</p>
                    </div>
                    <div class="flex flex-wrap gap-3">
                        ${renderRefundButtons(order)}
                        <button onclick="reorder(${order.id})" class="px-8 py-4 bg-primary text-on-primary rounded-full font-bold text-sm shadow-xl shadow-primary/20 hover:scale-105 active:scale-95 transition-all flex items-center gap-2">
                            <span class="material-symbols-outlined text-base">refresh</span>
                            Reorder All
                        </button>
                    </div>
                </div>

                <div class="grid lg:grid-cols-5 gap-12">
                    <div class="lg:col-span-3 space-y-8">
                        <div>
                            <h4 class="font-headline font-extrabold text-[10px] uppercase tracking-[0.2em] text-outline mb-6">Line Items</h4>
                            <div class="space-y-4">
                                ${allItems.map(item => `
                                    <div class="flex justify-between items-center py-4 border-b border-outline-variant/5 last:border-0">
                                        <div class="flex items-center gap-4">
                                            <div class="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center text-lg">🛒</div>
                                            <div>
                                                <p class="font-bold text-on-background text-sm">${item.product_name}</p>
                                                <p class="text-[10px] font-bold text-primary uppercase tracking-widest">${item.producer_name}</p>
                                            </div>
                                        </div>
                                        <div class="text-right">
                                            <p class="text-sm font-black text-on-background">${item.quantity} × $${item.unit_price}</p>
                                            <p class="text-xs font-bold text-outline">$${(item.quantity * item.unit_price).toFixed(2)}</p>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                            <div class="mt-8 p-8 bg-zinc-900 rounded-3xl text-white flex justify-between items-center">
                                <span class="font-headline font-bold text-lg">Total Amount Paid</span>
                                <span class="font-black text-3xl">$${Number(order.total_price).toFixed(2)}</span>
                            </div>
                        </div>
                    </div>

                    <div class="lg:col-span-2">
                        <h4 class="font-headline font-extrabold text-[10px] uppercase tracking-[0.2em] text-outline mb-8">Fulfillment Timeline</h4>
                        <div class="relative space-y-8 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-outline-variant/20">
                            ${history.map(log => {
                                const logDate = new Date(log.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                                const logDay = new Date(log.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                                const isCurrent = log.new_status === order.status;
                                return `
                                    <div class="relative pl-10">
                                        <div class="absolute left-0 top-1 w-6 h-6 rounded-full ${isCurrent ? 'bg-primary border-4 border-primary-fixed' : 'bg-outline-variant/30'} z-10 transition-colors"></div>
                                        <div>
                                            <div class="flex items-center gap-2 mb-1">
                                                <span class="text-[10px] font-black uppercase tracking-widest ${isCurrent ? 'text-primary' : 'text-on-surface-variant'}">${log.new_status}</span>
                                                <span class="text-[10px] font-bold text-outline">${logDay} @ ${logDate}</span>
                                            </div>
                                            <p class="text-xs text-on-surface-variant font-medium leading-relaxed">${log.note || `Order transitioned to ${log.new_status}`}</p>
                                            <p class="text-[10px] text-outline mt-1 italic">Updated by ${log.changed_by_name}</p>
                                        </div>
                                    </div>
                                `;
                            }).reverse().join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
        content.innerHTML = html;

        // Initialize Refund Form listener if not already done
        const refundForm = document.getElementById('refund-form');
        if (refundForm && !refundForm.hasAttribute('data-listener')) {
            refundForm.addEventListener('submit', handleRefundSubmit);
            refundForm.setAttribute('data-listener', 'true');
            
            // Handle reason change to show/hide evidence
            document.getElementById('refund-reason-category').addEventListener('change', (e) => {
                const container = document.getElementById('evidence-upload-container');
                if (e.target.value === 'spoiled') {
                    container.classList.remove('hidden');
                    document.getElementById('refund-evidence-image').setAttribute('required', 'true');
                } else {
                    container.classList.add('hidden');
                    document.getElementById('refund-evidence-image').removeAttribute('required');
                }
            });

            // Handle file name display
            document.getElementById('refund-evidence-image').addEventListener('change', (e) => {
                const fileName = e.target.files[0]?.name || 'Click or drag to upload photo';
                document.getElementById('file-name-display').innerText = fileName;
            });
        }

    } catch (e) {
        console.error(e);
        content.innerHTML = `<div class="p-20 text-center text-error"><p class="font-bold">Error loading details.</p></div>`;
    }
}

function closeOrderModal() {
    document.getElementById('order-modal').classList.add('hidden');
}

function renderRefundButtons(order) {
    const st = order.status.toLowerCase();
    if (st === 'cancelled' || st === 'refunded' || st === 'refund_requested') {
        return '';
    }

    if (st === 'delivered') {
        // Check if within 2 days
        const deliveredAt = order.delivered_at ? new Date(order.delivered_at) : new Date(order.updated_at);
        const now = new Date();
        const diffDays = (now - deliveredAt) / (1000 * 60 * 60 * 24);
        
        if (diffDays <= 2) {
            return `
                <button onclick="openRefundModal(${order.id}, ${JSON.stringify(order.items).replace(/"/g, '&quot;')})" class="px-8 py-4 bg-surface-container-high text-on-surface rounded-full font-bold text-sm hover:bg-surface-container-highest transition-all flex items-center gap-2">
                    <span class="material-symbols-outlined text-base">assignment_return</span>
                    Return / Refund
                </button>
            `;
        }
        return '';
    }

    // Otherwise show Cancel Order (for PENDING, CONFIRMED, READY)
    return `
        <button onclick="openRefundModal(${order.id}, ${JSON.stringify(order.items).replace(/"/g, '&quot;')}, true)" class="px-8 py-4 bg-rose-50 text-rose-700 border border-rose-100 rounded-full font-bold text-sm hover:bg-rose-100 transition-all flex items-center gap-2">
            <span class="material-symbols-outlined text-base">cancel</span>
            Cancel Order
        </button>
    `;
}

function openRefundModal(orderId, items, isCancellation = false) {
    document.getElementById('refund-order-id').value = orderId;
    const title = document.getElementById('refund-modal-title');
    const reasonSelect = document.getElementById('refund-reason-category');
    const itemSelect = document.getElementById('refund-item-select');
    
    // Set title and default reason
    if (isCancellation) {
        title.innerText = "Cancel Order";
        reasonSelect.value = "not_delivered";
        // Lock to not_delivered if it's a cancellation before delivery
        Array.from(reasonSelect.options).forEach(opt => {
            opt.disabled = opt.value !== 'not_delivered';
        });
    } else {
        title.innerText = "Request Return / Refund";
        Array.from(reasonSelect.options).forEach(opt => {
            opt.disabled = opt.value === 'not_delivered';
            if (opt.value === "") opt.disabled = false;
        });
        reasonSelect.value = "";
    }

    // Populate items
    itemSelect.innerHTML = '<option value="">Entire Order</option>';
    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.id;
        opt.innerText = `${item.product_name} (${item.quantity} × $${item.unit_price})`;
        itemSelect.appendChild(opt);
    });

    // Reset evidence field
    document.getElementById('evidence-upload-container').classList.add('hidden');
    document.getElementById('refund-evidence-image').value = '';
    document.getElementById('file-name-display').innerText = 'Click or drag to upload photo';
    document.getElementById('refund-reason-text').value = '';

    document.getElementById('refund-modal').classList.remove('hidden');
}

function closeRefundModal() {
    document.getElementById('refund-modal').classList.add('hidden');
}

async function handleRefundSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const token = localStorage.getItem('auth_token');
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnContent = submitBtn.innerHTML;

    // Validation for 'other' reason
    if (formData.get('reason_category') === 'other' && !formData.get('reason_text').trim()) {
        if (window.showToast) window.showToast('Please provide details for the "Other" reason.', 'error');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="material-symbols-outlined animate-spin">sync</span> Submitting...`;

    const headers = {
        'X-CSRFToken': getCookie('csrftoken')
    };
    if (token && token !== 'null') {
        headers['Authorization'] = `Token ${token}`;
    }

    try {
        const res = await fetch('/orders/api/v1/refund/request/', {
            method: 'POST',
            headers: headers,
            body: formData
        });

        const data = await res.json();

        if (res.ok) {
            if (window.showToast) window.showToast('Refund request submitted successfully!', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            if (window.showToast) window.showToast(data.error || 'Failed to submit refund request.', 'error');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnContent;
        }
    } catch (err) {
        console.error(err);
        if (window.showToast) window.showToast('Network error during submission.', 'error');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnContent;
    }
}

async function reorder(orderId) {
    const token = localStorage.getItem('auth_token');
    
    // UI Loading state
    const btn = event.currentTarget;
    const originalContent = btn.innerHTML;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin text-base">sync</span> Adding...`;
    btn.disabled = true;

    const headers = {
        'X-CSRFToken': getCookie('csrftoken')
    };
    if (token && token !== 'null') {
        headers['Authorization'] = `Token ${token}`;
    }

    try {
        const res = await fetch(`/orders/api/v1/${orderId}/reorder/`, {
            method: 'POST',
            headers: headers
        });

        const data = await res.json();

        if (res.ok) {
            // Success toast
            if (window.showToast) {
                window.showToast(data.message, 'success');
            }
            
            // Wait a bit then redirect to cart
            setTimeout(() => {
                window.location.href = '/orders/cart/';
            }, 1500);
        } else {
            if (window.showToast) {
                window.showToast(data.error || 'Failed to reorder items.', 'error');
            }
            btn.innerHTML = originalContent;
            btn.disabled = false;
        }
    } catch (e) {
        console.error(e);
        if (window.showToast) {
            window.showToast('Network error during reorder.', 'error');
        }
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

window.reorder = reorder;
window.viewOrderDetails = viewOrderDetails;
window.closeOrderModal = closeOrderModal;
window.openRefundModal = openRefundModal;
window.closeRefundModal = closeRefundModal;

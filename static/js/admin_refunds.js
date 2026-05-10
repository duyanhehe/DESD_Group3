/**
 * Admin Refund Review Logic
 * Uses a data store to avoid inline JSON serialization issues.
 */

// Store refund data by ID for safe access from onclick handlers
let refundStore = {};
let currentRefundId = null;

document.addEventListener('DOMContentLoaded', function() {
    loadRefundRequests();

    // Event Listeners
    document.getElementById('status-filter').addEventListener('change', loadRefundRequests);
    document.getElementById('close-review-modal').addEventListener('click', closeReviewModal);
    document.getElementById('close-image-modal').addEventListener('click', () => {
        document.getElementById('image-modal').style.display = 'none';
    });
});

async function loadRefundRequests() {
    const statusVal = document.getElementById('status-filter').value;
    const tbody = document.getElementById('refunds-table-body');
    const token = localStorage.getItem('auth_token');
    
    const headers = { 'Accept': 'application/json' };
    
    if (token && token !== 'null' && token !== 'undefined' && token.length > 10) {
        headers['Authorization'] = `Token ${token}`;
    }
    
    try {
        let response = await fetch(`/orders/api/v1/refund/review/list/?status=${statusVal}`, { headers });
        
        // Retry with session auth if token fails
        if (response.status === 401 && headers['Authorization']) {
            delete headers['Authorization'];
            response = await fetch(`/orders/api/v1/refund/review/list/?status=${statusVal}`, { headers });
        }

        if (!response.ok) throw new Error('Failed to fetch refunds');
        
        const refunds = await response.json();
        renderRefundTable(refunds);
    } catch (error) {
        console.error('Error:', error);
        tbody.innerHTML = `<tr><td colspan="6" class="px-8 py-10 text-center text-red-500 font-bold">Error loading data. Please refresh.</td></tr>`;
    }
}

function renderRefundTable(refunds) {
    const tbody = document.getElementById('refunds-table-body');
    refundStore = {}; // Reset store
    
    if (refunds.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="px-8 py-20 text-center text-zinc-400 font-bold">No refund requests found.</td></tr>`;
        return;
    }

    tbody.innerHTML = refunds.map(r => {
        // Store each refund by ID for safe onclick access
        refundStore[r.id] = r;

        const date = new Date(r.created_at).toLocaleDateString();
        const amount = parseFloat(r.requested_amount).toFixed(2);
        const st = (r.status || '').toLowerCase();
        const isPending = st === 'pending';
        
        // Button label changes based on status
        const btnLabel = isPending ? 'Review' : 'View Details';
        const btnClass = isPending 
            ? 'bg-zinc-900 text-white hover:bg-zinc-700' 
            : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200';

        return `
            <tr class="border-b border-zinc-50 hover:bg-zinc-50/50 transition-colors">
                <td class="px-8 py-6 text-sm font-medium text-zinc-900">${date}</td>
                <td class="px-8 py-6">
                    <div class="flex flex-col">
                        <span class="text-sm font-bold text-zinc-900">${escapeHtml(r.customer_name)}</span>
                        <span class="text-[11px] text-zinc-400 font-medium">Order #${r.order_id}</span>
                    </div>
                </td>
                <td class="px-8 py-6">
                    <div class="flex flex-col">
                        <span class="text-sm font-bold text-zinc-900">${escapeHtml(r.item_name)}</span>
                        <span class="text-[11px] text-zinc-500 font-medium">${formatReason(r.reason_category)}</span>
                    </div>
                </td>
                <td class="px-8 py-6">
                    <span class="text-sm font-black text-zinc-900">$${amount}</span>
                </td>
                <td class="px-8 py-6">
                    <span class="status-badge status-${st}">${r.status}</span>
                </td>
                <td class="px-8 py-6 text-right">
                    <button onclick="openReviewModal(${r.id})" class="action-btn px-4 py-2 ${btnClass} rounded-lg text-xs font-bold transition-all">
                        ${btnLabel}
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function formatReason(reason) {
    const map = {
        'spoiled': 'Spoiled / Damaged',
        'fresh_return': 'Fresh Item Return',
        'not_delivered': 'Cancellation',
        'other': 'Other'
    };
    return map[reason] || reason;
}

// Escape HTML to prevent XSS and broken attributes
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function openReviewModal(refundId) {
    const refund = refundStore[refundId];
    if (!refund) {
        console.error('Refund not found in store:', refundId);
        return;
    }

    currentRefundId = refund.id;
    const details = document.getElementById('modal-details');
    const actions = document.getElementById('modal-actions');
    const adminNoteArea = document.getElementById('admin-note');
    const modalTitle = document.getElementById('modal-title');
    
    adminNoteArea.value = refund.admin_note || '';
    
    let evidenceHtml = '';
    if (refund.evidence_image) {
        evidenceHtml = `
            <div>
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-2">Evidence Photo</label>
                <img src="${escapeHtml(refund.evidence_image)}" class="evidence-preview shadow-sm border border-zinc-100" onclick="showBigImage(${refund.id})">
                <p class="text-[10px] text-zinc-400 mt-2 italic">Click to enlarge</p>
            </div>
        `;
    }

    details.innerHTML = `
        <div class="grid grid-cols-2 gap-6">
            <div>
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-1">Customer</label>
                <p class="text-sm font-bold text-zinc-900">${escapeHtml(refund.customer_name)}</p>
            </div>
            <div>
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-1">Order</label>
                <p class="text-sm font-bold text-zinc-900">#${refund.order_id}</p>
            </div>
            <div class="col-span-2">
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-1">Item / Scope</label>
                <p class="text-sm font-bold text-zinc-900">${escapeHtml(refund.item_name)}</p>
            </div>
            <div>
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-1">Reason</label>
                <p class="text-sm font-bold text-zinc-900">${formatReason(refund.reason_category)}</p>
            </div>
            <div>
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-1">Amount to Refund</label>
                <p class="text-lg font-black text-emerald-700">$${parseFloat(refund.requested_amount).toFixed(2)}</p>
            </div>
        </div>
        
        ${refund.reason_text ? `
            <div>
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-1">Customer Message</label>
                <div class="p-4 bg-zinc-50 rounded-xl border border-zinc-100 text-sm text-zinc-600 font-medium leading-relaxed">
                    ${escapeHtml(refund.reason_text)}
                </div>
            </div>
        ` : ''}
        
        ${evidenceHtml}
    `;

    // Show/Hide actions based on status
    const st = (refund.status || '').toLowerCase();
    if (st === 'pending') {
        modalTitle.innerText = 'Review Refund';
        actions.style.display = 'flex';
        adminNoteArea.disabled = false;
        
        document.getElementById('btn-modal-approve').onclick = () => submitReview('approve');
        document.getElementById('btn-modal-reject').onclick = () => submitReview('reject');
    } else {
        modalTitle.innerText = st === 'approved' ? 'Refund Approved' : 'Refund Rejected';
        actions.style.display = 'none';
        adminNoteArea.disabled = true;
    }

    document.getElementById('review-modal').style.display = 'flex';
}

function closeReviewModal() {
    document.getElementById('review-modal').style.display = 'none';
}

async function submitReview(action) {
    const approveBtn = document.getElementById('btn-modal-approve');
    const rejectBtn = document.getElementById('btn-modal-reject');
    
    // Disable buttons to prevent double-clicks
    approveBtn.disabled = true;
    rejectBtn.disabled = true;
    const originalApproveHtml = approveBtn.innerHTML;
    approveBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm align-middle">sync</span> Processing...';
    
    const adminNote = document.getElementById('admin-note').value;
    const token = localStorage.getItem('auth_token');
    
    const headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    };
    
    if (token && token !== 'null' && token !== 'undefined' && token.length > 10) {
        headers['Authorization'] = `Token ${token}`;
    }
    
    try {
        let response = await fetch(`/orders/api/v1/refund/review/${currentRefundId}/`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ action, admin_note: adminNote })
        });
        
        // Retry with session auth if token fails
        if (response.status === 401 && headers['Authorization']) {
            delete headers['Authorization'];
            response = await fetch(`/orders/api/v1/refund/review/${currentRefundId}/`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ action, admin_note: adminNote })
            });
        }

        const data = await response.json();
        
        if (response.ok) {
            notify(data.message || `Refund ${action}ed successfully`, 'success');
            closeReviewModal();
            loadRefundRequests();
        } else {
            notify(data.error || 'Failed to submit review', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        notify('Connection error. Please try again.', 'error');
    } finally {
        approveBtn.disabled = false;
        rejectBtn.disabled = false;
        approveBtn.innerHTML = originalApproveHtml;
    }
}

function showBigImage(refundId) {
    const refund = refundStore[refundId];
    if (refund && refund.evidence_image) {
        document.getElementById('big-evidence-image').src = refund.evidence_image;
        document.getElementById('image-modal').style.display = 'flex';
    }
}

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

/**
 * Non-blocking notification. Falls back to a temporary DOM toast if window.showToast is unavailable.
 */
function notify(message, type = 'info') {
    if (window.showToast) {
        window.showToast(message, type);
        return;
    }
    // Fallback: create a temporary toast element instead of blocking alert()
    const toast = document.createElement('div');
    const bgColor = type === 'success' ? '#166534' : type === 'error' ? '#991b1b' : '#1e3a5f';
    toast.style.cssText = `position:fixed;top:24px;right:24px;z-index:9999;padding:16px 24px;border-radius:16px;background:${bgColor};color:white;font-weight:700;font-size:14px;box-shadow:0 8px 30px rgba(0,0,0,0.2);transition:opacity 0.5s;`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; }, 2500);
    setTimeout(() => { toast.remove(); }, 3000);
}

// Export functions for onclick handlers in dynamically generated HTML
window.openReviewModal = openReviewModal;
window.showBigImage = showBigImage;

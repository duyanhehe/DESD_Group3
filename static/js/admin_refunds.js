/**
 * Admin Refund Review Logic
 */

document.addEventListener('DOMContentLoaded', function() {
    loadRefundRequests();

    // Event Listeners
    document.getElementById('status-filter').addEventListener('change', loadRefundRequests);
    document.getElementById('close-review-modal').addEventListener('click', closeReviewModal);
    document.getElementById('close-image-modal').addEventListener('click', () => {
        document.getElementById('image-modal').style.display = 'none';
    });
});

let currentRefundId = null;

async function loadRefundRequests() {
    const status = document.getElementById('status-filter').value;
    const tbody = document.getElementById('refunds-table-body');
    const token = localStorage.getItem('auth_token');
    
    const headers = {
        'Accept': 'application/json'
    };
    
    if (token && token !== 'null' && token !== 'undefined' && token.length > 10) {
        headers['Authorization'] = `Token ${token}`;
    }
    
    try {
        const response = await fetch(`/orders/api/v1/refund/review/list/?status=${status}`, { headers });
        
        if (response.status === 401 && headers['Authorization']) {
            // Token failed, try without it (session auth)
            delete headers['Authorization'];
            const retryRes = await fetch(`/orders/api/v1/refund/review/list/?status=${status}`, { headers });
            if (!retryRes.ok) throw new Error('Unauthorized');
            const refunds = await retryRes.json();
            renderRefundTable(refunds);
            return;
        }

        if (!response.ok) throw new Error('Failed to fetch refunds');
        
        const refunds = await response.json();
        renderRefundTable(refunds);
    } catch (error) {
        console.error('Error:', error);
        tbody.innerHTML = `<tr><td colspan="6" class="px-8 py-10 text-center text-red-500 font-bold">Error loading data.</td></tr>`;
    }
}

function renderRefundTable(refunds) {
    const tbody = document.getElementById('refunds-table-body');
    
    if (refunds.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="px-8 py-20 text-center text-zinc-400 font-bold">No refund requests found.</td></tr>`;
        return;
    }

    tbody.innerHTML = refunds.map(r => {
        const date = new Date(r.created_at).toLocaleDateString();
        const amount = parseFloat(r.requested_amount).toFixed(2);
        
        return `
            <tr class="border-b border-zinc-50 hover:bg-zinc-50/50 transition-colors">
                <td class="px-8 py-6 text-sm font-medium text-zinc-900">${date}</td>
                <td class="px-8 py-6">
                    <div class="flex flex-col">
                        <span class="text-sm font-bold text-zinc-900">${r.customer_name}</span>
                        <span class="text-[11px] text-zinc-400 font-medium">Order #${r.order_id}</span>
                    </div>
                </td>
                <td class="px-8 py-6">
                    <div class="flex flex-col">
                        <span class="text-sm font-bold text-zinc-900">${r.item_name}</span>
                        <span class="text-[11px] text-zinc-500 font-medium">${formatReason(r.reason_category)}</span>
                    </div>
                </td>
                <td class="px-8 py-6">
                    <span class="text-sm font-black text-zinc-900">$${amount}</span>
                </td>
                <td class="px-8 py-6">
                    <span class="status-badge status-${r.status.toLowerCase()}">${r.status}</span>
                </td>
                <td class="px-8 py-6 text-right">
                    <button onclick="openReviewModal(${JSON.stringify(r).replace(/"/g, '&quot;')})" class="action-btn px-4 py-2 bg-zinc-900 text-white rounded-lg text-xs font-bold hover:bg-zinc-700 transition-all">
                        Review
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

function openReviewModal(refund) {
    currentRefundId = refund.id;
    const details = document.getElementById('modal-details');
    const actions = document.getElementById('modal-actions');
    const adminNoteArea = document.getElementById('admin-note');
    
    adminNoteArea.value = refund.admin_note || '';
    
    let evidenceHtml = '';
    if (refund.evidence_image) {
        evidenceHtml = `
            <div>
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-2">Evidence Photo</label>
                <img src="${refund.evidence_image}" class="evidence-preview shadow-sm border border-zinc-100" onclick="showBigImage('${refund.evidence_image}')">
                <p class="text-[10px] text-zinc-400 mt-2 italic">Click to enlarge</p>
            </div>
        `;
    }

    details.innerHTML = `
        <div class="grid grid-cols-2 gap-6">
            <div>
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-1">Customer</label>
                <p class="text-sm font-bold text-zinc-900">${refund.customer_name}</p>
            </div>
            <div>
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-1">Order</label>
                <p class="text-sm font-bold text-zinc-900">#${refund.order_id}</p>
            </div>
            <div class="col-span-2">
                <label class="text-[10px] font-black uppercase text-zinc-400 block mb-1">Item / Scope</label>
                <p class="text-sm font-bold text-zinc-900">${refund.item_name}</p>
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
                    ${refund.reason_text}
                </div>
            </div>
        ` : ''}
        
        ${evidenceHtml}
    `;

    // Show/Hide actions based on status
    const status = refund.status.toLowerCase();
    if (status === 'pending') {
        actions.style.display = 'flex';
        adminNoteArea.disabled = false;
        
        document.getElementById('btn-modal-approve').onclick = () => submitReview('approve');
        document.getElementById('btn-modal-reject').onclick = () => submitReview('reject');
    } else {
        actions.style.display = 'none';
        adminNoteArea.disabled = true;
    }

    document.getElementById('review-modal').style.display = 'flex';
}

function closeReviewModal() {
    document.getElementById('review-modal').style.display = 'none';
}

async function submitReview(action) {
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
        const response = await fetch(`/orders/api/v1/refund/review/${currentRefundId}/`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ action, admin_note: adminNote })
        });
        
        if (response.status === 401 && headers['Authorization']) {
             delete headers['Authorization'];
             const retryRes = await fetch(`/orders/api/v1/refund/review/${currentRefundId}/`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ action, admin_note: adminNote })
            });
            const retryData = await retryRes.json();
            if (retryRes.ok) {
                showToast(retryData.message || `Refund ${action}ed successfully`, 'success');
                closeReviewModal();
                loadRefundRequests();
            } else {
                showToast(retryData.error || 'Failed to submit review', 'error');
            }
            return;
        }

        const data = await response.json();
        
        if (response.ok) {
            showToast(data.message || `Refund ${action}ed successfully`, 'success');
            closeReviewModal();
            loadRefundRequests();
        } else {
            showToast(data.error || 'Failed to submit review', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Connection error', 'error');
    }
}

function showBigImage(url) {
    document.getElementById('big-evidence-image').src = url;
    document.getElementById('image-modal').style.display = 'flex';
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

function showToast(message, type = 'info') {
    if (window.showToast) {
        window.showToast(message, type);
    } else {
        alert(message);
    }
}

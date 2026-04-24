/**
 * Producer Settlements Dashboard
 * Handles fetching and displaying weekly payouts and settlement details.
 */

let settlementsData = [];
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
    fetchSettlements();
    setupFilters();
    setupModalTabs();
});

function setupFilters() {
    const tabs = document.querySelectorAll('.status-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active', 'bg-primary', 'text-on-primary'));
            tab.classList.add('active', 'bg-primary', 'text-on-primary');
            currentFilter = tab.dataset.status;
            renderTable();
        });
    });
}

function setupModalTabs() {
    const tabs = document.querySelectorAll('.modal-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => {
                t.classList.remove('active', 'text-primary');
                t.classList.add('text-on-surface-variant');
                const indicator = t.querySelector('.tab-indicator');
                if (indicator) indicator.remove();
            });
            
            tab.classList.add('active', 'text-primary');
            tab.classList.remove('text-on-surface-variant');
            tab.innerHTML += '<div class="tab-indicator absolute bottom-0 left-0 w-full h-1 bg-primary rounded-full"></div>';
            
            const target = tab.dataset.target;
            document.querySelectorAll('.modal-content').forEach(c => c.classList.add('hidden'));
            document.getElementById(target).classList.remove('hidden');
        });
    });
}

async function fetchSettlements() {
    const token = localStorage.getItem('auth_token');
    const headers = {
        'Accept': 'application/json',
    };
    
    const isValidToken = token && 
                         token !== 'null' && 
                         token !== 'undefined' && 
                         token.trim().length > 20;

    if (isValidToken) {
        headers['Authorization'] = `Token ${token}`;
    }

    try {
        const res = await fetch('/payments/api/v1/settlements/', { headers });
        
        if (res.status === 401 && isValidToken) {
            console.warn('Stored token invalid. Retrying with session...');
            localStorage.removeItem('auth_token');
            const retryRes = await fetch('/payments/api/v1/settlements/', { 
                headers: { 'Accept': 'application/json' } 
            });
            if (retryRes.ok) {
                settlementsData = await retryRes.json();
                renderStats();
                renderTable();
                return;
            }
        }
        
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        settlementsData = await res.json();
        renderStats();
        renderTable();
    } catch (e) {
        console.error(e);
        document.getElementById('settlements-tbody').innerHTML = `
            <tr>
                <td colspan="6" class="px-8 py-20 text-center">
                    <span class="material-symbols-outlined text-4xl text-error mb-4">error</span>
                    <p class="font-bold text-on-surface-variant">Failed to sync with treasury.</p>
                    <p class="text-xs text-outline mt-2">${e.message}</p>
                </td>
            </tr>
        `;
    }
}

function renderStats() {
    const totalPaid = settlementsData
        .filter(s => s.status === 'paid')
        .reduce((sum, s) => sum + parseFloat(s.payout_amount), 0);
        
    const pendingApproval = settlementsData
        .filter(s => s.status === 'calculated' || s.status === 'pending')
        .reduce((sum, s) => sum + parseFloat(s.payout_amount), 0);
        
    const approvedAmt = settlementsData
        .filter(s => s.status === 'approved')
        .reduce((sum, s) => sum + parseFloat(s.payout_amount), 0);

    document.getElementById('stat-total-paid').textContent = `$${totalPaid.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById('stat-pending-approval').textContent = `$${pendingApproval.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById('stat-approved-amt').textContent = `$${approvedAmt.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
}

function renderTable() {
    const tbody = document.getElementById('settlements-tbody');
    let filtered = [...settlementsData];
    
    if (currentFilter !== 'all') {
        filtered = filtered.filter(s => s.status === currentFilter);
    }
    
    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-8 py-20 text-center">
                    <span class="material-symbols-outlined text-4xl text-outline mb-4">payments</span>
                    <p class="font-bold text-on-surface-variant">No settlements found.</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = filtered.map(s => `
        <tr class="settlement-row group" onclick="viewSettlement('${s.id}')">
            <td class="px-8 py-6">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-surface-container-high flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-on-primary transition-all">
                        <span class="material-symbols-outlined text-xl">calendar_today</span>
                    </div>
                    <div>
                        <p class="font-black text-on-surface">${formatDateRange(s.week_start, s.week_end)}</p>
                        <p class="text-[10px] uppercase font-black text-outline tracking-wider">Settlement ID: ...${s.id.slice(-8)}</p>
                    </div>
                </div>
            </td>
            <td class="px-8 py-6 font-bold">$${parseFloat(s.total_sales).toFixed(2)}</td>
            <td class="px-8 py-6 text-rose-500 font-bold">-$${parseFloat(s.commission_amount).toFixed(2)}</td>
            <td class="px-8 py-6 font-black text-primary text-lg">$${parseFloat(s.payout_amount).toFixed(2)}</td>
            <td class="px-8 py-6">
                <span class="status-badge status-${s.status}">${s.status}</span>
            </td>
            <td class="px-8 py-6 text-right">
                <button class="w-10 h-10 rounded-full hover:bg-primary/10 text-primary transition-all">
                    <span class="material-symbols-outlined">chevron_right</span>
                </button>
            </td>
        </tr>
    `).join('');
}

async function viewSettlement(id) {
    const modal = document.getElementById('detail-modal');
    const settlement = settlementsData.find(s => s.id === id);
    
    if (!settlement) return;
    
    // Set basic info
    document.getElementById('modal-title').textContent = `Settlement Details`;
    document.getElementById('modal-period').textContent = `${formatDateRange(settlement.week_start, settlement.week_end)}`;
    document.getElementById('modal-total-sales').textContent = `$${parseFloat(settlement.total_sales).toFixed(2)}`;
    document.getElementById('modal-net-payout').textContent = `$${parseFloat(settlement.payout_amount).toFixed(2)}`;
    
    const badge = document.getElementById('modal-status-badge');
    badge.className = `status-badge status-${settlement.status}`;
    badge.textContent = settlement.status;
    
    // Clear lists
    document.getElementById('modal-items-tbody').innerHTML = '<tr><td colspan="5" class="p-8 text-center"><div class="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mx-auto"></div></td></tr>';
    document.getElementById('modal-audit-list').innerHTML = '<div class="p-8 text-center">Loading trail...</div>';
    
    // Open modal
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.querySelector('.modal-glass').classList.remove('scale-95');
        modal.querySelector('.modal-glass').classList.add('scale-100');
    }, 10);
    
    // Fetch Items & Audit
    fetchDetails(id);
}

async function fetchDetails(id) {
    const token = localStorage.getItem('auth_token');
    const headers = { 'Accept': 'application/json' };
    if (token && token.length > 20) headers['Authorization'] = `Token ${token}`;
    
    try {
        const [itemsRes, auditRes] = await Promise.all([
            fetch(`/payments/api/v1/settlements/${id}/items/`, { headers }),
            fetch(`/payments/api/v1/settlements/${id}/audit/`, { headers })
        ]);
        
        if (itemsRes.ok) {
            const items = await itemsRes.json();
            renderModalItems(items);
        }
        
        if (auditRes.ok) {
            const logs = await auditRes.json();
            renderModalAudit(logs);
        }
    } catch (e) {
        console.error('Error fetching details:', e);
    }
}

function renderModalItems(items) {
    const tbody = document.getElementById('modal-items-tbody');
    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-outline">No items in this period.</td></tr>';
        return;
    }
    
    tbody.innerHTML = items.map(i => `
        <tr class="hover:bg-surface-container-low transition-all">
            <td class="px-6 py-4">
                <p class="font-bold text-on-surface">${i.product_name}</p>
                <p class="text-[10px] text-outline">Order #${i.order_id}</p>
            </td>
            <td class="px-6 py-4 font-medium">${i.quantity}</td>
            <td class="px-6 py-4 font-bold">$${parseFloat(i.subtotal).toFixed(2)}</td>
            <td class="px-6 py-4 text-rose-500 text-xs">-$${parseFloat(i.commission).toFixed(2)}</td>
            <td class="px-6 py-4 font-black text-primary">$${parseFloat(i.payout).toFixed(2)}</td>
        </tr>
    `).join('');
}

function renderModalAudit(logs) {
    const container = document.getElementById('modal-audit-list');
    if (logs.length === 0) {
        container.innerHTML = '<p class="text-center text-outline p-4">No audit logs found.</p>';
        return;
    }
    
    container.innerHTML = logs.map(l => `
        <div class="flex gap-4">
            <div class="flex flex-col items-center">
                <div class="w-8 h-8 rounded-full bg-surface-container-high border-2 border-outline-variant/30 flex items-center justify-center text-primary z-10">
                    <span class="material-symbols-outlined text-sm">${getAuditIcon(l.action)}</span>
                </div>
                <div class="flex-1 w-0.5 bg-outline-variant/20 my-1"></div>
            </div>
            <div class="pb-6">
                <p class="text-xs font-black uppercase tracking-wider text-primary mb-1">${l.action}</p>
                <p class="text-sm font-medium text-on-surface mb-1">${l.notes || 'System action performed.'}</p>
                <div class="flex items-center gap-2 text-[10px] text-outline font-bold">
                    <span>By ${l.performed_by_name || 'System'}</span>
                    <span>•</span>
                    <span>${new Date(l.created_at).toLocaleString()}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function getAuditIcon(action) {
    switch(action) {
        case 'calculated': return 'calculate';
        case 'approved': return 'verified';
        case 'paid': return 'payments';
        case 'failed': return 'error';
        default: return 'history';
    }
}

function formatDateRange(start, end) {
    const s = new Date(start);
    const e = new Date(end);
    const options = { month: 'short', day: 'numeric' };
    return `${s.toLocaleDateString(undefined, options)} - ${e.toLocaleDateString(undefined, options)}, ${e.getFullYear()}`;
}

function closeModal() {
    const modal = document.getElementById('detail-modal');
    modal.querySelector('.modal-glass').classList.remove('scale-100');
    modal.querySelector('.modal-glass').classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 200);
}

// Close on escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

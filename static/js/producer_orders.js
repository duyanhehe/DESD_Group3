document.addEventListener('DOMContentLoaded', () => {
    fetchOrders();
    setupFilters();
});

function setupFilters() {
    const tabs = document.querySelectorAll('.status-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => {
                t.classList.remove('active', 'bg-primary', 'text-on-primary', 'shadow-lg', 'shadow-primary/20');
                t.classList.add('bg-surface-container-low', 'text-on-surface-variant');
            });
            tab.classList.add('active', 'bg-primary', 'text-on-primary', 'shadow-lg', 'shadow-primary/20');
            tab.classList.remove('bg-surface-container-low', 'text-on-surface-variant');
            
            currentFilter = tab.dataset.status;
            renderTable();
        });
    });

    const searchInput = document.getElementById('order-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value.toLowerCase();
            renderTable();
        });
    }
}

let ordersData = [];
let currentFilter = 'all';
let currentSearch = '';
let currentOrderForStatus = null;
let targetStatusStr = null;

const VALID_TRANSITIONS = {
    'pending': ['confirmed', 'cancelled'],
    'confirmed': ['ready', 'cancelled'],
    'ready': ['delivered', 'cancelled'],
    'delivered': [],
    'cancelled': []
};

// UI Config
const STATUS_STYLES = {
    'pending': { 
        bg: 'bg-amber-100/50', 
        text: 'text-amber-700', 
        dot: 'bg-amber-500',
        label: 'Pending'
    },
    'confirmed': { 
        bg: 'bg-blue-100/50', 
        text: 'text-blue-700', 
        dot: 'bg-blue-500',
        label: 'Confirmed'
    },
    'ready': { 
        bg: 'bg-emerald-100/50', 
        text: 'text-emerald-700', 
        dot: 'bg-emerald-500',
        label: 'Ready'
    },
    'delivered': { 
        bg: 'bg-zinc-100/50', 
        text: 'text-zinc-600', 
        dot: 'bg-zinc-400',
        label: 'Delivered'
    },
    'cancelled': { 
        bg: 'bg-error-container/20', 
        text: 'text-error', 
        dot: 'bg-error',
        label: 'Cancelled'
    }
};

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

async function fetchOrders() {
    const token = localStorage.getItem('auth_token');
    const headers = {
        'Accept': 'application/json',
    };
    
    // Only add Token if it looks like a real, non-placeholder token
    // Real tokens are typically 40+ characters. 'null', 'undefined' etc are short.
    const isValidToken = token && 
                         token !== 'null' && 
                         token !== 'undefined' && 
                         token.trim().length > 20;

    if (isValidToken) {
        headers['Authorization'] = `Token ${token}`;
    }

    try {
        const res = await fetch('/orders/api/v1/producer/', { headers });
        
        if (res.status === 401 && isValidToken) {
            console.warn('Stored token is invalid/expired. Clearing and retrying with session...');
            localStorage.removeItem('auth_token');
            const retryRes = await fetch('/orders/api/v1/producer/', { 
                headers: { 'Accept': 'application/json' } 
            });
            if (retryRes.ok) {
                ordersData = await retryRes.json();
                renderStats();
                renderTable();
                return;
            }
            throw new Error('Unauthorized');
        }
        
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        ordersData = await res.json();
        renderStats();
        renderTable();
    } catch (e) {
        console.error(e);
        const errorMsg = e.message || 'Failed to sync with order relay.';
        document.getElementById('orders-tbody').innerHTML = `
            <tr>
                <td colspan="6" class="px-8 py-20 text-center">
                    <span class="material-symbols-outlined text-4xl text-error mb-4">error</span>
                    <p class="font-bold text-on-surface-variant">${errorMsg}</p>
                    <p class="text-xs text-outline mt-2">Ensure you are logged in as a Producer.</p>
                </td>
            </tr>
        `;
    }
}

function renderStats() {
    let totalRevenue = 0;
    let activeOrders = 0;

    ordersData.forEach(o => {
        if (o.status !== 'cancelled' && o.status !== 'delivered') {
            activeOrders++;
        }
        if (o.status !== 'cancelled') {
            totalRevenue += parseFloat(o.my_subtotal);
        }
    });

    document.getElementById('order-stats-grid').innerHTML = `
        <div class="bg-primary rounded-[32px] p-8 relative overflow-hidden group shadow-xl shadow-primary/10">
            <div class="relative z-10 text-on-primary">
                <p class="font-bold text-[10px] uppercase tracking-widest opacity-80 mb-2">My Gross Revenue</p>
                <h3 class="text-4xl font-black mb-4">$${totalRevenue.toFixed(2)}</h3>
                <p class="text-[10px] font-bold opacity-60 uppercase tracking-widest">Total from ${ordersData.length} Orders</p>
            </div>
            <div class="absolute -right-4 -bottom-4 opacity-10 group-hover:scale-110 transition-transform duration-700">
                <span class="material-symbols-outlined text-8xl">payments</span>
            </div>
        </div>
        <div class="bg-surface-container-low rounded-[32px] p-8 flex flex-col justify-between border border-outline-variant/10">
            <div>
                <p class="text-on-surface-variant font-bold text-[10px] uppercase tracking-widest mb-1">Active Batches</p>
                <h3 class="text-4xl font-extrabold text-on-background">${activeOrders}</h3>
            </div>
            <div class="mt-4">
                <div class="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
                    <div class="h-full bg-primary rounded-full" style="width: ${ordersData.length ? (activeOrders / ordersData.length * 100) : 0}%"></div>
                </div>
            </div>
        </div>
        <div class="bg-surface-container-low rounded-[32px] p-8 flex flex-col justify-between border border-outline-variant/10">
            <div>
                <p class="text-on-surface-variant font-bold text-[10px] uppercase tracking-widest mb-1">Items Prepared</p>
                <h3 class="text-4xl font-extrabold text-on-background">${ordersData.reduce((acc, o) => acc + o.my_items.length, 0)}</h3>
            </div>
            <p class="text-[10px] font-bold text-outline-variant uppercase mt-2">Inventory Throughput</p>
        </div>
    `;
}

function renderTable() {
    const tbody = document.getElementById('orders-tbody');
    
    let filtered = ordersData;
    
    // Status Filter
    if (currentFilter !== 'all') {
        filtered = filtered.filter(o => o.status === currentFilter);
    }
    
    // Search Filter (ID or Customer Name)
    if (currentSearch) {
        filtered = filtered.filter(o => 
            o.id.toString().includes(currentSearch) || 
            o.customer_name.toLowerCase().includes(currentSearch) ||
            o.customer_email.toLowerCase().includes(currentSearch)
        );
    }

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-8 py-20 text-center">
                    <span class="material-symbols-outlined text-5xl text-outline mb-6">inbox</span>
                    <h4 class="font-headline text-xl font-bold mb-1">No orders found</h4>
                    <p class="text-on-surface-variant text-sm font-medium">Try adjusting your filters or search terms.</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map(order => {
        const style = STATUS_STYLES[order.status] || STATUS_STYLES['pending'];
        const allowed = VALID_TRANSITIONS[order.status] || [];
        
        const actionButtons = allowed.map(st => `
            <button class="px-4 py-1.5 rounded-full text-[10px] font-extrabold uppercase tracking-widest transition-all ${st === 'cancelled' ? 'bg-error-container/20 text-error hover:bg-error-container/40' : 'bg-primary text-on-primary shadow-sm hover:scale-105 active:scale-95'}"
                    onclick="event.stopPropagation(); prepareStatusUpdate(${order.id}, '${st}')">
                Mark ${st}
            </button>
        `).join('');

        const itemsSummary = order.my_items.map(item => `
            <div class="flex justify-between items-center py-2 group/item transition-all rounded-xl px-2 hover:bg-emerald-50">
                <span class="font-medium text-xs text-on-surface flex items-center gap-2">
                    <span class="w-5 h-5 bg-surface-container-high rounded flex items-center justify-center text-[10px] font-bold">${item.quantity}</span>
                    ${item.product_name}
                </span>
                <span class="font-bold text-xs text-on-surface-variant group-hover/item:text-primary">$${parseFloat(item.subtotal).toFixed(2)}</span>
            </div>
        `).join('');

        return `
            <tr class="group hover:bg-emerald-50/20 cursor-pointer border-b border-outline-variant/5 transition-all" onclick="toggleRow(${order.id})" id="row-${order.id}">
                <td class="px-8 py-6 font-bold text-on-surface-variant">#${order.id}</td>
                <td class="px-8 py-6">
                    <div>
                        <p class="font-extrabold text-on-background text-sm truncate max-w-[150px]">${order.customer_name}</p>
                        <p class="text-[10px] font-bold text-outline-variant uppercase tracking-wider">${order.customer_email.split('@')[0]}</p>
                    </div>
                </td>
                <td class="px-8 py-6">
                    <span class="px-3 py-1 bg-surface-container rounded-lg text-xs font-extrabold text-on-surface-variant">
                        ${order.my_items.length} Units
                    </span>
                </td>
                <td class="px-8 py-6">
                    <span class="text-sm font-black text-primary">$${parseFloat(order.my_subtotal).toFixed(2)}</span>
                </td>
                <td class="px-8 py-6">
                    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full ${style.bg} ${style.text}">
                        <div class="w-1.5 h-1.5 rounded-full ${style.dot} animate-pulse"></div>
                        <span class="text-[10px] font-black uppercase tracking-widest">${style.label}</span>
                    </div>
                </td>
                <td class="px-8 py-6 text-right">
                    <div class="flex items-center justify-end gap-2">
                        ${actionButtons}
                        <button class="p-2 text-outline hover:text-on-background transition-all" onclick="event.stopPropagation(); viewHistory(${order.id})">
                            <span class="material-symbols-outlined text-sm">history</span>
                        </button>
                    </div>
                </td>
            </tr>
            <tr id="details-${order.id}" class="hidden border-b border-outline-variant/5 bg-surface-container-low/30 overflow-hidden">
                <td colspan="6" class="px-8 py-8">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 bg-white rounded-[24px] p-8 shadow-inner border border-outline-variant/5">
                        <div class="space-y-6">
                            <h4 class="font-headline font-extrabold text-on-background uppercase text-[10px] tracking-[0.2em] border-b pb-4">Logistics Matrix</h4>
                            <div class="grid grid-cols-2 gap-6">
                                <div>
                                    <p class="text-[10px] font-bold text-outline uppercase tracking-widest mb-1">Customer</p>
                                    <p class="text-sm font-extrabold text-on-surface">${order.customer_name}</p>
                                    <p class="text-sm text-on-surface-variant">${order.customer_email}</p>
                                    <p class="text-sm text-on-surface-variant">${order.customer_phone || 'No phone'}</p>
                                </div>
                                <div>
                                    <p class="text-[10px] font-bold text-outline uppercase tracking-widest mb-1">Drop-off Point</p>
                                    <p class="text-sm font-extrabold text-on-surface leading-tight">${order.delivery_address || 'Collection point'}</p>
                                    <p class="text-[10px] font-bold text-primary mt-1">${order.customer_postcode || ''}</p>
                                </div>
                            </div>
                            <div class="pt-4">
                                <p class="text-[10px] font-bold text-outline uppercase tracking-widest mb-1">Order Timestamp</p>
                                <p class="text-sm font-medium text-on-surface-variant underline decoration-dotted">${new Date(order.created_at).toLocaleString()}</p>
                            </div>
                        </div>
                        <div class="space-y-6">
                            <h4 class="font-headline font-extrabold text-emerald-800 uppercase text-[10px] tracking-[0.2em] border-b border-emerald-100 pb-4">Fulfillment Queue</h4>
                            <div class="space-y-1">
                                ${itemsSummary}
                            </div>
                            <div class="pt-4 flex justify-between items-end">
                                <div>
                                    <p class="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">Producer Share</p>
                                    <p class="text-[10px] text-outline font-medium">After system processing</p>
                                </div>
                                <span class="text-2xl font-black text-primary">$${parseFloat(order.my_subtotal).toFixed(2)}</span>
                            </div>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

window.toggleRow = function(id) {
    const detailsRow = document.getElementById(`details-${id}`);
    const mainRow = document.getElementById(`row-${id}`);
    
    if (detailsRow.classList.contains('hidden')) {
        detailsRow.classList.remove('hidden');
        mainRow.classList.add('bg-emerald-50/50');
    } else {
        detailsRow.classList.add('hidden');
        mainRow.classList.remove('bg-emerald-50/50');
    }
};

window.prepareStatusUpdate = function(orderId, newStatus) {
    currentOrderForStatus = orderId;
    targetStatusStr = newStatus;
    
    document.getElementById('display-order-id').textContent = orderId;
    document.getElementById('status-modal-target').textContent = newStatus.toUpperCase();
    document.getElementById('status-note').value = '';
    
    const modal = document.getElementById('status-modal');
    modal.classList.remove('hidden');
    // Simple transition
    modal.querySelector('div').classList.remove('scale-95');
    modal.querySelector('div').classList.add('scale-100');
};

document.getElementById('status-modal-confirm').addEventListener('click', async () => {
    const note = document.getElementById('status-note').value.trim();
    if (!currentOrderForStatus || !targetStatusStr) return;

    const btn = document.getElementById('status-modal-confirm');
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin text-sm">sync</span> Syncing...`;
    btn.disabled = true;

    const token = localStorage.getItem('auth_token');
    const headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    };
    if (token && token !== 'null') {
        headers['Authorization'] = `Token ${token}`;
    }

    try {
        const res = await fetch(`/orders/api/v1/${currentOrderForStatus}/status/`, {
            method: 'PUT',
            headers: headers,
            body: JSON.stringify({ status: targetStatusStr, note: note })
        });
        
        const data = await res.json();
        if (!res.ok) {
            alert(data.error || 'Failed to update status.');
        } else {
            await fetchOrders();
            document.getElementById('status-modal').classList.add('hidden');
        }
    } catch (e) {
        console.error(e);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
});

window.viewHistory = async function(orderId) {
    const token = localStorage.getItem('auth_token');
    const headers = {};
    if (token && token !== 'null') {
        headers['Authorization'] = `Token ${token}`;
    }

    try {
        const res = await fetch(`/orders/api/v1/${orderId}/history/`, { headers });
        if (!res.ok) throw new Error('Failed to fetch history');
        
        const history = await res.json();
        
        let html = '';
        if (history.length === 0) {
            html = '<p class="text-sm font-medium text-outline-variant italic">No legacy record found.</p>';
        } else {
            html = history.map(h => {
                const isNew = !h.old_status;
                return `
                    <div class="relative pl-8 pb-6 border-l-2 border-emerald-100 last:border-0 last:pb-0">
                        <div class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-white border-2 border-emerald-500 flex items-center justify-center">
                            <div class="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                        </div>
                        <div class="flex justify-between items-start mb-2">
                            <span class="text-[10px] font-black text-emerald-800 uppercase tracking-widest px-2 py-1 bg-emerald-50 rounded">
                                ${h.new_status.toUpperCase()}
                            </span>
                            <span class="text-[10px] font-bold text-outline-variant">${new Date(h.timestamp).toLocaleString()}</span>
                        </div>
                        <p class="text-xs font-bold text-on-surface mb-1">
                            ${isNew ? 'New request initialized' : `Transition from ${h.old_status.toUpperCase()}`}
                        </p>
                        <p class="text-xs text-on-surface-variant mb-2">By ${h.changed_by_name || 'System Auto-Agent'}</p>
                        ${h.note ? `<div class="p-3 bg-surface-container-low rounded-xl text-xs font-medium italic text-on-surface-variant border-l-2 border-primary/20">"${h.note}"</div>` : ''}
                    </div>
                `;
            }).join('');
        }
        
        document.getElementById('audit-content').innerHTML = `
            <div class="p-1 border border-emerald-100 rounded-[20px] mb-8">
                <div class="px-6 py-3 bg-emerald-50/50 rounded-[16px] flex justify-between items-center text-[10px] font-black text-emerald-900 uppercase">
                    <span>Lifecycle Trace</span>
                    <span>Order #${orderId}</span>
                </div>
            </div>
            <div class="space-y-0">
                ${html}
            </div>
        `;
        document.getElementById('audit-modal').classList.remove('hidden');
    } catch (e) {
        console.error(e);
        alert('Audit trail extraction failed.');
    }
};

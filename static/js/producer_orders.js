document.addEventListener('DOMContentLoaded', () => {
    fetchOrders();
});

let ordersData = [];
let currentOrderForStatus = null;
let targetStatusStr = null;

const VALID_TRANSITIONS = {
    'pending': ['confirmed', 'cancelled'],
    'confirmed': ['ready', 'cancelled'],
    'ready': ['delivered', 'cancelled'],
    'delivered': [],
    'cancelled': []
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
    try {
        const res = await fetch('/orders/api/v1/producer/');
        if (!res.ok) throw new Error('Failed to fetch orders');
        
        ordersData = await res.json();
        renderStats();
        renderTable();
    } catch (e) {
        console.error(e);
        document.getElementById('orders-tbody').innerHTML = `<tr><td colspan="7" class="error">Failed to load orders.</td></tr>`;
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
        <div class="stat-card">
            <h3>Active Orders</h3>
            <p>${activeOrders}</p>
        </div>
        <div class="stat-card">
            <h3>Total Revenue (Est.)</h3>
            <p>$${totalRevenue.toFixed(2)}</p>
        </div>
        <div class="stat-card">
            <h3>Total Orders</h3>
            <p>${ordersData.length}</p>
        </div>
    `;
}

function renderTable() {
    const tbody = document.getElementById('orders-tbody');
    
    if (ordersData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 40px;">No orders found.</td></tr>`;
        return;
    }

    tbody.innerHTML = ordersData.map(order => {
        let statusColor = '#666';
        if (order.status === 'pending') statusColor = '#d97706';
        if (order.status === 'confirmed') statusColor = '#2563eb';
        if (order.status === 'ready') statusColor = '#16a34a';
        if (order.status === 'cancelled') statusColor = '#dc2626';

        // Filter out transitions, build buttons
        const allowed = VALID_TRANSITIONS[order.status] || [];
        let actionButtonsHtml = allowed.map(st => `
            <button class="btn btn-sm ${st === 'cancelled' ? 'btn-ghost' : 'btn-primary'}" 
                    style="margin-right: 5px; ${st === 'cancelled' ? 'color: red;' : ''}"
                    onclick="event.stopPropagation(); prepareStatusUpdate(${order.id}, '${st}')">
                Mark ${st.charAt(0).toUpperCase() + st.slice(1)}
            </button>
        `).join('');

        let itemsHtml = order.my_items.map(item => `
            <div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dashed var(--border-light);">
                <span>${item.quantity}x ${item.product_name}</span>
                <span>$${item.subtotal}</span>
            </div>
        `).join('');

        return `
            <tr style="cursor: pointer; transition: background 0.2s;" onclick="toggleRow(${order.id})" id="row-${order.id}">
                <td>#${order.id}</td>
                <td>${order.customer_name}</td>
                <td>${order.my_items.length}</td>
                <td style="font-weight: 600;">$${parseFloat(order.my_subtotal).toFixed(2)}</td>
                <td><span class="badge" style="background-color: ${statusColor}20; color: ${statusColor}; padding: 4px 8px; border-radius: 4px;">${order.status.toUpperCase()}</span></td>
                <td>${new Date(order.created_at).toLocaleDateString()}</td>
                <td class="table-actions">
                    ${actionButtonsHtml}
                    <button class="btn btn-sm btn-ghost" onclick="event.stopPropagation(); viewHistory(${order.id})">History</button>
                </td>
            </tr>
            <tr id="details-${order.id}" class="hidden" style="background-color: #fafafa;">
                <td colspan="7" style="padding: 20px;">
                    <div style="display: flex; gap: 40px;">
                        <div style="flex: 1;">
                            <h4 style="margin-top: 0;">Customer Information</h4>
                            <p><strong>Name:</strong> ${order.customer_name}</p>
                            <p><strong>Email:</strong> ${order.customer_email}</p>
                            <p><strong>Phone:</strong> ${order.customer_phone || 'N/A'}</p>
                            <p><strong>Address:</strong> ${order.delivery_address || 'N/A'} ${order.customer_postcode || ''}</p>
                        </div>
                        <div style="flex: 1;">
                            <h4 style="margin-top: 0;">Your Items to Prepare</h4>
                            ${itemsHtml}
                            <div style="display: flex; justify-content: space-between; padding: 8px 0; font-weight: 700; margin-top: 8px; border-top: 2px solid var(--border-light);">
                                <span>Subtotal:</span>
                                <span>$${parseFloat(order.my_subtotal).toFixed(2)}</span>
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
    if (detailsRow.classList.contains('hidden')) {
        detailsRow.classList.remove('hidden');
    } else {
        detailsRow.classList.add('hidden');
    }
};

window.prepareStatusUpdate = function(orderId, newStatus) {
    currentOrderForStatus = orderId;
    targetStatusStr = newStatus;
    
    document.getElementById('display-order-id').textContent = orderId;
    document.getElementById('status-modal-target').textContent = newStatus.toUpperCase();
    document.getElementById('status-note').value = '';
    document.getElementById('status-modal').classList.remove('hidden');
};

document.getElementById('status-modal-confirm').addEventListener('click', async () => {
    const note = document.getElementById('status-note').value.trim();
    if (!currentOrderForStatus || !targetStatusStr) return;

    try {
        const res = await fetch(`/orders/api/v1/${currentOrderForStatus}/status/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ status: targetStatusStr, note: note })
        });
        
        const data = await res.json();
        if (!res.ok) {
            alert(data.error || 'Failed to update status.');
        } else {
            // refresh
            fetchOrders();
            document.getElementById('status-modal').classList.add('hidden');
        }
    } catch (e) {
        console.error(e);
    }
});

window.viewHistory = async function(orderId) {
    try {
        const res = await fetch(`/orders/api/v1/${orderId}/history/`);
        if (!res.ok) throw new Error('Failed to fetch history');
        
        const history = await res.json();
        
        let html = '';
        if (history.length === 0) {
            html = '<p>No history found.</p>';
        } else {
            html = history.map(h => `
                <div style="margin-bottom: 16px; padding-left: 16px; border-left: 2px solid var(--primary);">
                    <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 4px;">
                        ${new Date(h.timestamp).toLocaleString()} by ${h.changed_by_name || 'System'}
                    </div>
                    <div style="font-weight: 600;">
                        ${h.old_status ? h.old_status.toUpperCase() : 'NEW'} &rarr; ${h.new_status.toUpperCase()}
                    </div>
                    ${h.note ? `<div style="margin-top: 4px; font-style: italic; color: #555;">Note: ${h.note}</div>` : ''}
                </div>
            `).join('');
        }
        
        document.getElementById('audit-content').innerHTML = html;
        document.getElementById('audit-modal').classList.remove('hidden');
    } catch (e) {
        console.error(e);
        alert('Failed to load history.');
    }
};

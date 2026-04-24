/**
 * Admin Settlements Management
 * Handles fetching, filtering, calculating and processing producer payouts.
 */

let settlements = [];
let summaryData = null;

document.addEventListener('DOMContentLoaded', () => {
    fetchSettlements();
    fetchSummary();
    setupEventListeners();
    
    // Set default date for calculation to today
    document.getElementById('calculate-date').valueAsDate = new Date();
});

function setupEventListeners() {
    // Filters
    document.getElementById('status-filter').addEventListener('change', fetchSettlements);
    document.getElementById('producer-search').addEventListener('input', debounce(renderTable, 300));
    
    // Modals
    document.getElementById('open-calculate-modal').addEventListener('click', () => {
        document.getElementById('calculate-modal').style.display = 'flex';
    });
    
    document.getElementById('close-calculate-modal').addEventListener('click', () => {
        document.getElementById('calculate-modal').style.display = 'none';
    });
    
    document.getElementById('close-pay-modal').addEventListener('click', () => {
        document.getElementById('pay-modal').style.display = 'none';
    });

    // Actions
    document.getElementById('run-calculation').addEventListener('click', runCalculation);
    document.getElementById('confirm-payment').addEventListener('click', confirmPayment);
    document.getElementById('export-csv').addEventListener('click', exportCSV);
}

async function fetchSettlements() {
    const status = document.getElementById('status-filter').value;
    let url = '/payments/api/v1/admin/settlements/';
    if (status) url += `?status=${status}`;

    try {
        const headers = {
            'X-CSRFToken': getCookie('csrftoken')
        };
        const token = localStorage.getItem('auth_token');
        if (token && token !== 'null') {
            headers['Authorization'] = `Token ${token}`;
        }

        const response = await fetch(url, { headers });
        settlements = await response.json();
        renderTable();
    } catch (error) {
        console.error('Error fetching settlements:', error);
    }
}

async function fetchSummary() {
    try {
        const headers = {};
        const token = localStorage.getItem('auth_token');
        if (token && token !== 'null') {
            headers['Authorization'] = `Token ${token}`;
        }

        const response = await fetch('/payments/api/v1/admin/settlements/summary/', { headers });
        summaryData = await response.json();
        renderSummary();
    } catch (error) {
        console.error('Error fetching summary:', error);
    }
}

function renderSummary() {
    if (!summaryData) return;
    
    const container = document.getElementById('admin-summary-grid');
    container.innerHTML = `
        <div class="admin-stats-card">
            <p class="text-[10px] font-black uppercase text-zinc-400 tracking-widest mb-1">Total Payouts</p>
            <h4 class="text-3xl font-black text-zinc-900">$${summaryData.total_payouts}</h4>
            <p class="text-xs text-zinc-400 mt-2 font-bold">${summaryData.total_settlements} Settlements</p>
        </div>
        <div class="admin-stats-card">
            <p class="text-[10px] font-black uppercase text-zinc-400 tracking-widest mb-1">Commission Earned</p>
            <h4 class="text-3xl font-black text-emerald-600">$${summaryData.total_commission}</h4>
            <p class="text-xs text-emerald-600/60 mt-2 font-bold">5% Base Rate</p>
        </div>
        <div class="admin-stats-card">
            <p class="text-[10px] font-black uppercase text-zinc-400 tracking-widest mb-1">Pending Approval</p>
            <h4 class="text-3xl font-black text-amber-600">${summaryData.status_breakdown.calculated || 0}</h4>
            <p class="text-xs text-amber-600/60 mt-2 font-bold">Awaiting verification</p>
        </div>
        <div class="admin-stats-card">
            <p class="text-[10px] font-black uppercase text-zinc-400 tracking-widest mb-1">Current Period</p>
            <h4 class="text-lg font-black text-zinc-900">Weekly</h4>
            <p class="text-xs text-zinc-400 mt-2 font-bold">${formatDate(summaryData.week_start)} - ${formatDate(summaryData.week_end)}</p>
        </div>
    `;
}

function renderTable() {
    const tbody = document.getElementById('settlements-table-body');
    const searchTerm = document.getElementById('producer-search').value.toLowerCase();
    
    const filtered = settlements.filter(s => 
        s.producer_name.toLowerCase().includes(searchTerm)
    );

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-8 py-20 text-center">
                    <p class="font-bold text-zinc-400 italic">No settlements match your criteria.</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map(s => `
        <tr class="group hover:bg-zinc-50 transition-colors border-b border-zinc-50">
            <td class="px-8 py-6">
                <p class="font-black text-zinc-900 text-sm mb-0.5">${formatDate(s.week_start)} - ${formatDate(s.week_end)}</p>
                <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-tighter">ID: ${s.id.split('-')[0]}...</p>
            </td>
            <td class="px-8 py-6">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-black text-xs uppercase">
                        ${s.producer_name.substring(0, 2)}
                    </div>
                    <span class="font-bold text-zinc-900 capitalize">${s.producer_name}</span>
                </div>
            </td>
            <td class="px-8 py-6 font-bold text-zinc-900">$${s.total_sales}</td>
            <td class="px-8 py-6 font-black text-zinc-900">$${s.payout_amount}</td>
            <td class="px-8 py-6">
                <span class="status-badge status-${s.status.toLowerCase()}">${s.status}</span>
            </td>
            <td class="px-8 py-6">
                <div class="flex items-center justify-end gap-2">
                    ${s.status === 'calculated' ? `
                        <button onclick="approveSettlement('${s.id}')" class="action-btn bg-emerald-100 text-emerald-700 hover:bg-emerald-600 hover:text-white" title="Approve">
                            <span class="material-symbols-outlined text-sm">check</span>
                        </button>
                    ` : ''}
                    
                    ${s.status === 'approved' ? `
                        <button onclick="openPayModal('${s.id}', '${s.producer_name}')" class="action-btn bg-primary/10 text-primary hover:bg-primary hover:text-on-primary" title="Mark Paid">
                            <span class="material-symbols-outlined text-sm">payments</span>
                        </button>
                    ` : ''}

                    ${s.status === 'failed' ? `
                        <button onclick="retrySettlement('${s.id}')" class="action-btn bg-amber-100 text-amber-700 hover:bg-amber-600 hover:text-white" title="Retry">
                            <span class="material-symbols-outlined text-sm">refresh</span>
                        </button>
                    ` : ''}

                    ${s.status === 'paid' ? `
                        <span class="material-symbols-outlined text-emerald-600" title="Paid">verified</span>
                    ` : `
                        <button onclick="failSettlement('${s.id}')" class="action-btn bg-red-50 text-red-700 hover:bg-red-600 hover:text-white" title="Fail / Reject">
                            <span class="material-symbols-outlined text-sm">close</span>
                        </button>
                    `}
                </div>
            </td>
        </tr>
    `).join('');
}

async function runCalculation() {
    const weekDate = document.getElementById('calculate-date').value;
    const btn = document.getElementById('run-calculation');
    
    if (!weekDate) {
        alert('Please select a date.');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin material-symbols-outlined">sync</span> Calculating...';

    try {
        const requestOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ week_date: weekDate })
        };
        
        const token = localStorage.getItem('auth_token');
        if (token && token !== 'null') {
            requestOptions.headers['Authorization'] = `Token ${token}`;
        }

        const response = await fetch('/payments/api/v1/admin/settlements/calculate/', requestOptions);

        const data = await response.json();
        if (response.ok) {
            alert(`Calculation complete: ${data.message}`);
            document.getElementById('calculate-modal').style.display = 'none';
            fetchSettlements();
            fetchSummary();
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Calculation error:', error);
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Calculate Now';
    }
}

async function approveSettlement(id) {
    if (!confirm('Are you sure you want to approve this settlement for payment?')) return;

    try {
        const headers = {
            'X-CSRFToken': getCookie('csrftoken')
        };
        const token = localStorage.getItem('auth_token');
        if (token && token !== 'null') {
            headers['Authorization'] = `Token ${token}`;
        }

        const response = await fetch(`/payments/api/v1/admin/settlements/${id}/approve/`, {
            method: 'POST',
            headers: headers
        });

        if (response.ok) {
            fetchSettlements();
            fetchSummary();
        }
    } catch (error) {
        console.error('Approval error:', error);
    }
}

function openPayModal(id, producerName) {
    document.getElementById('pay-settlement-id').value = id;
    document.getElementById('pay-producer-name').textContent = producerName;
    document.getElementById('pay-modal').style.display = 'flex';
}

async function confirmPayment() {
    const id = document.getElementById('pay-settlement-id').value;
    const method = document.getElementById('pay-method').value;
    const reference = document.getElementById('pay-reference').value;
    const notes = document.getElementById('pay-notes').value;

    if (!reference) {
        alert('Please enter a transaction reference.');
        return;
    }

    try {
        const requestOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                payment_method: method,
                payment_reference: reference,
                notes: notes
            })
        };
        
        const token = localStorage.getItem('auth_token');
        if (token && token !== 'null') {
            requestOptions.headers['Authorization'] = `Token ${token}`;
        }

        const response = await fetch(`/payments/api/v1/admin/settlements/${id}/pay/`, requestOptions);

        if (response.ok) {
            document.getElementById('pay-modal').style.display = 'none';
            fetchSettlements();
            fetchSummary();
        }
    } catch (error) {
        console.error('Payment confirmation error:', error);
    }
}

async function failSettlement(id) {
    const reason = prompt('Reason for failure/rejection:');
    if (!reason) return;

    try {
        const requestOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ reason: reason })
        };

        const token = localStorage.getItem('auth_token');
        if (token && token !== 'null') {
            requestOptions.headers['Authorization'] = `Token ${token}`;
        }

        const response = await fetch(`/payments/api/v1/admin/settlements/${id}/fail/`, requestOptions);

        if (response.ok) {
            fetchSettlements();
        }
    } catch (error) {
        console.error('Failure marking error:', error);
    }
}

async function retrySettlement(id) {
    if (!confirm('Are you sure you want to retry this failed settlement?')) return;

    try {
        const headers = {
            'X-CSRFToken': getCookie('csrftoken')
        };
        const token = localStorage.getItem('auth_token');
        if (token && token !== 'null') {
            headers['Authorization'] = `Token ${token}`;
        }

        const response = await fetch(`/payments/api/v1/admin/settlements/${id}/retry/`, {
            method: 'POST',
            headers: headers
        });

        if (response.ok) {
            fetchSettlements();
            fetchSummary();
        } else {
            const data = await response.json();
            alert(`Error retrying settlement: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Retry error:', error);
    }
}

function exportCSV() {
    const status = document.getElementById('status-filter').value;
    let url = '/payments/api/v1/admin/settlements/export/';
    if (status) url += `?status=${status}`;
    
    window.location.href = url;
}

// Helpers
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

function formatDate(dateStr) {
    const options = { month: 'short', day: 'numeric' };
    return new Date(dateStr).toLocaleDateString(undefined, options);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

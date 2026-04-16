document.addEventListener('DOMContentLoaded', () => {
    // Global Cart Badge Count
    refreshCartBadge();

    // specific to cart page
    const cartContent = document.getElementById('cart-content');
    if (cartContent) {
        renderCartPage();
        
        document.getElementById('clear-cart-btn').addEventListener('click', clearCart);
        document.getElementById('checkout-btn').addEventListener('click', checkout);
    }
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

// ─── Auth Gate ────────────────────────────────────────────────
// Reads server-injected meta tag — no API round-trip needed
function isAuthenticated() {
    const meta = document.querySelector('meta[name="user-authenticated"]');
    return meta && meta.getAttribute('content') === 'true';
}

window.showAuthModal = function(returnUrl) {
    const modal = document.getElementById('auth-gate-modal');
    const loginBtn = document.getElementById('auth-gate-login-btn');
    if (!modal) return;

    // Set the ?next= redirect on the login button
    const next = returnUrl || window.location.pathname;
    const loginBase = document.querySelector('meta[name="login-url"]')?.getAttribute('content') || '/accounts/login/';
    loginBtn.href = `${loginBase}?next=${encodeURIComponent(next)}`;

    modal.classList.remove('hidden');
    // Animate panel in
    requestAnimationFrame(() => {
        const panel = document.getElementById('auth-gate-panel');
        if (panel) panel.style.animation = 'slideUp 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards';
    });
};

window.closeAuthModal = function() {
    const modal = document.getElementById('auth-gate-modal');
    if (modal) modal.classList.add('hidden');
};

// Close on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') window.closeAuthModal();
});

// ─── Add to Cart ───────────────────────────────────────────────
// Ensure global handle
window.addToCart = async function(productId, quantity = 1) {
    // Auth gate — check before any network call
    if (!isAuthenticated()) {
        window.showAuthModal(window.location.pathname);
        return;
    }

    try {
        const res = await fetch('/orders/api/v1/cart/add/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ product_id: productId, quantity: quantity })
        });
        const data = await res.json();

        if (!res.ok) {
            // Could be stock issue, permission issue, etc.
            if (res.status === 401 || res.status === 403) {
                window.showAuthModal(window.location.pathname);
            } else {
                // Show inline toast for stock/validation errors
                showToast(data.error || 'Could not add item to cart.');
            }
        } else {
            // Update badge with total quantity across all items
            const totalQty = data.items ? data.items.reduce((sum, i) => sum + i.quantity, 0) : 0;
            updateCartBadge(totalQty);
            showToast('Added to basket! 🛒', 'success');
        }
    } catch (e) {
        console.error(e);
        showToast('Something went wrong. Please try again.');
    }
};

// Lightweight toast — no library needed
function showToast(message, type = 'error') {
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

    // Auto-dismiss after 2.5s
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(12px)';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}



async function updateCartItem(itemId, quantity) {
    if (quantity < 1) {
        removeCartItem(itemId);
        return;
    }
    try {
        const res = await fetch(`/orders/api/v1/cart/item/${itemId}/`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ quantity })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || 'Invalid quantity.', 'error');
        }
        
        renderCartPage();
        refreshCartBadge();
    } catch (e) {
        console.error(e);
    }
}

async function removeCartItem(itemId) {
    try {
        await fetch(`/orders/api/v1/cart/item/${itemId}/remove/`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        renderCartPage();
        refreshCartBadge();
    } catch (e) {
        console.error(e);
    }
}

async function clearCart() {
    if (!confirm('Are you sure you want to empty your basket?')) return;
    try {
        await fetch('/orders/api/v1/cart/clear/', {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        renderCartPage();
        refreshCartBadge();
    } catch (e) {
        console.error(e);
    }
}

async function checkout() {
    const btn = document.getElementById('checkout-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin text-sm">sync</span> Finalizing...`;
    btn.disabled = true;

    try {
        const res = await fetch('/orders/api/v1/create/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (!res.ok) {
            if (res.status === 401 || res.status === 403) {
                window.showAuthModal(window.location.pathname);
            } else {
                showToast(data.error || 'Checkout failed.', 'error');
            }
            btn.innerHTML = originalText;
            btn.disabled = false;
        } else {
            // Redirect to homepage with success message
            window.location.href = '/?order=success';
        }
    } catch (e) {
        console.error(e);
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}


function updateCartBadge(count) {
    const badge = document.getElementById('cart-count');
    if (badge) {
        badge.textContent = count;
        // Use Tailwind hidden class
        if (count > 0) {
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }
}

async function refreshCartBadge() {
    try {
        const res = await fetch('/orders/api/v1/cart/');
        if (res.ok) {
            const data = await res.json();
            // Show total quantity, not distinct product count
            const totalQty = data.items ? data.items.reduce((sum, i) => sum + i.quantity, 0) : 0;
            updateCartBadge(totalQty);
        } else {
            updateCartBadge(0);
        }
    } catch (e) {
        updateCartBadge(0);
    }
}


async function renderCartPage() {
    const cartContent = document.getElementById('cart-content');
    const clearBtn = document.getElementById('clear-cart-btn');
    const checkoutBtn = document.getElementById('checkout-btn');
    
    try {
        const res = await fetch('/orders/api/v1/cart/');
        
        if (!res.ok) {
            cartContent.innerHTML = `
                <div class="flex flex-col items-center justify-center py-20 text-center bg-surface-container-low rounded-[32px] border border-dashed border-outline-variant">
                    <span class="material-symbols-outlined text-6xl text-outline mb-6">lock</span>
                    <h3 class="font-headline text-2xl font-bold mb-2">Member Access Only</h3>
                    <p class="text-on-surface-variant font-medium mb-8">Please log in to review your cart and proceed to checkout.</p>
                    <a href="/accounts/login/" class="px-8 py-3 bg-primary text-on-primary rounded-full font-bold shadow-lg shadow-primary/20">Sign In</a>
                </div>
            `;
            return;
        }

        const data = await res.json();
        
        if (!data.items || data.items.length === 0) {
            cartContent.innerHTML = `
                <div class="flex flex-col items-center justify-center py-20 text-center bg-surface-container-low rounded-[32px] border border-dashed border-outline-variant/30">
                    <span class="material-symbols-outlined text-6xl text-outline mb-6">shopping_basket</span>
                    <h3 class="font-headline text-2xl font-bold mb-2">Your basket is empty</h3>
                    <p class="text-on-surface-variant font-medium mb-8">Looks like you haven't added any fresh harvests yet.</p>
                    <a href="/" class="px-8 py-4 bg-primary text-on-primary rounded-full font-bold shadow-xl shadow-primary/20 hover:scale-105 transition-all">Start Shopping</a>
                </div>
            `;
            clearBtn.classList.add('hidden');
            checkoutBtn.classList.add('hidden');
            return;
        }

        clearBtn.classList.remove('hidden');
        checkoutBtn.classList.remove('hidden');

        let html = '<div class="space-y-12">';
        
        data.grouped_by_producer.forEach(group => {
            let itemsHtml = group.items.map(item => `
                <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center py-8 border-b border-outline-variant/5 last:border-0 group">
                    <div class="flex gap-6 items-center flex-1">
                        <div class="w-16 h-16 bg-surface-container rounded-2xl flex items-center justify-center text-3xl opacity-40 group-hover:scale-110 transition-transform">
                            🛒
                        </div>
                        <div>
                            <h4 class="font-headline font-bold text-lg text-on-background">${item.product_name}</h4>
                            <p class="text-sm font-bold text-primary">$${item.unit_price} <span class="text-xs text-outline font-medium tracking-tight">/ ${item.unit}</span></p>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-12 w-full sm:w-auto mt-6 sm:mt-0">
                        <div class="flex items-center bg-surface-container-high rounded-2xl p-1 border border-outline-variant/5 shadow-sm">
                            <button class="w-10 h-10 flex items-center justify-center rounded-xl hover:bg-white transition-all text-on-surface-variant hover:text-primary active:scale-90" onclick="updateCartItem(${item.id}, ${item.quantity - 1})">
                                <span class="material-symbols-outlined font-bold text-sm">remove</span>
                            </button>
                            <span class="w-12 text-center font-black text-on-background">${item.quantity}</span>
                            <button class="w-10 h-10 flex items-center justify-center rounded-xl hover:bg-white transition-all text-on-surface-variant hover:text-primary active:scale-90" onclick="updateCartItem(${item.id}, ${item.quantity + 1})">
                                <span class="material-symbols-outlined font-bold text-sm">add</span>
                            </button>
                        </div>
                        
                        <div class="text-right min-w-[100px]">
                            <p class="text-[10px] font-bold text-outline uppercase tracking-widest mb-1">Subtotal</p>
                            <span class="font-black text-on-background text-lg">$${item.subtotal}</span>
                        </div>
                        
                        <button class="p-2 text-outline hover:text-error transition-colors" onclick="removeCartItem(${item.id})">
                            <span class="material-symbols-outlined text-lg">delete</span>
                        </button>
                    </div>
                </div>
            `).join('');

            html += `
                <div class="bg-surface-container-lowest rounded-[32px] overflow-hidden shadow-sm border border-outline-variant/5">
                    <div class="px-10 py-6 bg-surface-container-low flex justify-between items-center border-b border-outline-variant/10">
                        <div class="flex items-center gap-3">
                            <div class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-700">
                                <span class="material-symbols-outlined text-sm">potted_plant</span>
                            </div>
                            <h3 class="font-headline font-extrabold text-on-background uppercase text-[10px] tracking-[0.2em]">Farm: ${group.producer_name}</h3>
                        </div>
                        <span class="text-[10px] font-bold text-primary uppercase tracking-widest bg-emerald-50 px-3 py-1 rounded-full">Origin Direct</span>
                    </div>
                    <div class="px-10">
                        ${itemsHtml}
                    </div>
                    <div class="px-10 py-6 bg-surface-container-lowest flex justify-between items-center border-t border-dashed border-outline-variant/20 italic">
                        <span class="text-xs font-bold text-outline uppercase tracking-widest">Share from ${group.producer_name}</span>
                        <span class="font-extrabold text-on-background">$${group.subtotal.toFixed(2)}</span>
                    </div>
                </div>
            `;
        });

        html += `
            <div class="mt-20 p-12 bg-zinc-900 rounded-[48px] text-white flex flex-col md:flex-row justify-between items-center gap-8 relative overflow-hidden shadow-2xl">
                <div class="relative z-10">
                    <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-[0.3em] mb-3 block">Final Calculation</span>
                    <h3 class="font-headline text-3xl font-extrabold mb-1">Order Summary</h3>
                    <p class="text-zinc-400 text-sm font-medium">Includes all service fees and local delivery.</p>
                </div>
                
                <div class="flex items-center gap-12 relative z-10 w-full md:w-auto">
                    <div class="text-right hidden sm:block">
                        <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Net Total</p>
                        <p class="text-2xl font-black text-white">$${Number(data.total).toFixed(2)}</p>
                    </div>
                    <div class="flex-1 md:flex-none">
                        <button onclick="checkout()" class="w-full md:w-auto px-12 py-5 bg-white text-zinc-900 rounded-full font-black text-lg shadow-xl hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-3">
                            Confirm and Pay $${Number(data.total).toFixed(2)}
                            <span class="material-symbols-outlined font-black">arrow_forward</span>
                        </button>
                    </div>
                </div>
                
                <!-- Decorative element -->
                <div class="absolute -right-12 -bottom-12 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl"></div>
            </div>
            
            <div class="mt-12 text-center">
                <p class="text-[10px] font-bold text-outline-variant uppercase tracking-widest flex items-center justify-center gap-2">
                    <span class="material-symbols-outlined text-sm">verified_user</span>
                    Secure Transaction via Food Network Ledger
                </p>
            </div>
        </div>`;

        cartContent.innerHTML = html;

    } catch (e) {
        console.error(e);
        cartContent.innerHTML = `
            <div class="flex flex-col items-center justify-center py-20 text-center text-error">
                <span class="material-symbols-outlined text-4xl mb-4">report</span>
                <p class="font-bold uppercase text-xs tracking-widest">Error syncing basket data.</p>
            </div>
        `;
    }
}

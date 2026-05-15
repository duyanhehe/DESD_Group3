document.addEventListener('DOMContentLoaded', () => {
    // Check for payment cancellation
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('order') === 'cancel') {
        window.showToast('Payment cancelled. Your items are still in the basket.', 'error');
        // Clean up URL without refreshing
        window.history.replaceState({}, document.title, window.location.pathname);
    }

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

    // Auto-dismiss after 2.5s
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(12px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000); // Increased to 4s for better visibility
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
    btn.innerHTML = `<span class="material-symbols-outlined animate-spin text-sm">sync</span> Redirecting to Stripe...`;
    btn.disabled = true;

    try {
        const token = localStorage.getItem('auth_token');
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        };
        
        if (token) {
            headers['Authorization'] = `Token ${token}`;
        }

        const deliveryDate = document.getElementById('delivery-date-input')?.value;
        const isRecurring = document.getElementById('is-recurring-input')?.checked || false;

        const res = await fetch('/payments/api/v1/checkout/', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                delivery_date: deliveryDate,
                is_recurring: isRecurring
            })
        });
        
        const data = await res.json();
        
        if (!res.ok) {
            if (res.status === 401 || res.status === 403) {
                window.showAuthModal(window.location.pathname);
            } else {
                window.showToast(data.error || 'Checkout failed.', 'error');
            }
            btn.innerHTML = originalText;
            btn.disabled = false;
        } else if (data.checkout_url) {
            // Redirect to Stripe
            window.location.href = data.checkout_url;
        } else {
            window.showToast('Could not initiate payment session.', 'error');
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (e) {
        console.error(e);
        window.showToast('Network error during checkout.', 'error');
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

// ─── Shared Fetch Cache ──────────────────────────────────────
// Prevents multiple parallel requests to the heavy cart API
let _pendingCartFetch = null;

async function getCartData() {
    if (_pendingCartFetch) return _pendingCartFetch;

    _pendingCartFetch = fetch('/orders/api/v1/cart/').then(async res => {
        if (!res.ok) {
            _pendingCartFetch = null;
            throw new Error('Cart fetch failed');
        }
        const data = await res.json();
        _pendingCartFetch = null; // Clear after success
        return data;
    }).catch(err => {
        _pendingCartFetch = null;
        throw err;
    });

    return _pendingCartFetch;
}

async function refreshCartBadge() {
    // Only fetch if user is logged in to avoid 401 errors in console/logs
    if (!isAuthenticated()) {
        updateCartBadge(0);
        return;
    }
    try {
        const data = await getCartData();
        // Show total quantity, not distinct product count
        const totalQty = data.items ? data.items.reduce((sum, i) => sum + i.quantity, 0) : 0;
        updateCartBadge(totalQty);
    } catch (e) {
        updateCartBadge(0);
    }
}


async function fetchCartRecommendations(itemNames) {
    const recContainer = document.getElementById('cart-recommendations');
    if (!recContainer) return;

    try {
        const res = await fetch('/ai/recommendations/cart/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ items: itemNames })
        });
        if (!res.ok) return;

        const data = await res.json();
        if (data.products && data.products.length > 0) {
            recContainer.innerHTML = `
                <div class="space-y-12">
                    <div class="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 border-b border-outline-variant/10 pb-8">
                        <div class="max-w-xl">
                            <span class="text-[10px] font-bold text-primary uppercase tracking-[0.2em] mb-3 block">Complete your basket</span>
                            <h2 class="font-headline text-3xl font-extrabold text-on-background tracking-tight italic">Recommended For You</h2>
                            <p class="text-on-surface-variant text-sm font-medium leading-relaxed mt-2">
                                <span class="material-symbols-outlined text-primary text-base inline-block align-middle mr-1">auto_awesome</span>
                                ${data.explanation || 'Based on your current basket selections.'}
                            </p>
                        </div>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
                        ${data.products.slice(0, 4).map(p => `
                            <div class="bg-surface-container-low rounded-3xl overflow-hidden group hover:shadow-xl transition-all duration-300 border border-outline-variant/10 flex flex-col p-4">
                                <div class="aspect-square bg-surface-container rounded-2xl flex items-center justify-center text-3xl opacity-30 group-hover:scale-105 transition-transform mb-4">
                                    🛒
                                </div>
                                <h4 class="font-headline font-bold text-on-background text-[11px] mb-1 uppercase tracking-wider h-8 line-clamp-2">${p.name}</h4>
                                <div class="flex justify-between items-center mt-auto pt-3 border-t border-outline-variant/5">
                                    <span class="text-sm font-black text-primary">$${p.price}</span>
                                    <button onclick="window.addToCart(${p.id})" class="px-3 py-1.5 bg-zinc-900 text-white rounded-full text-[10px] font-bold hover:bg-emerald-700 transition-colors">
                                        Add
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            recContainer.classList.remove('hidden');
        }
    } catch (e) {
        console.error('Error fetching cart recommendations:', e);
    }
}


async function renderCartPage() {
    const cartContent = document.getElementById('cart-content');
    const clearBtn = document.getElementById('clear-cart-btn');
    const checkoutBtn = document.getElementById('checkout-btn');
    
    try {
        const data = await getCartData();
        
        if (!data.items || data.items.length === 0) {
            cartContent.innerHTML = `
                <div class="flex flex-col items-center justify-center py-20 text-center bg-surface-container-low rounded-[32px] border border-dashed border-outline-variant/30">
                    <span class="material-symbols-outlined text-6xl text-outline mb-6">shopping_basket</span>
                    <h3 class="font-headline text-2xl font-bold mb-2">Your basket is empty</h3>
                    <p class="text-on-surface-variant font-medium mb-8">Looks like you haven't added any fresh harvests yet.</p>
                    <a href="/" class="px-8 py-4 bg-primary text-on-primary rounded-full font-bold shadow-xl shadow-primary/20 hover:scale-105 transition-all">Start Shopping</a>
                </div>
            `;
            if (clearBtn) clearBtn.classList.add('hidden');
            if (checkoutBtn) checkoutBtn.classList.add('hidden');
            return;
        }

        // Fetch AI recommendations based on current cart items
        if (data.items && data.items.length > 0) {
            const itemNames = data.items.map(i => i.product_name);
            fetchCartRecommendations(itemNames);
        }

        if (clearBtn) clearBtn.classList.remove('hidden');
        if (checkoutBtn) checkoutBtn.classList.remove('hidden');

        let html = '<div class="space-y-12">';
        
        // Tiered Discount Notices (TC-017)
        html += `
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                <div class="bg-blue-50 border border-blue-200 p-6 rounded-[32px] flex items-center gap-6">
                    <div class="w-12 h-12 bg-blue-500 text-white rounded-2xl flex items-center justify-center shrink-0">
                        <span class="material-symbols-outlined">trending_down</span>
                    </div>
                    <div>
                        <h4 class="font-bold text-blue-900">Tiered Bulk Savings</h4>
                        <p class="text-[11px] text-blue-700 leading-tight">Buy more, save more: <strong>10% (>5)</strong>, <strong>15% (>7)</strong>, or <strong>20% (>10)</strong> off!</p>
                    </div>
                </div>
                ${data.is_community_group ? `
                <div class="bg-emerald-50 border border-emerald-200 p-6 rounded-[32px] flex items-center gap-6">
                    <div class="w-12 h-12 bg-emerald-500 text-white rounded-2xl flex items-center justify-center shrink-0">
                        <span class="material-symbols-outlined">group</span>
                    </div>
                    <div>
                        <h4 class="font-bold text-emerald-900">Community Group Bonus</h4>
                        <p class="text-[11px] text-emerald-700 leading-tight">Your account receives an <strong>additional 10% discount</strong> on all bulk tiers!</p>
                    </div>
                </div>
                ` : ''}
            </div>
        `;
        
        data.grouped_by_producer.forEach(group => {
            let itemsHtml = group.items.map(item => {
                const qty = item.quantity;
                let bulkRate = 0;
                if (qty > 10) bulkRate = 0.20;
                else if (qty > 7) bulkRate = 0.15;
                else if (qty > 5) bulkRate = 0.10;
                
                const groupRate = data.is_community_group ? 0.10 : 0;
                const totalDiscount = bulkRate + groupRate;
                const multiplier = Math.max(1.0 - totalDiscount, 0.5);
                const hasDiscount = totalDiscount > 0;
                
                return `
                <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center py-8 border-b border-outline-variant/5 last:border-0 group">
                    <div class="flex gap-6 items-center flex-1">
                        <div class="w-16 h-16 bg-surface-container rounded-2xl flex items-center justify-center text-3xl opacity-40 group-hover:scale-110 transition-transform">
                            🛒
                        </div>
                        <div>
                            <h4 class="font-headline font-bold text-lg text-on-background">
                                ${item.product_name}
                                ${hasDiscount ? `<span class="ml-2 px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-black rounded uppercase tracking-widest">${(totalDiscount * 100).toFixed(0)}% Discount Applied</span>` : ''}
                            </h4>
                            <div class="flex items-center gap-3">
                                <p class="text-sm font-bold text-primary">
                                    ${hasDiscount ? `<span class="line-through text-outline opacity-50 mr-2">$${item.unit_price}</span>$${(item.unit_price * multiplier).toFixed(2)}` : `$${item.unit_price}`}
                                    <span class="text-xs text-outline font-medium tracking-tight">/ ${item.unit}</span>
                                </p>
                                ${(item.food_miles !== null && item.food_miles !== undefined) ? `
                                <div class="flex items-center gap-1 text-xs text-outline group-hover:text-emerald-600 transition-colors px-2 py-0.5 bg-surface-container-high rounded-full cursor-help" title="Food Miles = distance from the farm to you">
                                    <span class="material-symbols-outlined text-[14px]">location_on</span>
                                    <span class="font-bold">${Number(item.food_miles).toFixed(1)} km</span>
                                    ${item.food_miles < 50 ? '<span class="material-symbols-outlined text-[14px] text-emerald-500 ml-0.5">eco</span><span class="text-[9px] uppercase font-bold text-emerald-600 tracking-widest ml-0.5">Local</span>' : ''}
                                </div>
                                ` : `
                                <div class="flex items-center gap-1 text-[10px] text-outline/50 px-2 py-0.5 bg-surface-container-high rounded-full cursor-help" title="Cannot calculate distance. Please update a valid postcode in your profile.">
                                    <span class="material-symbols-outlined text-[14px]">location_off</span>
                                    <span class="font-bold uppercase tracking-widest">N/A</span>
                                </div>
                                `}
                            </div>
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
            `;}).join('');

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
                <div class="relative z-10 w-full lg:w-1/2">
                    <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-[0.3em] mb-3 block">Final Calculation</span>
                    <h3 class="font-headline text-3xl font-extrabold mb-1">Order Summary</h3>
                    <p class="text-zinc-400 text-sm font-medium mb-6">Includes all service fees and local delivery.</p>
                    
                    <!-- TC-007 & TC-018: Delivery & Recurring -->
                    <div class="grid grid-cols-1 gap-4 mb-6">
                        <div class="bg-white/5 border border-white/10 rounded-2xl p-4">
                            <label class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2 block flex items-center gap-2">
                                <span class="material-symbols-outlined text-xs">calendar_month</span>
                                Delivery Date (Min 48h Lead Time)
                            </label>
                            <input type="date" id="delivery-date-input" 
                                   class="bg-transparent text-white border-b border-white/20 focus:border-emerald-400 outline-none w-full py-1 text-sm font-bold"
                                   min="${new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString().split('T')[0]}"
                                   value="${new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString().split('T')[0]}">
                        </div>
                        
                        <div class="flex items-center justify-between bg-white/5 border border-white/10 rounded-2xl p-5 cursor-pointer hover:bg-white/10 transition-all group" onclick="const inp = document.getElementById('is-recurring-input'); inp.checked = !inp.checked;">
                            <div class="flex items-center gap-4">
                                <div class="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
                                    <span class="material-symbols-outlined">sync</span>
                                </div>
                                <div>
                                    <p class="text-xs font-bold text-white">Setup Recurring Order</p>
                                    <p class="text-[10px] text-zinc-400 font-medium">Auto-repeat this basket every 7 days</p>
                                </div>
                            </div>
                            <!-- Premium Toggle Switch -->
                            <div class="relative inline-block w-12 h-6 transition duration-200 ease-in">
                                <input type="checkbox" id="is-recurring-input" class="peer absolute w-0 h-0 opacity-0" onclick="event.stopPropagation()">
                                <span class="absolute cursor-pointer top-0 left-0 right-0 bottom-0 bg-zinc-700 rounded-full transition-all duration-300 peer-checked:bg-emerald-500 before:absolute before:content-[''] before:h-4 before:w-4 before:left-1 before:bottom-1 before:bg-white before:rounded-full before:transition-all before:duration-300 peer-checked:before:translate-x-6"></span>
                            </div>
                        </div>
                    </div>

                    ${(data.total_food_miles !== null && data.total_food_miles !== undefined) ? `
                    <div class="inline-flex items-center gap-2 bg-emerald-900/40 border border-emerald-500/20 px-3 py-1.5 rounded-full cursor-help" title="Food Miles = distance from the farm to you">
                        <span class="material-symbols-outlined text-emerald-400 text-sm">eco</span>
                        <span class="text-[11px] font-bold text-emerald-100 uppercase tracking-widest">Total Food Miles: ${Number(data.total_food_miles).toFixed(1)} km</span>
                    </div>
                    ` : `
                    <div class="inline-flex items-center gap-2 bg-zinc-800/80 border border-zinc-700/50 px-3 py-1.5 rounded-full cursor-help" title="Cannot calculate due to missing valid postcode.">
                        <span class="material-symbols-outlined text-zinc-500 text-sm">location_off</span>
                        <span class="text-[11px] font-bold text-zinc-400 uppercase tracking-widest">Total Food Miles: N/A</span>
                    </div>
                    `}
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

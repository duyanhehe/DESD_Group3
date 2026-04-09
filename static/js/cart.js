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

// Ensure global handle
window.addToCart = async function(productId, quantity = 1) {
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
            alert(data.error || 'Failed to add item to cart.');
        } else {
            // Update badge
            updateCartBadge(data.items ? data.items.length : 0);
            alert('Item added to cart!');
        }
    } catch (e) {
        console.error(e);
        alert('You must be logged in to add objects to cart.');
    }
};

async function updateCartItem(itemId, quantity) {
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
            alert(data.error || 'Invalid quantity.');
        }
        
        // Re-render
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
    if (!confirm('Are you sure you want to empty your cart?')) return;
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
    try {
        const res = await fetch('/orders/api/v1/create/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.error || 'Checkout failed.');
        } else {
            alert('Order placed successfully! Redirecting to orders page...');
            window.location.href = '/orders/api/v1/'; // To be updated to a template view in step 3
        }
    } catch (e) {
        console.error(e);
    }
}

function updateCartBadge(count) {
    const badge = document.getElementById('cart-count');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
}

async function refreshCartBadge() {
    try {
        const res = await fetch('/orders/api/v1/cart/');
        if (res.ok) {
            const data = await res.json();
            const count = data.items ? data.items.length : 0; // Number of unique items
            updateCartBadge(count);
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
            cartContent.innerHTML = `<p style="padding: 20px;">You are not logged in or have no cart yet.</p>`;
            return;
        }

        const data = await res.json();
        
        if (!data.items || data.items.length === 0) {
            cartContent.innerHTML = `
                <div style="text-align: center; padding: 40px; border: 1px dashed var(--border-light); border-radius: 12px; margin-top: 20px;">
                    <h3>Your cart is empty</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 20px;">Looks like you haven't added anything to your cart yet.</p>
                    <a href="/" class="btn btn-primary">Start Shopping</a>
                </div>
            `;
            clearBtn.style.display = 'none';
            checkoutBtn.style.display = 'none';
            return;
        }

        // Show buttons
        clearBtn.style.display = 'inline-block';
        checkoutBtn.style.display = 'inline-block';

        let html = '';
        data.grouped_by_producer.forEach(group => {
            let itemsHtml = group.items.map(item => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 0; border-bottom: 1px solid var(--border-light);">
                    <div style="flex: 2;">
                        <h4 style="margin: 0;">${item.product_name}</h4>
                        <p style="margin: 4px 0 0; font-size: 14px; color: var(--text-secondary);">$${item.unit_price} / ${item.unit}</p>
                    </div>
                    <div style="flex: 1; display: flex; align-items: center; gap: 10px;">
                        <button class="btn btn-ghost" onclick="updateCartItem(${item.id}, ${item.quantity - 1})" style="padding: 4px 8px;">-</button>
                        <span>${item.quantity}</span>
                        <button class="btn btn-ghost" onclick="updateCartItem(${item.id}, ${item.quantity + 1})" style="padding: 4px 8px;">+</button>
                    </div>
                    <div style="flex: 1; text-align: right; font-weight: 600;">
                        $${item.subtotal}
                    </div>
                    <div style="margin-left: 20px;">
                        <button class="btn btn-ghost" onclick="removeCartItem(${item.id})" style="color: red; padding: 4px 8px;">Remove</button>
                    </div>
                </div>
            `).join('');

            html += `
                <div style="background: white; border: 1px solid var(--border-light); border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.02);">
                    <div style="border-bottom: 2px solid var(--bg-color); padding-bottom: 12px; margin-bottom: 12px; display: flex; justify-content: space-between;">
                        <h3 style="margin: 0;">Farm: ${group.producer_name}</h3>
                        <span style="font-weight: 600; color: var(--text-secondary);">Subtotal: $${group.subtotal.toFixed(2)}</span>
                    </div>
                    ${itemsHtml}
                </div>
            `;
        });

        html += `
            <div style="display: flex; justify-content: flex-end; align-items: center; padding: 20px 0; font-size: 24px; font-weight: 700;">
                <span>Grand Total:</span>
                <span style="color: var(--primary); margin-left: 20px;">$${Number(data.total).toFixed(2)}</span>
            </div>
        `;

        cartContent.innerHTML = html;

    } catch (e) {
        console.error(e);
        cartContent.innerHTML = `<div class="error" style="padding: 20px;">Error loading cart.</div>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const successContent = document.getElementById('order-success-content');
    
    // Fetch latest order
    async function fetchLatestOrder() {
        try {
            const res = await fetch('/orders/api/v1/');
            if (!res.ok) throw new Error('Could not fetch orders');
            
            const orders = await res.json();
            if (orders && orders.length > 0) {
                const latestOrder = orders[0];
                renderOrderSuccess(latestOrder);
                fetchOrderRecommendations(latestOrder.id);
            } else {
                successContent.innerHTML = `
                    <div class="flex flex-col items-center justify-center py-20 text-center bg-surface-container-low rounded-[32px] border border-dashed border-outline-variant/30">
                        <span class="material-symbols-outlined text-6xl text-outline mb-6">shopping_bag</span>
                        <h3 class="font-headline text-2xl font-bold mb-2">No Recent Orders</h3>
                        <p class="text-on-surface-variant font-medium mb-8">We couldn't find any recent orders for your account.</p>
                        <a href="/" class="px-8 py-4 bg-primary text-on-primary rounded-full font-bold shadow-xl shadow-primary/20 hover:scale-105 transition-all">Start Shopping</a>
                    </div>
                `;
            }
        } catch (error) {
            console.error(error);
            successContent.innerHTML = `
                <div class="flex flex-col items-center justify-center py-20 text-center text-error">
                    <span class="material-symbols-outlined text-4xl mb-4">report</span>
                    <p class="font-bold uppercase text-xs tracking-widest">Error loading order details.</p>
                </div>
            `;
        }
    }
    
    function renderOrderSuccess(order) {
        successContent.innerHTML = `
            <div class="bg-surface-container-lowest rounded-[48px] p-12 text-center border border-outline-variant/10 shadow-xl mb-12">
                <div class="w-24 h-24 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center mx-auto mb-8 animate-in zoom-in duration-500">
                    <span class="material-symbols-outlined text-5xl">check_circle</span>
                </div>
                <h1 class="font-headline text-4xl md:text-5xl font-extrabold text-on-background tracking-tight mb-4">Payment Successful!</h1>
                <p class="text-on-surface-variant text-lg font-medium max-w-2xl mx-auto mb-8">
                    Your order <span class="font-black text-on-background">#${order.id}</span> has been confirmed. Our producers are getting your fresh items ready.
                </p>
                <div class="flex flex-wrap justify-center gap-4">
                    <a href="/orders/history/" class="px-8 py-4 bg-surface-container-high text-on-surface-variant rounded-full font-bold shadow-sm hover:bg-surface-container-highest transition-all active:scale-95">
                        View Order Details
                    </a>
                    <a href="/" class="px-8 py-4 bg-primary text-on-primary rounded-full font-bold shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all">
                        Continue Shopping
                    </a>
                </div>
            </div>
        `;
    }
    
    async function fetchOrderRecommendations(orderId) {
        const recContainer = document.getElementById('order-recommendations');
        if (!recContainer) return;
        
        try {
            const res = await fetch(`/ai/recommendations/order/${orderId}/`);
            if (!res.ok) return;
            
            const data = await res.json();
            if (data.products && data.products.length > 0) {
                recContainer.innerHTML = `
                    <div class="space-y-12">
                        <div class="max-w-xl text-center mx-auto">
                            <span class="text-[10px] font-bold text-primary uppercase tracking-[0.2em] mb-3 block">Wait, there's more</span>
                            <h2 class="font-headline text-3xl font-extrabold text-on-background tracking-tight italic">Based on your order</h2>
                            <p class="text-on-surface-variant text-sm font-medium leading-relaxed mt-2">
                                <span class="material-symbols-outlined text-primary text-base inline-block align-middle mr-1">auto_awesome</span>
                                ${data.explanation || 'Customers who bought these items also enjoyed:'}
                            </p>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
                            ${data.products.slice(0, 4).map(p => `
                                <div class="bg-surface-container-low rounded-3xl overflow-hidden group hover:shadow-xl transition-all duration-300 border border-outline-variant/10 flex flex-col p-4 cursor-pointer" onclick="window.location.href='/products/${p.id}/'">
                                    <div class="aspect-[4/3] bg-surface-container rounded-2xl flex items-center justify-center text-5xl opacity-40 group-hover:scale-105 transition-transform duration-500 mb-4">
                                        🛒
                                    </div>
                                    <h4 class="font-headline font-bold text-on-background text-[11px] mb-1 uppercase tracking-wider h-8 line-clamp-2">${p.name}</h4>
                                    <div class="flex justify-between items-center mt-auto pt-3 border-t border-outline-variant/5">
                                        <span class="text-sm font-black text-primary">$${p.price}</span>
                                        <button onclick="event.stopPropagation(); window.addToCart(${p.id})" class="px-3 py-1.5 bg-zinc-900 text-white rounded-full text-[10px] font-bold hover:bg-emerald-700 transition-colors">
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
        } catch (error) {
            console.error('Error fetching order recommendations:', error);
        }
    }
    
    fetchLatestOrder();
});

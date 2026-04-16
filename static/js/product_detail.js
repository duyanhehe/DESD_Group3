document.addEventListener('DOMContentLoaded', () => {
    const detailContent = document.getElementById('product-detail-content');

    const allergenIcons = {
        'Cereals containing gluten': '🌾',
        'Crustaceans': '🦐',
        'Eggs': '🥚',
        'Fish': '🐟',
        'Peanuts': '🥜',
        'Soya': '🫘',
        'Milk': '🥛',
        'Nuts': '🥜',
        'Celery': '🥗',
        'Mustard': '🌭',
        'Sesame': '🥯',
        'Sulphur dioxide': '🧂',
        'Lupin': '🌱',
        'Molluscs': '🐚',
        'None': '✅',
        'Not Applicable': '✅'
    };

    const categoryIcons = {
        'Fruits': '🍎',
        'Vegetables': '🥕',
        'Dairy': '🥛',
        'Bakery': '🍞',
        'Meat': '🥩',
        'Seafood': '🐟',
        'Drinks': '🥤',
        'None': '🛒'
    };

    async function fetchProductDetail() {
        try {
            const response = await fetch(`/products/api/v1/${PRODUCT_ID}/`);
            if (!response.ok) throw new Error('Product not found');
            const product = await response.json();
            renderProductDetail(product);
        } catch (error) {
            console.error('Product fetch error:', error);
            detailContent.innerHTML = `
                <div class="flex flex-col items-center justify-center py-24 text-center bg-surface-container-low rounded-[48px] border border-dashed border-outline-variant/30">
                    <span class="material-symbols-outlined text-6xl text-outline mb-6">search_off</span>
                    <h2 class="font-headline text-2xl font-bold mb-2">Product Not Found</h2>
                    <p class="text-on-surface-variant font-medium mb-8">The item you're looking for might have been removed or is currently unavailable.</p>
                    <a href="/" class="px-8 py-3 bg-primary text-on-primary rounded-full font-bold shadow-lg shadow-primary/20">Back to Marketplace</a>
                </div>
            `;
        }
    }

    function renderProductDetail(product) {
        const isSafe = product.allergen_names.some(name =>
            name.toLowerCase().includes('none') || name.toLowerCase().includes('not applicable')
        );

        const prodIcon = categoryIcons[product.category_name] || '🛒';
        const isInStock = product.stock_quantity > 0;

        detailContent.innerHTML = `
            <div class="grid lg:grid-cols-2 gap-16 items-start">
                <!-- Visual Panel -->
                <div class="relative">
                    <div class="aspect-square bg-surface-container-low rounded-[32px] flex items-center justify-center text-9xl shadow-inner border border-outline-variant/5">
                        ${prodIcon}
                    </div>
                    <!-- Category Badge -->
                    <div class="absolute top-6 left-6">
                        <span class="px-4 py-1.5 bg-white/90 backdrop-blur-md text-primary text-[10px] font-black rounded-full uppercase tracking-widest border border-white/20 shadow-sm">
                            ${product.category_name || 'Fresh Produce'}
                        </span>
                    </div>
                </div>

                <!-- Info Panel -->
                <div class="py-4 space-y-8">
                    <!-- Producer -->
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-xl bg-secondary-container flex items-center justify-center text-sm">👨‍🌾</div>
                        <span class="text-[10px] font-extrabold text-on-surface-variant uppercase tracking-[0.2em]">Produced by ${product.producer_name}</span>
                    </div>

                    <!-- Name -->
                    <h1 class="font-headline text-4xl lg:text-5xl font-extrabold text-on-background leading-tight tracking-tight">
                        ${product.name}
                    </h1>

                    <!-- Price -->
                    <div class="flex items-baseline gap-2">
                        <span class="text-3xl font-black text-primary">$${product.price}</span>
                        <span class="text-sm font-bold text-outline uppercase tracking-tighter">/ ${product.unit || 'item'}</span>
                    </div>

                    <!-- Stock indicator -->
                    <div class="inline-flex items-center gap-2">
                        <div class="w-2 h-2 rounded-full ${isInStock ? 'bg-emerald-500 animate-pulse' : 'bg-error'}"></div>
                        <span class="text-[10px] font-extrabold uppercase tracking-widest ${isInStock ? 'text-emerald-700' : 'text-error'}">
                            ${isInStock ? `${product.stock_quantity} in stock` : 'Out of Stock'}
                        </span>
                    </div>

                    <!-- Description -->
                    <div class="space-y-3">
                        <h3 class="text-[10px] font-extrabold text-outline uppercase tracking-widest">About this product</h3>
                        <p class="text-on-surface-variant leading-relaxed">${product.description}</p>
                    </div>

                    <!-- Allergen Panel -->
                    <div class="p-6 rounded-[24px] border ${isSafe ? 'bg-emerald-50/50 border-emerald-100' : 'bg-amber-50/50 border-amber-100'}">
                        <h4 class="text-[10px] font-extrabold uppercase tracking-widest mb-3 ${isSafe ? 'text-emerald-700' : 'text-amber-700'}">
                            ${isSafe ? '🟢 Food Safety — No Common Allergens' : '⚠️ Allergen Warning'}
                        </h4>
                        <div class="flex flex-wrap gap-2">
                            ${product.allergen_names.map(name => {
                                const icon = allergenIcons[name] || '⚠️';
                                return `<span class="px-3 py-1 rounded-full text-xs font-bold ${isSafe ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">${icon} ${name}</span>`;
                            }).join('')}
                        </div>
                        ${!isSafe ? '<p class="text-[11px] text-amber-600 font-medium mt-3">Please exercise caution if you have severe food allergies.</p>' : ''}
                    </div>

                    <!-- Add to Cart -->
                    <button
                        onclick="window.addToCart(${product.id})"
                        ${isInStock ? '' : 'disabled'}
                        class="w-full py-5 bg-primary text-on-primary rounded-full font-extrabold text-lg shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-3 ${isInStock ? '' : 'opacity-50 cursor-not-allowed'}">
                        <span class="material-symbols-outlined">add_shopping_cart</span>
                        ${isInStock ? 'Add to Cart' : 'Out of Stock'}
                    </button>
                </div>
            </div>
        `;
    }

    fetchProductDetail();
});

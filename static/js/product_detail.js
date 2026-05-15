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

            // Fetch related products
            fetchRelatedProducts();
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

    async function fetchRelatedProducts() {
        const relatedContainer = document.getElementById('related-products');
        try {
            const res = await fetch(`/ai/recommendations/product/${PRODUCT_ID}/`);
            if (!res.ok) return;

            const data = await res.json();
            if (data.products && data.products.length > 0) {
                relatedContainer.innerHTML = `
                    <div class="space-y-10">
                        <div class="max-w-xl">
                            <span class="text-[10px] font-bold text-primary uppercase tracking-[0.2em] mb-2 block">Perfect Pairing</span>
                            <h2 class="font-headline text-3xl font-extrabold text-on-background">Frequently Bought Together</h2>
                            <p class="text-on-surface-variant text-sm font-medium mt-1">Customers who selected this harvest also appreciated these items.</p>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
                            ${data.products.slice(0, 4).map(p => createSimpleProductCard(p)).join('')}
                        </div>
                    </div>
                `;
                relatedContainer.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error fetching related products:', error);
        }
    }

    function createSimpleProductCard(product) {
        const icon = categoryIcons[product.category_name] || '🛍';
        return `
            <div class="bg-surface-container-lowest rounded-3xl overflow-hidden group hover:shadow-xl transition-all duration-300 border border-outline-variant/5 flex flex-col cursor-pointer"
                 onclick="window.location.href='/products/${product.id}/'">
                <div class="aspect-[4/3] relative overflow-hidden bg-surface-container">
                    <div class="absolute inset-0 flex items-center justify-center text-4xl opacity-30 group-hover:scale-105 transition-transform">
                        ${icon}
                    </div>
                    ${product.image_url ? `<img src="${product.image_url}" class="w-full h-full object-cover relative z-10 group-hover:scale-105 transition-transform duration-500" alt="${product.name}">` : ''}
                </div>
                <div class="p-5 flex-grow flex flex-col">
                    <h3 class="font-headline font-bold text-on-background text-sm mb-1 group-hover:text-primary transition-colors">${product.name}</h3>
                    <div class="flex justify-between items-center mt-auto">
                        <span class="text-sm font-black text-primary">$${product.price}</span>
                        <button onclick="event.stopPropagation(); window.addToCart(${product.id})" 
                                class="w-8 h-8 bg-surface-container-high text-on-surface-variant hover:bg-primary hover:text-on-primary rounded-xl flex items-center justify-center transition-all active:scale-90">
                            <span class="material-symbols-outlined text-sm">add_shopping_cart</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    function renderProductDetail(product) {
        const isSafe = product.allergen_names.some(name =>
            name.toLowerCase().includes('none') || name.toLowerCase().includes('not applicable')
        );

        const prodIcon = categoryIcons[product.category_name] || '🛒';
        const isInStock = product.stock_quantity > 0;
        const isOrganic = product.is_organic;
        const isSurplus = product.is_surplus;
        const hasDiscount = isSurplus && product.discount_price;

        detailContent.innerHTML = `
            <div class="grid lg:grid-cols-2 gap-16 items-start">
                <!-- Visual Panel -->
                <div class="relative group">
                    <div class="aspect-square bg-surface-container-low rounded-[32px] flex items-center justify-center text-9xl shadow-inner border border-outline-variant/5 overflow-hidden">
                        <div class="absolute inset-0 flex items-center justify-center opacity-20 group-hover:scale-110 transition-transform duration-700">
                            ${prodIcon}
                        </div>
                        ${(product.image_url || product.image) ? `<img src="${product.image_url || product.image}" class="w-full h-full object-cover relative z-10 group-hover:scale-105 transition-transform duration-700" alt="${product.name}">` : ''}
                    </div>
                    <!-- Category Badge -->
                    <div class="absolute top-6 left-6 flex flex-col gap-2">
                        <span class="px-4 py-1.5 bg-white/90 backdrop-blur-md text-primary text-[10px] font-black rounded-full uppercase tracking-widest border border-white/20 shadow-sm">
                            ${product.category_name || 'Fresh Produce'}
                        </span>
                        ${isOrganic ? `
                        <span class="px-4 py-1.5 bg-emerald-600 text-white text-[10px] font-black rounded-full uppercase tracking-widest shadow-sm flex items-center gap-2">
                            <span class="material-symbols-outlined text-xs">verified</span> Organic
                        </span>` : ''}
                    </div>
                    
                    ${isSurplus ? `
                    <div class="absolute bottom-6 right-6">
                        <span class="px-4 py-2 bg-amber-400 text-amber-950 text-[11px] font-black rounded-2xl uppercase tracking-widest shadow-xl border-2 border-white flex items-center gap-2 rotate-3">
                            <span class="material-symbols-outlined text-sm">local_fire_department</span> Surplus Deal
                        </span>
                    </div>` : ''}
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

                    <!-- Rating -->
                    ${product.reviews && product.reviews.length > 0 ? `
                        <div class="flex items-center gap-2 cursor-pointer" onclick="document.getElementById('reviews-list').scrollIntoView({behavior: 'smooth'})">
                            <div class="flex text-amber-400">
                                <span class="material-symbols-outlined text-lg" style="font-variation-settings: 'FILL' 1;">star</span>
                            </div>
                            <span class="text-sm font-bold text-on-surface">${(product.reviews.reduce((sum, r) => sum + r.rating, 0) / product.reviews.length).toFixed(1)}</span>
                            <span class="text-sm font-medium text-outline-variant underline decoration-outline-variant/30 hover:text-primary transition-colors">(${product.reviews.length} reviews)</span>
                        </div>
                    ` : `
                        <div class="flex items-center gap-2 cursor-pointer" onclick="document.getElementById('reviews-list').scrollIntoView({behavior: 'smooth'})">
                            <span class="material-symbols-outlined text-lg text-zinc-300">star</span>
                            <span class="text-sm font-medium text-outline-variant hover:text-primary transition-colors">No reviews yet. Be the first!</span>
                        </div>
                    `}

                    <!-- Price -->
                    <div class="flex items-baseline gap-2">
                        ${hasDiscount ? `
                            <span class="text-3xl font-black text-emerald-600">$${product.discount_price}</span>
                            <span class="text-lg font-bold text-outline line-through">$${product.price}</span>
                        ` : `
                            <span class="text-3xl font-black text-primary">$${product.price}</span>
                        `}
                        <span class="text-sm font-bold text-outline uppercase tracking-tighter">/ ${product.unit || 'item'}</span>
                    </div>

                    <!-- Seasonal Availability (TC-016) -->
                    ${(product.season_start_month && product.season_end_month) ? `
                    <div class="inline-flex items-center gap-3 bg-amber-50 px-5 py-3 rounded-2xl border border-amber-200">
                        <div class="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-600">
                            <span class="material-symbols-outlined text-xl">calendar_today</span>
                        </div>
                        <div>
                            <p class="text-[9px] font-black text-amber-800 uppercase tracking-widest">Seasonal Availability</p>
                            <p class="text-xs font-bold text-amber-700">Available: ${[
                                "January", "February", "March", "April", "May", "June",
                                "July", "August", "September", "October", "November", "December"
                            ][product.season_start_month - 1]} - ${[
                                "January", "February", "March", "April", "May", "June",
                                "July", "August", "September", "October", "November", "December"
                            ][product.season_end_month - 1]}</p>
                        </div>
                    </div>
                    ` : ''}

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

                    <!-- Food Miles (TC-013) -->
                    ${product.food_miles !== null ? `
                    <div class="inline-flex items-center gap-2 bg-emerald-50 px-4 py-2 rounded-2xl border border-emerald-100">
                        <span class="material-symbols-outlined text-emerald-600 text-lg">eco</span>
                        <div>
                            <p class="text-[9px] font-black text-emerald-800 uppercase tracking-widest">Local Impact</p>
                            <p class="text-xs font-bold text-emerald-700">${Number(product.food_miles).toFixed(1)} food miles from farm to you</p>
                        </div>
                    </div>
                    ` : ''}

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

            <!-- Educational Content (TC-020) -->
            ${(product.recipes.length > 0 || product.farm_stories.length > 0) ? `
            <div class="mt-24 space-y-16">
                <div class="grid md:grid-cols-2 gap-12">
                    ${product.recipes.length > 0 ? `
                    <div class="space-y-8">
                        <div class="flex items-center gap-3">
                            <span class="material-symbols-outlined text-primary">menu_book</span>
                            <h3 class="font-headline text-2xl font-extrabold">Recipe Suggestions</h3>
                        </div>
                        <div class="grid grid-cols-1 gap-4">
                            ${product.recipes.map(r => `
                                <a href="/education/" class="flex items-center gap-4 p-4 bg-surface-container-low rounded-[24px] border border-outline-variant/10 hover:border-primary/20 transition-all group">
                                    <div class="w-16 h-16 rounded-xl overflow-hidden bg-surface-container flex-shrink-0">
                                        ${r.image ? `<img src="${r.image}" class="w-full h-full object-cover">` : '<div class="w-full h-full flex items-center justify-center text-xl">🥗</div>'}
                                    </div>
                                    <div>
                                        <h4 class="font-bold text-sm group-hover:text-primary transition-colors">${r.title}</h4>
                                        <p class="text-[9px] font-bold text-outline uppercase tracking-widest mt-1">View Recipe</p>
                                    </div>
                                </a>
                            `).join('')}
                        </div>
                    </div>` : ''}

                    ${product.farm_stories.length > 0 ? `
                    <div class="space-y-8">
                        <div class="flex items-center gap-3">
                            <span class="material-symbols-outlined text-primary">potted_plant</span>
                            <h3 class="font-headline text-2xl font-extrabold">Farm Stories</h3>
                        </div>
                        <div class="grid grid-cols-1 gap-4">
                            ${product.farm_stories.map(s => `
                                <a href="/education/" class="flex items-center gap-4 p-4 bg-surface-container-low rounded-[24px] border border-outline-variant/10 hover:border-primary/20 transition-all group">
                                    <div class="w-16 h-16 rounded-xl overflow-hidden bg-surface-container flex-shrink-0">
                                        ${s.image ? `<img src="${s.image}" class="w-full h-full object-cover">` : '<div class="w-full h-full flex items-center justify-center text-2xl">🚜</div>'}
                                    </div>
                                    <div>
                                        <h4 class="font-bold text-sm group-hover:text-primary transition-colors">${s.title}</h4>
                                        <p class="text-[9px] font-bold text-outline uppercase tracking-widest mt-1">Meet the Producer</p>
                                    </div>
                                </a>
                            `).join('')}
                        </div>
                    </div>` : ''}
                </div>
            </div>` : ''}

            <!-- Reviews Section (TC-024) -->
            <div class="mt-32 pt-20 border-t border-outline-variant/10">
                <div class="grid lg:grid-cols-12 gap-16">
                    <div class="lg:col-span-4">
                        <span class="text-[10px] font-bold text-primary uppercase tracking-[0.2em] mb-2 block">Customer Voice</span>
                        <h2 class="font-headline text-3xl font-extrabold text-on-background mb-4">Community Reviews</h2>
                        <p class="text-on-surface-variant font-medium text-sm leading-relaxed mb-8">
                            Only verified purchasers can leave reviews to ensure the highest quality feedback for our community.
                        </p>
                        
                        <!-- Review Form (Hidden by default, shown if can_review) -->
                        ${product.can_review ? `
                        <div id="review-form-container" class="bg-surface-container-low p-8 rounded-[32px] border border-outline-variant/5">
                            <h4 class="font-bold text-sm mb-4">Share your experience</h4>
                            <form id="review-form" class="space-y-4">
                                <div>
                                    <label class="text-[10px] font-bold text-outline uppercase mb-2 block">Rating</label>
                                    <div class="flex gap-2" id="star-rating">
                                        ${[1, 2, 3, 4, 5].map(i => `<span class="material-symbols-outlined cursor-pointer text-zinc-300 hover:text-amber-400 transition-colors" data-value="${i}">star</span>`).join('')}
                                    </div>
                                    <input type="hidden" name="rating" id="rating-input" value="5">
                                </div>
                                <div>
                                    <label class="text-[10px] font-bold text-outline uppercase mb-2 block">Your Comment</label>
                                    <textarea name="comment" rows="3" class="w-full px-5 py-3 bg-white border-none rounded-2xl focus:ring-2 focus:ring-primary/20 font-medium text-sm resize-none" placeholder="What did you think of this harvest?"></textarea>
                                </div>
                                <button type="submit" class="w-full py-3 bg-secondary-container text-on-secondary-container rounded-full font-bold text-sm hover:bg-secondary transition-all">Submit Review</button>
                            </form>
                            <p id="review-feedback" class="text-[10px] font-bold mt-4 text-center hidden"></p>
                        </div>
                        ` : ''}
                    </div>

                    <div class="lg:col-span-8">
                        <div class="space-y-6" id="reviews-list">
                            ${product.reviews && product.reviews.length > 0 ? product.reviews.map(r => `
                                <div class="p-8 bg-white/50 border border-outline-variant/10 rounded-[32px] space-y-4">
                                    <div class="flex justify-between items-start">
                                        <div class="flex items-center gap-3">
                                            <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center font-black text-primary text-xs">${r.customer_name[0].toUpperCase()}</div>
                                            <div>
                                                <p class="font-bold text-sm">${r.customer_name}</p>
                                                <p class="text-[10px] text-outline font-medium">${new Date(r.created_at).toLocaleDateString()}</p>
                                            </div>
                                        </div>
                                        <div class="flex text-amber-400">
                                            ${Array(r.rating).fill('<span class="material-symbols-outlined text-sm">star</span>').join('')}
                                        </div>
                                    </div>
                                    <p class="text-on-surface-variant text-sm font-medium leading-relaxed italic">"${r.comment}"</p>
                                </div>
                            `).join('') : `
                                <div class="flex flex-col items-center justify-center py-20 text-center bg-surface-container-low/30 rounded-[32px] border border-dashed border-outline-variant/20">
                                    <span class="material-symbols-outlined text-4xl text-outline mb-4">chat_bubble</span>
                                    <p class="text-sm font-bold text-outline-variant uppercase tracking-widest">No reviews yet</p>
                                    <p class="text-xs text-on-surface-variant mt-2 font-medium">Be the first to share your thoughts on this harvest.</p>
                                </div>
                            `}
                        </div>
                    </div>
                </div>
            </div>
        `;

        setupReviewForm(product.id);
    }

    function setupReviewForm(productId) {
        const stars = document.querySelectorAll('#star-rating span');
        const ratingInput = document.getElementById('rating-input');
        const form = document.getElementById('review-form');
        const feedback = document.getElementById('review-feedback');

        stars.forEach(star => {
            star.addEventListener('click', () => {
                const val = star.dataset.value;
                ratingInput.value = val;
                stars.forEach(s => {
                    s.classList.toggle('text-amber-400', s.dataset.value <= val);
                    s.classList.toggle('text-zinc-300', s.dataset.value > val);
                    s.style.fontVariationSettings = s.dataset.value <= val ? "'FILL' 1" : "'FILL' 0";
                });
            });
        });

        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const data = {
                    rating: parseInt(formData.get('rating')),
                    comment: formData.get('comment')
                };

                try {
                    const response = await fetch(`/products/api/v1/${productId}/add_review/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': window.getCookie('csrftoken') || ''
                        },
                        body: JSON.stringify(data)
                    });

                    const result = await response.json();
                    if (response.ok) {
                        feedback.innerText = 'Review submitted successfully!';
                        feedback.className = 'text-[10px] font-bold mt-4 text-center text-emerald-600';
                        feedback.classList.remove('hidden');
                        setTimeout(() => location.reload(), 1500);
                    } else {
                        feedback.innerText = result.error || 'Failed to submit review.';
                        feedback.className = 'text-[10px] font-bold mt-4 text-center text-error';
                        feedback.classList.remove('hidden');
                    }
                } catch (error) {
                    feedback.innerText = 'Connection error.';
                    feedback.classList.remove('hidden');
                }
            });
        }
    }

    fetchProductDetail();
});

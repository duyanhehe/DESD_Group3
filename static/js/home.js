document.addEventListener('DOMContentLoaded', () => {
    const categoryPillsContainer = document.getElementById('category-pills');
    const marketplaceContent = document.getElementById('marketplace-content');
    const searchInput = document.getElementById('global-search');

    let allProducts = [];
    let allCategories = [];

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

    // Initialize
    async function init() {
        try {
            // Start fetching recommendations in parallel
            fetchAIRecommendations();

            const [catRes, prodRes] = await Promise.all([
                fetch('/categories/api/v1/'),
                fetch('/products/api/v1/')
            ]);

            if (!catRes.ok || !prodRes.ok) {
                console.error('API Error:', catRes.status, prodRes.status);
                throw new Error('Failed to fetch marketplace data');
            }

            const categories = await catRes.json();
            const products = await prodRes.json();

            allCategories = categories;
            allProducts = products;

            if (!Array.isArray(categories) || !Array.isArray(products)) {
                throw new Error('Invalid data format received from server');
            }

            renderCategories(categories);
            renderMarketplace(categories, products);
            
            // Setup Search
            searchInput.addEventListener('input', (e) => {
                const term = e.target.value.toLowerCase();
                filterProducts(term);
            });

        } catch (error) {
            console.error('Error fetching marketplace data:', error);
            marketplaceContent.innerHTML = `
                <div class="flex flex-col items-center justify-center p-20 text-center">
                    <span class="material-symbols-outlined text-6xl text-error mb-4">error</span>
                    <h3 class="font-headline text-2xl font-bold mb-2">Oops! Something went wrong</h3>
                    <p class="text-on-surface-variant">${error.message}</p>
                </div>
            `;
        }
    }

    async function fetchAIRecommendations() {
        try {
            const res = await fetch('/ai/recommendations/homepage/');
            if (!res.ok) return;

            const data = await res.json();
            
            // 1. Render Trending
            if (data.trending && data.trending.length > 0) {
                const trendingContainer = document.getElementById('trending-recommendations');
                trendingContainer.innerHTML = `
                    <div class="space-y-8">
                        <div class="flex items-end justify-between border-b border-outline-variant/10 pb-6">
                            <div class="max-w-xl">
                                <span class="text-[10px] font-bold text-primary uppercase tracking-[0.2em] mb-2 block">Hot Harvest</span>
                                <h2 class="font-headline text-3xl font-extrabold text-on-background">Trending Now</h2>
                                <p class="text-on-surface-variant text-sm font-medium mt-1">Discover what other food enthusiasts are loving this week.</p>
                            </div>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
                            ${data.trending.slice(0, 4).map(p => renderProductCard(p)).join('')}
                        </div>
                    </div>
                `;
                
                // Only show if "All Items" is currently selected (or if pills aren't rendered yet)
                const activePill = categoryPillsContainer.querySelector('.bg-primary');
                if (!activePill || activePill.getAttribute('data-id') === 'all') {
                    trendingContainer.classList.remove('hidden');
                }
            }

            // 2. Render Personalized
            if (data.personalized && data.personalized.length > 0) {
                const personaContainer = document.getElementById('personalized-recommendations');
                personaContainer.innerHTML = `
                    <div class="space-y-8 bg-primary/5 p-10 rounded-[48px] border border-primary/10 relative overflow-hidden">
                        <div class="absolute -right-20 -top-20 w-64 h-64 bg-primary/5 rounded-full blur-3xl"></div>
                        <div class="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-end gap-6 border-b border-primary/10 pb-8">
                            <div class="max-w-xl">
                                <span class="text-[10px] font-bold text-primary uppercase tracking-[0.2em] mb-2 block">Curated just for you</span>
                                <h2 class="font-headline text-3xl font-extrabold text-on-background">Personalized Picks</h2>
                                <p class="text-on-surface-variant text-sm font-medium mt-2 leading-relaxed">
                                    <span class="material-symbols-outlined text-primary text-base inline-block align-middle mr-1">auto_awesome</span>
                                    ${data.personalized_explanation || 'Based on your recent interests and seasonal favorites.'}
                                </p>
                            </div>
                        </div>
                        <div class="relative z-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
                            ${data.personalized.slice(0, 4).map(p => renderProductCard(p)).join('')}
                        </div>
                    </div>
                `;
                
                // Only show if "All Items" is currently selected (or if pills aren't rendered yet)
                const activePill = categoryPillsContainer.querySelector('.bg-primary');
                if (!activePill || activePill.getAttribute('data-id') === 'all') {
                    personaContainer.classList.remove('hidden');
                }
            }

        } catch (error) {
            console.error('Error fetching AI recommendations:', error);
        }
    }

    /**
     * Toggles the visibility of AI recommendation sections.
     * @param {boolean} show - Whether to show or hide sections.
     */
    function toggleRecommendationSections(show) {
        const personaContainer = document.getElementById('personalized-recommendations');
        const trendingContainer = document.getElementById('trending-recommendations');

        if (show) {
            // Show only if they have been populated with content
            if (personaContainer && personaContainer.innerHTML.trim() !== '') {
                personaContainer.classList.remove('hidden');
            }
            if (trendingContainer && trendingContainer.innerHTML.trim() !== '') {
                trendingContainer.classList.remove('hidden');
            }
        } else {
            personaContainer?.classList.add('hidden');
            trendingContainer?.classList.add('hidden');
        }
    }

    function renderCategories(categories) {
        const pillClass = "pill flex-shrink-0 px-6 py-2.5 rounded-full font-bold text-sm transition-all cursor-pointer whitespace-nowrap flex items-center gap-2 border border-outline-variant/10";
        const activeClass = "bg-primary text-on-primary shadow-lg shadow-primary/20 scale-105";
        const inactiveClass = "bg-surface-container-high text-on-surface-variant hover:bg-emerald-50 hover:text-primary hover:border-primary/20";

        categoryPillsContainer.innerHTML = `
            <div class="${pillClass} ${activeClass}" data-id="all">
                <span class="material-symbols-outlined text-sm">grid_view</span>
                All Items
            </div>
            <div class="${pillClass} ${inactiveClass}" data-id="organic">
                <span class="material-symbols-outlined text-base text-emerald-500" style="font-variation-settings: 'FILL' 1;">eco</span>
                Organic
            </div>
            <div class="${pillClass} ${inactiveClass}" data-id="surplus">
                <span class="material-symbols-outlined text-base text-amber-500" style="font-variation-settings: 'FILL' 1;">bolt</span>
                Surplus
            </div>
            ${categories.map(cat => `
                <div class="${pillClass} ${inactiveClass}" data-id="${cat.id}">
                    <span class="text-base">${categoryIcons[cat.name] || '🛒'}</span>
                    ${cat.name}
                </div>
            `).join('')}
        `;

        // Handle Click
        categoryPillsContainer.querySelectorAll('.pill').forEach(pill => {
            pill.addEventListener('click', () => {
                categoryPillsContainer.querySelectorAll('.pill').forEach(p => {
                    p.classList.remove(...activeClass.split(' '));
                    p.classList.add(...inactiveClass.split(' '));
                });
                pill.classList.remove(...inactiveClass.split(' '));
                pill.classList.add(...activeClass.split(' '));
                
                const categoryId = pill.getAttribute('data-id');

                // Toggle AI sections: Show only for "All Items"
                toggleRecommendationSections(categoryId === 'all');

                if (categoryId === 'all') {
                    renderMarketplace(allCategories, allProducts);
                } else if (categoryId === 'organic') {
                    // Show all organic products
                    const filteredProd = allProducts.filter(p => p.is_organic);
                    renderMarketplace(allCategories, filteredProd);
                } else if (categoryId === 'surplus') {
                    const filteredProd = allProducts.filter(p => p.is_surplus);
                    renderMarketplace(allCategories, filteredProd);
                } else {
                    const filteredCat = allCategories.filter(c => c.id == categoryId);
                    const filteredProd = allProducts.filter(p => p.category == categoryId);
                    renderMarketplace(filteredCat, filteredProd);
                }
            });
        });
    }

    function renderMarketplace(categories, products) {
        if (products.length === 0) {
            marketplaceContent.innerHTML = `
                <div class="flex flex-col items-center justify-center p-20 text-center bg-surface-container-low rounded-3xl border border-dashed border-outline-variant">
                    <span class="material-symbols-outlined text-6xl text-outline mb-4">search_off</span>
                    <p class="text-on-surface-variant font-medium">No products found matching your criteria.</p>
                </div>
            `;
            return;
        }

        const grouped = {};
        products.forEach(p => {
            const catId = p.category || 'uncategorized';
            if (!grouped[catId]) grouped[catId] = [];
            grouped[catId].push(p);
        });

        marketplaceContent.innerHTML = categories.map(cat => {
            const catProducts = grouped[cat.id] || [];
            if (catProducts.length === 0) return '';

            return `
                <section class="space-y-8" id="cat-${cat.id}">
                    <div class="flex flex-col md:flex-row justify-between items-end gap-4 border-b border-outline-variant/10 pb-6">
                        <div class="max-w-xl">
                            <h2 class="font-headline text-3xl font-extrabold text-on-background">${cat.name}</h2>
                            <p class="text-on-surface-variant text-sm font-medium mt-1">Freshly picked from our local partner farms.</p>
                        </div>
                        <button onclick="document.querySelector('[data-id=\'${cat.id}\']')?.click()" class="text-primary font-bold flex items-center gap-2 group text-sm hover:gap-3 transition-all">
                            View all ${cat.name}
                            <span class="material-symbols-outlined transition-transform group-hover:translate-x-1 text-base">arrow_forward</span>
                        </button>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
                        ${catProducts.map(p => renderProductCard(p)).join('')}
                    </div>
                </section>
            `;
        }).join('');
    }

    function renderProductCard(product) {
        const icon = categoryIcons[product.category_name] || '🛍';
        return `
            <div class="bg-surface-container-lowest rounded-3xl overflow-hidden group hover:shadow-2xl transition-all duration-300 border border-outline-variant/5 hover:border-primary/10 flex flex-col cursor-pointer"
                 data-name="${product.name.toLowerCase()}"
                 onclick="window.location.href='/products/${product.id}/'">
                <div class="aspect-[4/3] relative overflow-hidden bg-surface-container">
                    <div class="absolute inset-0 flex items-center justify-center text-5xl opacity-40 group-hover:scale-110 transition-transform duration-500">
                        ${icon}
                    </div>
                    ${(product.image_url || product.image) ? `<img src="${product.image_url || product.image}" class="w-full h-full object-cover relative z-10 group-hover:scale-105 transition-transform duration-500" alt="${product.name}">` : ''}

                    <div class="absolute top-4 left-4 z-20 flex flex-col gap-2">
                        <span class="px-3 py-1 bg-white/80 backdrop-blur-md text-primary text-[10px] font-bold rounded-full uppercase tracking-widest border border-white/20">
                            ${product.category_name || 'Stock'}
                        </span>
                        ${product.is_organic ? `
                            <span class="px-3 py-1 bg-emerald-500/90 backdrop-blur-md text-white text-[10px] font-bold rounded-full uppercase tracking-widest flex items-center gap-1">
                                <span class="material-symbols-outlined text-[10px]" style="font-variation-settings: 'FILL' 1;">eco</span>
                                Organic
                            </span>
                        ` : ''}
                        ${product.is_surplus ? `
                            <span class="px-3 py-1 bg-amber-500/90 backdrop-blur-md text-white text-[10px] font-bold rounded-full uppercase tracking-widest flex items-center gap-1">
                                <span class="material-symbols-outlined text-[10px]" style="font-variation-settings: 'FILL' 1;">bolt</span>
                                Surplus
                            </span>
                        ` : ''}
                    </div>

                    <!-- Quick-add button: stopPropagation so card click doesn't also fire -->
                    <button onclick="event.stopPropagation(); window.addToCart(${product.id})" 
                            class="absolute bottom-4 right-4 z-20 w-10 h-10 bg-primary text-on-primary rounded-2xl flex items-center justify-center shadow-lg transform translate-y-12 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all hover:bg-primary-container active:scale-90"
                            title="Add to cart">
                        <span class="material-symbols-outlined">add_shopping_cart</span>
                    </button>
                </div>

                <div class="p-6 flex-grow flex flex-col">
                    <div class="flex justify-between items-start mb-2">
                        <div>
                            <h3 class="font-headline font-bold text-on-background leading-tight text-lg group-hover:text-primary transition-colors">${product.name}</h3>
                            ${product.reviews && product.reviews.length > 0 ? `
                                <div class="flex items-center gap-1 mt-1">
                                    <span class="material-symbols-outlined text-[12px] text-amber-400" style="font-variation-settings: 'FILL' 1;">star</span>
                                    <span class="text-[10px] font-bold text-on-surface-variant">${(product.reviews.reduce((sum, r) => sum + r.rating, 0) / product.reviews.length).toFixed(1)}</span>
                                    <span class="text-[10px] font-medium text-outline">(${product.reviews.length})</span>
                                </div>
                            ` : `
                                <div class="flex items-center gap-1 mt-1">
                                    <span class="material-symbols-outlined text-[12px] text-zinc-300">star</span>
                                    <span class="text-[10px] font-medium text-outline">No reviews</span>
                                </div>
                            `}
                        </div>
                        <div class="text-right flex-shrink-0 ml-4">
                            ${product.is_surplus && product.discount_price ? `
                                <span class="text-xs text-outline line-through block font-bold">$${product.price}</span>
                                <span class="text-lg font-extrabold text-error">$${product.discount_price}</span>
                            ` : `
                                <span class="text-lg font-extrabold text-primary">$${product.price}</span>
                            `}
                            <span class="block text-[10px] text-outline font-bold uppercase tracking-tighter">/ ${product.unit || 'item'}</span>
                        </div>
                    </div>

                    <div class="mt-auto pt-4 border-t border-outline-variant/5 flex items-center justify-between">
                        <div class="flex items-center gap-2 text-xs font-bold text-on-surface-variant">
                            <div class="w-6 h-6 rounded-lg bg-surface-container-high flex items-center justify-center text-[10px]">👨‍🌾</div>
                            ${product.producer_name}
                        </div>
                        <span class="text-[10px] font-bold text-primary/0 group-hover:text-primary uppercase tracking-widest transition-colors flex items-center gap-1">
                            View
                            <span class="material-symbols-outlined text-xs">arrow_forward</span>
                        </span>
                    </div>
                </div>
            </div>
        `;
    }

    function filterProducts(term) {
        if (!term) {
            const activePill = categoryPillsContainer.querySelector('.bg-primary');
            const isAll = activePill && activePill.getAttribute('data-id') === 'all';
            toggleRecommendationSections(isAll);
            renderMarketplace(allCategories, allProducts);
            return;
        }

        // Hide recommendations during search to focus on results
        toggleRecommendationSections(false);

        const filtered = allProducts.filter(p => 
            p.name.toLowerCase().includes(term) || 
            p.producer_name.toLowerCase().includes(term) ||
            (p.category_name && p.category_name.toLowerCase().includes(term))
        );

        marketplaceContent.innerHTML = `
            <section class="space-y-8">
                <div class="flex flex-col md:flex-row justify-between items-end gap-4 border-b border-outline-variant/10 pb-6">
                    <div class="max-w-xl">
                        <h2 class="font-headline text-3xl font-extrabold text-on-background">Search Results</h2>
                        <p class="text-on-surface-variant text-sm font-medium mt-1">Found ${filtered.length} items matching your criteria.</p>
                    </div>
                    <button onclick="document.querySelector('[data-id=\'all\']')?.click()" class="text-primary font-bold flex items-center gap-2 group text-sm hover:gap-3 transition-all">
                        Back to Marketplace
                        <span class="material-symbols-outlined transition-transform rotate-180 group-hover:-translate-x-1 text-base">arrow_forward</span>
                    </button>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
                    ${filtered.length > 0 
                        ? filtered.map(p => renderProductCard(p)).join('') 
                        : `
                        <div class="col-span-full py-20 text-center bg-surface-container-low rounded-3xl border border-dashed border-outline-variant">
                            <span class="material-symbols-outlined text-5xl text-outline mb-4">search_off</span>
                            <p class="text-on-surface-variant font-medium">No matching items found. Try a different term or browse categories.</p>
                        </div>
                        `
                    }
                </div>
            </section>
        `;
    }

    init();
});

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

    function renderCategories(categories) {
        const pillClass = "pill flex-shrink-0 px-6 py-2.5 rounded-full font-bold text-sm transition-all cursor-pointer whitespace-nowrap flex items-center gap-2 border border-outline-variant/10";
        const activeClass = "bg-primary text-on-primary shadow-lg shadow-primary/20 scale-105";
        const inactiveClass = "bg-surface-container-high text-on-surface-variant hover:bg-emerald-50 hover:text-primary hover:border-primary/20";

        categoryPillsContainer.innerHTML = `
            <div class="${pillClass} ${activeClass}" data-id="all">
                <span class="material-symbols-outlined text-sm">grid_view</span>
                All Items
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
                if (categoryId === 'all') {
                    renderMarketplace(allCategories, allProducts);
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
                    ${product.image_url ? `<img src="${product.image_url}" class="w-full h-full object-cover relative z-10 group-hover:scale-105 transition-transform duration-500" alt="${product.name}">` : ''}

                    <div class="absolute top-4 left-4 z-20">
                        <span class="px-3 py-1 bg-white/80 backdrop-blur-md text-primary text-[10px] font-bold rounded-full uppercase tracking-widest border border-white/20">
                            ${product.category_name || 'Stock'}
                        </span>
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
                        <h3 class="font-headline font-bold text-on-background leading-tight text-lg group-hover:text-primary transition-colors">${product.name}</h3>
                        <div class="text-right flex-shrink-0 ml-4">
                            <span class="text-lg font-extrabold text-primary">$${product.price}</span>
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
            renderMarketplace(allCategories, allProducts);
            return;
        }

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

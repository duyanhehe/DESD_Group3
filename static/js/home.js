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

            // Ensure we have arrays
            if (!Array.isArray(categories) || !Array.isArray(products)) {
                console.error('Data format error:', categories, products);
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
            marketplaceContent.innerHTML = `<div class="error" style="padding: 40px; text-align: center;"><h3>Oops! Something went wrong</h3><p>${error.message}</p></div>`;
        }
    }

    function renderCategories(categories) {
        categoryPillsContainer.innerHTML = `
            <div class="pill active" data-id="all">All Items</div>
            ${categories.map(cat => `
                <div class="pill" data-id="${cat.id}">
                    <span>${categoryIcons[cat.name] || '🛒'}</span>
                    ${cat.name}
                </div>
            `).join('')}
        `;

        // Handle Click
        categoryPillsContainer.querySelectorAll('.pill').forEach(pill => {
            pill.addEventListener('click', () => {
                categoryPillsContainer.querySelector('.pill.active').classList.remove('active');
                pill.classList.add('active');
                
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
                <div class="no-results">
                    <p>No products found matching your criteria.</p>
                </div>
            `;
            return;
        }

        // Group products by category
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
                <section class="category-section" id="cat-${cat.id}">
                    <div class="section-header">
                        <h2>${cat.name}</h2>
                        <a href="#" class="show-all">Show all</a>
                    </div>
                    <div class="product-carousel">
                        ${catProducts.map(p => renderProductCard(p)).join('')}
                    </div>
                </section>
            `;
        }).join('');
    }

    function renderProductCard(product) {
        const icon = categoryIcons[product.category_name] || '🛒';
        return `
            <div class="product-card" data-name="${product.name.toLowerCase()}">
                <div class="card-add-btn">+</div>
                <div class="card-image-box">${icon}</div>
                <div class="card-info">
                    <div class="card-price">
                        $${product.price}
                        <span class="unit">/ ${product.unit || 'item'}</span>
                    </div>
                    <div class="card-title">${product.name}</div>
                    <div class="card-producer">${product.producer_name}</div>
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

        // For search results, we just show one "Results" section
        marketplaceContent.innerHTML = `
            <section class="category-section">
                <div class="section-header">
                    <h2>Search Results for "${term}"</h2>
                </div>
                <div class="product-carousel" style="flex-wrap: wrap; overflow: visible;">
                    ${filtered.length > 0 
                        ? filtered.map(p => renderProductCard(p)).join('') 
                        : '<p style="padding: 20px;">No matching items found.</p>'
                    }
                </div>
            </section>
        `;
    }

    init();
});

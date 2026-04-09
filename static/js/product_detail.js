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

    async function fetchProductDetail() {
        try {
            const response = await fetch(`/products/api/v1/${PRODUCT_ID}/`);
            if (!response.ok) throw new Error('Product not found');
            const product = await response.json();
            renderProductDetail(product);
        } catch (error) {
            console.error('Error:', error);
            detailContent.innerHTML = `<div class="error-msg"><h2>Oops! Product not found.</h2><p>The item you are looking for might have been removed or is currently unavailable.</p></div>`;
        }
    }

    function renderProductDetail(product) {
        const isSafe = product.allergen_names.some(name => 
            name.toLowerCase().includes('none') || name.toLowerCase().includes('not applicable')
        );

        const categoryIcons = {
            'Fruits': '🍎',
            'Vegetables': '🥕',
            'Dairy': '🥛',
            'Bakery': '🍞',
            'None': '🛒'
        };

        const prodIcon = categoryIcons[product.category_name] || '🛒';

        detailContent.innerHTML = `
            <div class="product-detail-layout">
                <!-- Left: Visuals -->
                <div class="detail-visual-box">
                    <div class="detail-image-card">
                        ${prodIcon}
                    </div>
                </div>

                <!-- Right: Information -->
                <div class="detail-info-box">
                    <span class="detail-producer">Produced by ${product.producer_name}</span>
                    <h1 class="product-name">${product.name}</h1>
                    
                    <div class="detail-price">
                        $${product.price} <span class="unit">/ ${product.unit || 'item'}</span>
                    </div>

                    <div class="detail-stock-status ${product.stock_quantity > 0 ? 'status-available' : 'status-out'}">
                        ${product.stock_quantity > 0 ? `${product.stock_quantity} in stock` : 'Out of Stock'}
                    </div>

                    <div class="detail-description">
                        <h3>Description</h3>
                        <p>${product.description}</p>
                    </div>

                    <!-- Allergen Warning Component -->
                    <div class="detail-warning-box ${isSafe ? 'safe' : ''}">
                        <div class="warning-title">
                            ${isSafe ? '🟢 Food Safety Information' : '⚠️ Allergen Warning'}
                        </div>
                        <p class="warning-text">
                            ${isSafe 
                                ? 'This product is marked as <strong>None/Not Applicable</strong> for common allergens.' 
                                : `This product <strong>contains</strong> the following allergens:`}
                        </p>
                        <div class="allergen-pills">
                            ${product.allergen_names.map(name => {
                                const icon = allergenIcons[name] || '⚠️';
                                return `<span class="allergen-badge ${isSafe ? 'safe' : ''}">${icon} ${name}</span>`;
                            }).join('')}
                        </div>
                        ${!isSafe ? '<p style="font-size: 11px; color: #C62828; margin-top: 12px; font-weight: 500;">Please exercise caution if you have severe food allergies.</p>' : ''}
                    </div>

                    <div style="margin-top: 40px;">
                        <button class="btn btn-primary btn-block" style="padding: 18px; font-size: 18px;">Add to Cart</button>
                    </div>
                </div>
            </div>
        `;
    }

    fetchProductDetail();
});

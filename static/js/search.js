document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('global-search');
    const suggestionsBox = document.getElementById('search-suggestions');
    const suggestionsList = suggestionsBox.querySelector('.suggestions-list');
    const viewAllLink = document.getElementById('view-all-results');
    
    let debounceTimer;

    if (!searchInput) return;

    searchInput.addEventListener('input', function(e) {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();

        if (query.length < 2) {
            suggestionsBox.classList.add('hidden');
            return;
        }

        debounceTimer = setTimeout(() => {
            fetchSearchResults(query);
        }, 300);
    });

    // Close dropdown when typing esc or clicking outside
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            suggestionsBox.classList.add('hidden');
        } else if (e.key === 'Enter' && document.activeElement === searchInput) {
            e.preventDefault();
            const query = searchInput.value.trim();
            if (query) {
                window.location.href = `/products/search/?q=${encodeURIComponent(query)}`;
            }
        }
    });

    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
            suggestionsBox.classList.add('hidden');
        }
    });

    // Update the "View all" link dynamically
    searchInput.addEventListener('keyup', function(e) {
        const query = e.target.value.trim();
        if (query) {
            viewAllLink.href = `/products/search/?q=${encodeURIComponent(query)}`;
            viewAllLink.textContent = `View all results for "${query}"`;
        }
    });

    async function fetchSearchResults(query) {
        try {
            const response = await fetch(`/products/api/v1/search/?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Search failed');
            
            const data = await response.json();
            renderSuggestions(data.results || []);
        } catch (error) {
            console.error(error);
        }
    }

    function renderSuggestions(results) {
        suggestionsList.innerHTML = '';
        
        if (results.length === 0) {
            suggestionsList.innerHTML = '<div class="suggestion-item no-results">No products found</div>';
        } else {
            // Show up to 5 results
            const topResults = results.slice(0, 5);
            topResults.forEach(product => {
                const item = document.createElement('a');
                item.href = `/products/${product.id}/`;
                item.className = 'suggestion-item';
                
                const producerName = product.producer_name || 'Unknown Producer';
                const categoryName = product.category_name || 'Uncategorized';
                
                item.innerHTML = `
                    <div class="suggestion-info">
                        <span class="suggestion-name">${product.name}</span>
                        <span class="suggestion-meta">${categoryName} • ${producerName}</span>
                    </div>
                    <div class="suggestion-price">$${product.price} / ${product.unit}</div>
                `;
                suggestionsList.appendChild(item);
            });
        }
        
        suggestionsBox.classList.remove('hidden');
    }
});

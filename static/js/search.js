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
            suggestionsList.innerHTML = '<div class="p-8 text-center text-[10px] font-bold text-outline-variant uppercase tracking-widest">No products found</div>';
        } else {
            const topResults = results.slice(0, 5);
            topResults.forEach(product => {
                const item = document.createElement('a');
                item.href = `/products/${product.id}/`;
                item.className = 'flex justify-between items-center p-4 hover:bg-surface-container-low transition-all border-b border-outline-variant/5 last:border-0 group';
                
                const producerName = product.producer_name || 'Direct Source';
                const categoryName = product.category_name || 'Fresh';
                
                item.innerHTML = `
                    <div class="flex flex-col gap-1">
                        <span class="text-sm font-bold text-on-surface group-hover:text-primary transition-colors">${product.name}</span>
                        <span class="text-[10px] font-bold text-outline uppercase tracking-widest">${categoryName} • ${producerName}</span>
                    </div>
                    <div class="text-right">
                        <p class="text-sm font-black text-on-surface">$${product.price}</p>
                        <p class="text-[9px] font-bold text-outline-variant uppercase tracking-tighter">/ ${product.unit}</p>
                    </div>
                `;
                suggestionsList.appendChild(item);
            });
        }
        
        suggestionsBox.classList.remove('hidden');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const editableCells = document.querySelectorAll('.editable-cell');

    editableCells.forEach(cell => {
        cell.addEventListener('click', function() {
            // Prevent multiple clicks creating multiple inputs
            if (this.querySelector('input')) return;

            const originalValue = this.textContent.trim();
            const field = this.getAttribute('data-field');
            const productId = this.getAttribute('data-id');

            // Create input
            const input = document.createElement('input');
            input.type = field === 'price' ? 'text' : 'number';
            if (field === 'stock_quantity') {
                input.min = '0';
                input.step = '1';
            }
            input.value = originalValue;
            input.className = 'form-input';
            input.style.width = '80px';
            input.style.padding = '2px 4px';
            input.style.fontSize = '14px';

            this.innerHTML = '';
            this.appendChild(input);
            input.focus();

            // Handle save on blur or Enter
            const saveHandler = async (e) => {
                if (e.type === 'keydown' && e.key !== 'Enter') return;
                
                // Prevent duplicate triggers
                input.removeEventListener('blur', saveHandler);
                input.removeEventListener('keydown', saveHandler);

                const newValue = input.value.trim();
                
                // If unchanged or empty, revert
                if (newValue === '' || newValue === originalValue) {
                    this.textContent = originalValue;
                    return;
                }

                // Show spinner
                this.innerHTML = '<span style="color: var(--text-secondary);">⌛</span>';

                try {
                    const payload = {};
                    payload[field] = newValue;

                    const res = await fetch(`/products/api/v1/${productId}/edit/`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify(payload)
                    });

                    const data = await res.json();
                    
                    if (!res.ok) {
                        alert(data.error || 'Failed to update field.');
                        this.textContent = originalValue;
                    } else {
                        // Success checkmark flash
                        this.innerHTML = '<span style="color: green;">✓</span>';
                        setTimeout(() => {
                            // The API may format decimals differently
                            this.textContent = data.data[field];
                            // Optionally reload page if stock changes from 0 to >0 to update status badges
                            if (field === 'stock_quantity' && (originalValue === '0' || newValue === '0')) {
                                window.location.reload();
                            }
                        }, 800);
                    }
                } catch (err) {
                    console.error(err);
                    alert('Error saving data.');
                    this.textContent = originalValue;
                }
            };

            input.addEventListener('blur', saveHandler);
            input.addEventListener('keydown', saveHandler);
        });
    });
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

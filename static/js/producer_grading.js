document.addEventListener('DOMContentLoaded', () => {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('image-upload');

    // Drag & Drop visual feedback
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, () => {
            uploadZone.firstElementChild.nextElementSibling.classList.add('border-primary', 'bg-primary/5');
            uploadZone.firstElementChild.nextElementSibling.classList.remove('border-primary/30');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, () => {
            uploadZone.firstElementChild.nextElementSibling.classList.remove('border-primary', 'bg-primary/5');
            uploadZone.firstElementChild.nextElementSibling.classList.add('border-primary/30');
        }, false);
    });

    // Handle Drop
    uploadZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            console.log('File dropped:', files[0].name);
            fileInput.files = files; // Ensure file is attached to form for submission
            handleFile(files[0]);
        }
    });

    // Handle Click Selection (Now handled by <label for="image-upload">)
    fileInput.addEventListener('change', function() {
        if (this.files && this.files.length > 0) {
            console.log('File selected via picker:', this.files[0].name);
            handleFile(this.files[0]);
        }
    });
});

function handleFile(file) {
    // Validate file type
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
        showError('Invalid file type. Please upload a JPG or PNG image.');
        return;
    }

    // Validate size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        showError('File is too large. Maximum size is 10MB.');
        return;
    }

    // Show preview and switch to loading state
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('image-original').src = e.target.result;
        
        // Hide upload, show loading
        document.getElementById('upload-zone').classList.add('hidden');
        document.getElementById('error-message').classList.add('hidden');
        document.getElementById('results-section').classList.add('hidden');
        document.getElementById('loading-state').classList.remove('hidden');

        uploadToAI(file);
    };
    reader.readAsDataURL(file);
}

async function uploadToAI(file) {
    const formData = new FormData();
    formData.append('image', file);

    try {
        const headers = {
            'X-CSRFToken': getCookie('csrftoken')
        };
        const token = localStorage.getItem('auth_token');
        if (token && token !== 'null') {
            headers['Authorization'] = `Token ${token}`;
        }

        const response = await fetch('/ai/grading/', {
            method: 'POST',
            headers: headers,
            body: formData
        });

        const data = await response.json();

        document.getElementById('loading-state').classList.add('hidden');

        if (response.ok && data.success) {
            renderResults(data);
        } else {
            showError(data.error || 'Failed to analyze the image.');
            document.getElementById('upload-zone').classList.remove('hidden');
        }
    } catch (error) {
        console.error('AI Grading Error:', error);
        document.getElementById('loading-state').classList.add('hidden');
        showError('A network error occurred while contacting the AI engine.');
        document.getElementById('upload-zone').classList.remove('hidden');
    }
}

function renderResults(data) {
    const resultsSection = document.getElementById('results-section');
    resultsSection.classList.remove('hidden');

    // 1. Grade Badge
    // Expecting format like "Grade A" or "Grade F (Rotten/Defective)"
    const gradeLetter = data.grade.includes('Grade') ? data.grade.split(' ')[1] : data.grade.charAt(0);
    document.getElementById('grade-letter').textContent = gradeLetter;
    document.getElementById('grade-title').textContent = data.grade;
    document.getElementById('grade-class').textContent = data.class_name ? data.class_name.replace('_', ' ') : 'Unknown Class';

    // Apply colors based on Grade
    const badge = document.getElementById('grade-badge');
    const letter = document.getElementById('grade-letter');
    
    // Reset colors
    badge.className = 'w-32 h-32 rounded-full flex items-center justify-center flex-shrink-0 border-8 shadow-inner';
    letter.className = 'text-4xl font-black block';

    if (gradeLetter === 'A') {
        badge.classList.add('border-emerald-100', 'bg-emerald-50');
        letter.classList.add('text-emerald-600');
    } else if (gradeLetter === 'B') {
        badge.classList.add('border-lime-100', 'bg-lime-50');
        letter.classList.add('text-lime-600');
    } else if (gradeLetter === 'C') {
        badge.classList.add('border-yellow-100', 'bg-yellow-50');
        letter.classList.add('text-yellow-600');
    } else if (gradeLetter === 'D') {
        badge.classList.add('border-orange-100', 'bg-orange-50');
        letter.classList.add('text-orange-600');
    } else if (gradeLetter === 'F') {
        badge.classList.add('border-red-100', 'bg-red-50');
        letter.classList.add('text-red-600');
    } else {
        badge.classList.add('border-surface-container-highest');
        letter.classList.add('text-on-surface-variant');
    }

    // 2. Metrics
    if (data.metrics) {
        // Backend key: cv_defect_estimation (not defect_pct)
        const defectPct = data.metrics.cv_defect_estimation || 0;
        document.getElementById('metric-defect-val').textContent = `${defectPct.toFixed(1)}%`;
        document.getElementById('metric-defect-bar').style.width = `${Math.min(defectPct, 100)}%`;
        // Color code defect bar (high defect is bad/red, low is good/green)
        const defectBar = document.getElementById('metric-defect-bar');
        defectBar.className = 'h-full transition-all duration-1000 ' + (defectPct > 20 ? 'bg-error' : (defectPct > 5 ? 'bg-amber-500' : 'bg-emerald-500'));

        const sizeScore = data.metrics.size_score || 0;
        document.getElementById('metric-size-val').textContent = sizeScore.toFixed(2);
        document.getElementById('metric-size-bar').style.width = `${Math.min(sizeScore, 100)}%`;

        // Backend key: shape_solidity (not shape_score)
        const shapeScore = data.metrics.shape_solidity || 0;
        document.getElementById('metric-shape-val').textContent = shapeScore.toFixed(2);
        document.getElementById('metric-shape-bar').style.width = `${Math.min(shapeScore, 100)}%`;

        const textureDensity = data.metrics.texture_density || 0;
        document.getElementById('metric-texture-val').textContent = textureDensity.toFixed(2);
        document.getElementById('metric-texture-bar').style.width = `${Math.min(textureDensity * 100, 100)}%`;

        // Backend key: ripeness_pct (number 0-100), convert to human-readable label
        const ripePct = data.metrics.ripeness_pct;
        let ripenessLabel;
        if (ripePct === undefined || ripePct === null) {
            ripenessLabel = 'N/A';
        } else if (ripePct === 0) {
            ripenessLabel = 'Unripe';
        } else if (ripePct < 30) {
            ripenessLabel = 'Unripe (' + ripePct.toFixed(1) + '%)';
        } else if (ripePct < 60) {
            ripenessLabel = 'Partially Ripe (' + ripePct.toFixed(1) + '%)';
        } else if (ripePct < 85) {
            ripenessLabel = 'Ripe (' + ripePct.toFixed(1) + '%)';
        } else {
            ripenessLabel = 'Fully Ripe (' + ripePct.toFixed(1) + '%)';
        }
        document.getElementById('metric-ripeness-val').textContent = ripenessLabel;
    }

    // 3. XAI Reasons
    if (data.xai && data.xai.reasons) {
        const list = document.getElementById('xai-reasons-list');
        list.innerHTML = '';
        data.xai.reasons.forEach(reason => {
            const li = document.createElement('li');
            li.className = 'flex items-start gap-3';
            li.innerHTML = `<span class="material-symbols-outlined text-secondary text-sm mt-0.5">check_circle</span> <span>${reason}</span>`;
            list.appendChild(li);
        });
    }

    // 4. Heatmap
    if (data.xai && data.xai.heatmap_url) {
        const heatmapImg = document.getElementById('image-heatmap');
        heatmapImg.src = data.xai.heatmap_url;
        document.getElementById('heatmap-container').classList.remove('opacity-0');
        document.getElementById('heatmap-container').classList.add('opacity-100');
    } else {
        document.getElementById('heatmap-container').classList.add('opacity-0');
        document.getElementById('heatmap-container').classList.remove('opacity-100');
    }
}

function showError(msg) {
    const errorEl = document.getElementById('error-message');
    document.getElementById('error-text').textContent = msg;
    errorEl.classList.remove('hidden');
}

function resetUpload() {
    document.getElementById('image-upload').value = '';
    document.getElementById('results-section').classList.add('hidden');
    document.getElementById('error-message').classList.add('hidden');
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('upload-zone').classList.remove('hidden');
}

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

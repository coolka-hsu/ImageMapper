document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    const imageInput = document.getElementById('image');
    const mapTextarea = document.getElementById('map_html');

    // File validation
    imageInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            // Check file size (10MB limit)
            const maxSize = 10 * 1024 * 1024; // 10MB in bytes
            if (file.size > maxSize) {
                alert('File size must be less than 10MB');
                this.value = '';
                return;
            }

            // Check file type
            const allowedTypes = ['image/png', 'image/jpg', 'image/jpeg', 'image/gif'];
            if (!allowedTypes.includes(file.type)) {
                alert('Please upload a PNG, JPG, JPEG, or GIF file');
                this.value = '';
                return;
            }

            // Display file info
            const fileInfo = document.createElement('div');
            fileInfo.className = 'alert alert-info mt-2';
            fileInfo.innerHTML = `
                <i class="fas fa-info-circle me-2"></i>
                <strong>Selected:</strong> ${file.name} (${formatFileSize(file.size)})
            `;
            
            // Remove any existing file info
            const existingInfo = this.parentNode.querySelector('.alert-info');
            if (existingInfo) {
                existingInfo.remove();
            }
            
            this.parentNode.appendChild(fileInfo);
        }
    });

    // Map textarea validation and formatting
    mapTextarea.addEventListener('blur', function() {
        const value = this.value.trim();
        if (value) {
            // Basic validation for area tags
            const areaRegex = /<area[^>]+>/gi;
            const matches = value.match(areaRegex);
            
            if (matches) {
                const count = matches.length;
                const info = document.createElement('div');
                info.className = 'alert alert-success mt-2';
                info.innerHTML = `
                    <i class="fas fa-check-circle me-2"></i>
                    Found ${count} area tag${count > 1 ? 's' : ''}
                `;
                
                // Remove any existing info
                const existingInfo = this.parentNode.querySelector('.alert-success, .alert-warning');
                if (existingInfo) {
                    existingInfo.remove();
                }
                
                this.parentNode.appendChild(info);
            } else {
                const warning = document.createElement('div');
                warning.className = 'alert alert-warning mt-2';
                warning.innerHTML = `
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    No valid area tags found. Please check your HTML.
                `;
                
                // Remove any existing info
                const existingInfo = this.parentNode.querySelector('.alert-success, .alert-warning');
                if (existingInfo) {
                    existingInfo.remove();
                }
                
                this.parentNode.appendChild(warning);
            }
        }
    });

    // Form submission handling
    uploadForm.addEventListener('submit', function(e) {
        // Validate form before submission
        const imageFile = imageInput.files[0];
        const mapContent = mapTextarea.value.trim();

        if (!imageFile) {
            e.preventDefault();
            alert('Please select an image file');
            return;
        }

        if (!mapContent) {
            e.preventDefault();
            alert('Please provide HTML map code');
            return;
        }

        // Show loading modal
        loadingModal.show();
        
        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
    });

    // Auto-format map HTML
    function formatMapHTML() {
        const textarea = mapTextarea;
        let content = textarea.value;
        
        // Basic formatting (optional)
        content = content.replace(/>\s*</g, '>\n<');
        content = content.trim();
        
        textarea.value = content;
    }

    // Add format button
    const formatBtn = document.createElement('button');
    formatBtn.type = 'button';
    formatBtn.className = 'btn btn-sm btn-outline-secondary mt-2';
    formatBtn.innerHTML = '<i class="fas fa-code me-1"></i>Format';
    formatBtn.addEventListener('click', formatMapHTML);
    
    mapTextarea.parentNode.appendChild(formatBtn);

    // Utility function to format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Example code insertion
    document.querySelector('[data-bs-target="#exampleCode"]').addEventListener('click', function() {
        const isExpanded = this.getAttribute('aria-expanded') === 'true';
        if (!isExpanded) {
            // Add button to insert example
            setTimeout(() => {
                const exampleDiv = document.getElementById('exampleCode');
                if (!exampleDiv.querySelector('.btn-success')) {
                    const insertBtn = document.createElement('button');
                    insertBtn.type = 'button';
                    insertBtn.className = 'btn btn-success btn-sm mt-2';
                    insertBtn.innerHTML = '<i class="fas fa-plus me-1"></i>Use This Example';
                    insertBtn.addEventListener('click', function() {
                        const exampleCode = `<map name="example">
  <area shape="rect" coords="0,0,300,150" href="https://example.com/link1" alt="Section 1">
  <area shape="rect" coords="0,150,300,300" href="https://example.com/link2" alt="Section 2">
  <area shape="rect" coords="0,300,300,450" href="https://example.com/link3" alt="Section 3">
</map>`;
                        mapTextarea.value = exampleCode;
                        mapTextarea.dispatchEvent(new Event('blur'));
                        bootstrap.Collapse.getInstance(exampleDiv).hide();
                    });
                    exampleDiv.querySelector('.card-body').appendChild(insertBtn);
                }
            }, 100);
        }
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-success)');
    alerts.forEach(alert => {
        if (!alert.querySelector('.btn-close')) return;
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

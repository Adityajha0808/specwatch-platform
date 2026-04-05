/* Frontend JavaScript for SpecWatch Dashboard */

// Pipeline control
let pipelineModal;
let pipelineCheckInterval;


// Initialize pipeline modal
document.addEventListener('DOMContentLoaded', function() {

    const modalElement = document.getElementById('pipelineModal');
    if (modalElement) {
        pipelineModal = new bootstrap.Modal(modalElement, {
            backdrop: 'static',
            keyboard: false
        });
    }
    
    // Populate vendor dropdown
    populateVendorDropdown();
});


/**
 * Populate vendor dropdown for pipeline selection
 */
function populateVendorDropdown() {
    const dropdown = document.getElementById('pipelineVendorSelect');
    if (!dropdown) return;
    
    fetch('/vendors/api/list')
        .then(response => response.json())
        .then(vendors => {
            // Keep "All Vendors" option
            // Add vendor options
            vendors.forEach(vendor => {
                const option = document.createElement('option');
                option.value = vendor.name;
                option.textContent = vendor.display_name || vendor.name;
                dropdown.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading vendors:', error);
        });
}


/**
 * Run a pipeline from the UI
 * @param {string} type - Pipeline type: 'discovery', 'analysis', 'alerting', or 'full'
 */
function runPipeline(type) {
    // Get selected vendor
    const vendorSelect = document.getElementById('pipelineVendorSelect');
    const selectedVendor = vendorSelect ? vendorSelect.value : '';
    
    // Build display message
    const vendorText = selectedVendor ? ` for ${selectedVendor}` : ' for all vendors';
    
    // Show modal
    if (pipelineModal) {
        pipelineModal.show();
    }
    
    // Reset progress
    updatePipelineProgress(0, 'Starting', `Initiating ${type} pipeline ${vendorText}...`);
    
    // Build request body
    const requestBody = {};
    if (selectedVendor) {
        requestBody.vendor = selectedVendor;
    }
    
    // Trigger pipeline
    fetch(`/api/pipelines/${type}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Start polling for status
            startPipelineStatusPolling();
        } else {
            alert('Error starting pipeline: ' + (data.error || 'Unknown error'));
            if (pipelineModal) {
                pipelineModal.hide();
            }
        }
    })
    .catch(error => {
        alert('Error starting pipeline: ' + error);
        if (pipelineModal) {
            pipelineModal.hide();
        }
    });
}


/**
 * Start polling pipeline status
 */
function startPipelineStatusPolling() {
    // Clear any existing interval
    if (pipelineCheckInterval) {
        clearInterval(pipelineCheckInterval);
    }
    
    // Poll every 500ms
    pipelineCheckInterval = setInterval(checkPipelineStatus, 500);
}


/**
 * Check pipeline status
 */
function checkPipelineStatus() {
    fetch('/api/pipelines/status')
        .then(response => response.json())
        .then(data => {
            // Update progress UI
            updatePipelineProgress(
                data.progress,
                data.current_stage || 'Running',
                data.message || ''
            );
            
            // Check if complete
            if (!data.running) {
                clearInterval(pipelineCheckInterval);
                
                // Show result
                if (data.result === 'success') {
                    updatePipelineProgress(100, 'Complete', '✅ Pipeline completed successfully!');
                    
                    // Auto-close after 2 seconds and reload page
                    setTimeout(() => {
                        if (pipelineModal) {
                            pipelineModal.hide();
                        }
                        location.reload();
                    }, 2000);
                } else if (data.result === 'error') {
                    updatePipelineProgress(data.progress, 'Error', '❌ ' + data.message);
                    
                    // Don't auto-close on error
                    setTimeout(() => {
                        if (pipelineModal) {
                            pipelineModal.hide();
                        }
                    }, 5000);
                }
            }
        })
        .catch(error => {
            console.error('Error checking pipeline status:', error);
            clearInterval(pipelineCheckInterval);
        });
}


/**
 * Update pipeline progress UI
 * @param {number} progress - Progress percentage (0-100)
 * @param {string} stage - Current stage name
 * @param {string} message - Status message
 */
function updatePipelineProgress(progress, stage, message) {
    const progressBar = document.getElementById('pipelineProgress');
    const stageElement = document.getElementById('pipelineStage');
    const messageElement = document.getElementById('pipelineMessage');
    
    if (progressBar) {
        progressBar.style.width = progress + '%';
        progressBar.textContent = progress + '%';
        progressBar.setAttribute('aria-valuenow', progress);
    }
    
    if (stageElement) {
        stageElement.textContent = stage;
    }
    
    if (messageElement) {
        messageElement.textContent = message;
    }
}


/**
 * Format timestamp for display
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted timestamp
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;
    
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}


/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Show toast or alert
        alert('Copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}


/**
 * Confirm action with dialog
 * @param {string} message - Confirmation message
 * @param {function} callback - Callback if confirmed
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}


// Export for use in templates
window.runPipeline = runPipeline;
window.formatTimestamp = formatTimestamp;
window.copyToClipboard = copyToClipboard;
window.confirmAction = confirmAction;

// Competition Mode JavaScript Utilities

class CompetitionManager {
    constructor() {
        this.currentCompetition = null;
        this.currentAthlete = null;
        this.currentSeries = null;
        this.cameraStream = null;
    }

    // Initialize competition manager
    init(competitionData) {
        this.currentCompetition = competitionData;
        this.setupEventListeners();
    }

    // Setup global event listeners
    setupEventListeners() {
        // Auto-refresh competition status
        if (this.currentCompetition && this.currentCompetition.status === 'active') {
            setInterval(() => this.checkCompetitionStatus(), 30000); // Check every 30 seconds
        }
    }

    // Check if competition can be finished
    async checkCompetitionStatus() {
        if (!this.currentCompetition) return;
        
        try {
            const response = await fetch(`/competition/${this.currentCompetition.id}/results`);
            const data = await response.json();
            
            const finishBtn = document.getElementById('finishBtn');
            if (finishBtn) {
                finishBtn.disabled = !data.competition.can_finish;
            }
        } catch (error) {
            console.error('Error checking competition status:', error);
        }
    }

    // Format date/time for display
    formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleString();
    }

    // Format time for display
    formatTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // Calculate statistics for an athlete
    calculateAthleteStats(athleteData) {
        const finishedSeries = athleteData.series.filter(s => 
            s.status === 'finished' || s.status === 'finished_early'
        );
        
        const totalShots = athleteData.series.reduce((sum, s) => sum + s.shots_count, 0);
        const totalScore = athleteData.total_score;
        const avgScore = totalShots > 0 ? (totalScore / totalShots).toFixed(1) : 0;
        const bestSeries = Math.max(...athleteData.series.map(s => s.total_score));
        
        return {
            finishedSeries: finishedSeries.length,
            totalSeries: athleteData.series_count,
            totalShots,
            totalScore,
            avgScore,
            bestSeries,
            progress: (finishedSeries.length / athleteData.series_count) * 100
        };
    }

    // Generate series status badge HTML
    getSeriesBadge(series) {
        const statusClass = series.status === 'finished' ? 'success' : 
                           series.status === 'finished_early' ? 'warning' : 'secondary';
        const statusIcon = series.status === 'finished' ? 'check' : 
                          series.status === 'finished_early' ? 'stop' : 'clock';
        
        return `<span class="badge bg-${statusClass}">
            <i class="bi bi-${statusIcon}"></i> ${series.status}
        </span>`;
    }

    // Show loading state
    showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
        }
    }

    // Show error message
    showError(message) {
        // Create toast notification
        const toastHtml = `
            <div class="toast align-items-center text-white bg-danger border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        const toastContainer = this.getOrCreateToastContainer();
        const toastElement = document.createElement('div');
        toastElement.innerHTML = toastHtml;
        toastContainer.appendChild(toastElement.firstElementChild);
        
        const toast = new bootstrap.Toast(toastContainer.lastElementChild);
        toast.show();
    }

    // Show success message
    showSuccess(message) {
        const toastHtml = `
            <div class="toast align-items-center text-white bg-success border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        const toastContainer = this.getOrCreateToastContainer();
        const toastElement = document.createElement('div');
        toastElement.innerHTML = toastHtml;
        toastContainer.appendChild(toastElement.firstElementChild);
        
        const toast = new bootstrap.Toast(toastContainer.lastElementChild);
        toast.show();
    }

    // Get or create toast container
    getOrCreateToastContainer() {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(container);
        }
        return container;
    }

    // Confirm action with dialog
    confirmAction(message, callback) {
        if (confirm(message)) {
            callback();
        }
    }

    // Handle API errors
    handleApiError(error, customMessage = 'Operation failed') {
        console.error('API Error:', error);
        this.showError(customMessage + ': ' + (error.message || 'Unknown error'));
    }

    // Debounce function for search/filter inputs
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Validate image file
    validateImageFile(file) {
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp'];
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        if (!allowedTypes.includes(file.type)) {
            throw new Error('Invalid file type. Please upload an image file.');
        }
        
        if (file.size > maxSize) {
            throw new Error('File too large. Maximum size is 10MB.');
        }
        
        return true;
    }

    // Create image preview
    createImagePreview(file, callback) {
        const reader = new FileReader();
        reader.onload = function(e) {
            callback(e.target.result);
        };
        reader.readAsDataURL(file);
    }

    // Download data as JSON
    downloadJson(data, filename) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Print competition results
    printResults(competitionId) {
        window.open(`/competition/${competitionId}/results?print=true`, '_blank');
    }
}

// Camera management
class CameraManager {
    constructor() {
        this.stream = null;
        this.video = null;
        this.canvas = null;
    }

    async startCamera(videoElement, canvasElement) {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                } 
            });
            
            this.video = videoElement;
            this.canvas = canvasElement;
            
            this.video.srcObject = this.stream;
            this.video.style.display = 'block';
            
            return true;
        } catch (error) {
            console.error('Error accessing camera:', error);
            throw new Error('Unable to access camera. Please check permissions.');
        }
    }

    capturePhoto() {
        if (!this.video || !this.canvas) {
            throw new Error('Camera not initialized');
        }
        
        const context = this.canvas.getContext('2d');
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        return this.canvas.toDataURL('image/jpeg', 0.9);
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.video) {
            this.video.style.display = 'none';
        }
    }

    // Check if camera is available
    isCameraAvailable() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }
}

// Image upload manager
class ImageUploadManager {
    constructor() {
        this.maxFileSize = 10 * 1024 * 1024; // 10MB
        this.allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp'];
    }

    validateFile(file) {
        if (!this.allowedTypes.includes(file.type)) {
            throw new Error('Invalid file type. Please upload JPEG, PNG, GIF, or BMP images.');
        }
        
        if (file.size > this.maxFileSize) {
            throw new Error('File too large. Maximum size is 10MB.');
        }
        
        return true;
    }

    async uploadFile(file, uploadUrl, onProgress = null) {
        this.validateFile(file);
        
        const formData = new FormData();
        formData.append('image', file);
        
        try {
            const response = await fetch(uploadUrl, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Upload error:', error);
            throw new Error('Failed to upload image. Please try again.');
        }
    }

    async uploadBase64(imageData, uploadUrl) {
        try {
            const response = await fetch(uploadUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image: imageData })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Upload error:', error);
            throw new Error('Failed to upload image. Please try again.');
        }
    }
}

// Initialize global instances
const competitionManager = new CompetitionManager();
const cameraManager = new CameraManager();
const imageUploadManager = new ImageUploadManager();

// Export for use in templates
window.competitionManager = competitionManager;
window.cameraManager = cameraManager;
window.imageUploadManager = imageUploadManager;

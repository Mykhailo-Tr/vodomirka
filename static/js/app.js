let currentFile = null;
let currentImageType = 'file'; // 'file' or 'camera'
let currentStream = null;
let camerasLoaded = false;

const preview = document.getElementById("preview");
const processBtn = document.getElementById("processBtn");
const cameraSelect = document.getElementById("cameraSelect");
const cameraVideo = document.getElementById("cameraVideo");
const cameraCanvas = document.getElementById("cameraCanvas");
const cameraPreview = document.getElementById("cameraPreview");
const cameraControls = document.getElementById("cameraControls");
const captureBtn = document.getElementById("captureBtn");
const stopCameraBtn = document.getElementById("stopCameraBtn");
const useCameraBtn = document.getElementById("useCameraBtn");
const useFileBtn = document.getElementById("useFileBtn");
const fileInput = document.getElementById("fileInput");

const baseImg = document.getElementById("baseImg");
const idealImg = document.getElementById("idealImg");
const scoredImg = document.getElementById("scoredImg");

const shots = document.getElementById("shots");
const total = document.getElementById("total");
const jsonOut = document.getElementById("jsonOut");
const copyBtn = document.getElementById("copyBtn");

const modalImg = document.getElementById("modalImg");
const imgModal = document.getElementById("imgModal");

// Request camera permission and load cameras
async function initCameraSystem() {
    try {
        // Сначала запрашиваем доступ к медиаустройствам (как в Google Meet)
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment', // По умолчанию задняя камера
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        });
        
        // Останавливаем поток после получения разрешения
        stream.getTracks().forEach(track => track.stop());
        
        // Теперь можем получить список камер
        await loadCameraList();
        camerasLoaded = true;
        
        // Показываем выбор камеры
        cameraSelect.disabled = false;
        cameraSelect.innerHTML = '<option value="">-- Виберіть камеру --</option>' + cameraSelect.innerHTML;
        
    } catch (err) {
        console.error('Error getting camera permission:', err);
        cameraSelect.innerHTML = '<option value="">-- Доступ до камери відхилено --</option>';
        cameraSelect.disabled = true;
        alert('Для використання камери дозвольте доступ до неї у браузері.');
    }
}

// Load available cameras
async function loadCameraList() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(device => device.kind === 'videoinput');
        
        cameraSelect.innerHTML = '';
        videoDevices.forEach((device, index) => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.text = device.label || `Камера ${index + 1}`;
            cameraSelect.appendChild(option);
        });
    } catch (err) {
        console.error('Error getting camera list:', err);
    }
}

// Start camera stream with selected device
async function startCamera(deviceId) {
    stopCamera(); // Stop any existing stream
    
    const constraints = {
        video: {
            deviceId: deviceId ? { exact: deviceId } : undefined,
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: deviceId ? undefined : 'environment'
        }
    };
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        currentStream = stream;
        cameraVideo.srcObject = stream;
        cameraPreview.classList.remove('d-none');
        cameraControls.classList.remove('d-none');
        
        // Mirror for front camera
        const track = stream.getVideoTracks()[0];
        const settings = track.getSettings();
        if (settings.facingMode === 'user') {
            cameraVideo.style.transform = 'scaleX(-1)';
        } else {
            cameraVideo.style.transform = 'scaleX(1)';
        }
        
        // Wait for video to be ready
        await new Promise(resolve => {
            cameraVideo.onloadedmetadata = () => {
                cameraVideo.play();
                resolve();
            };
        });
        
        // Enable capture button
        captureBtn.disabled = false;
        
    } catch (err) {
        console.error('Error accessing camera:', err);
        alert('Помилка доступу до камери: ' + err.message);
        stopCamera();
    }
}

// Stop camera stream
function stopCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
        cameraVideo.srcObject = null;
        cameraPreview.classList.add('d-none');
        cameraControls.classList.add('d-none');
        captureBtn.disabled = true;
    }
}

// Capture photo from camera
async function capturePhoto() {
    if (!currentStream) return;
    
    cameraCanvas.width = cameraVideo.videoWidth;
    cameraCanvas.height = cameraVideo.videoHeight;
    
    const ctx = cameraCanvas.getContext('2d');
    
    // Mirror if needed
    if (cameraVideo.style.transform === 'scaleX(-1)') {
        ctx.translate(cameraCanvas.width, 0);
        ctx.scale(-1, 1);
    }
    
    ctx.drawImage(cameraVideo, 0, 0, cameraCanvas.width, cameraCanvas.height);
    
    // Reset transform
    if (cameraVideo.style.transform === 'scaleX(-1)') {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
    }
    
    // Convert to data URL
    const imageData = cameraCanvas.toDataURL('image/jpeg', 0.9);
    
    // Show loading
    captureBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Зберігається...';
    captureBtn.disabled = true;
    
    try {
        // Send to server
        const res = await fetch("/snapshot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: imageData })
        });
        
        const data = await res.json();
        if (res.ok) {
            currentFile = data.filename;
            currentImageType = 'camera';
            
            // Show preview
            preview.src = data.image_url;
            preview.classList.remove('d-none');
            cameraPreview.classList.add('d-none');
            
            // Enable process button
            processBtn.disabled = false;
            
            // Set base image
            baseImg.src = data.image_url;
            
            // Stop camera after capture
            stopCamera();
            cameraSelect.value = '';
            
            // Show success message
            showToast('Знімок успішно збережено!', 'success');
        } else {
            alert('Помилка збереження знімка: ' + data.error);
        }
    } catch (error) {
        console.error('Error saving snapshot:', error);
        alert('Помилка збереження знімка: ' + error.message);
    } finally {
        // Restore capture button
        captureBtn.innerHTML = '<i class="bi bi-camera"></i> Зробити знімок';
        captureBtn.disabled = false;
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.custom-toast');
    existingToasts.forEach(toast => toast.remove());
    
    // Create toast
    const toast = document.createElement('div');
    toast.className = `custom-toast alert alert-${type} alert-dismissible fade show`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1050;
        min-width: 250px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Initialize camera system when page loads
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        initCameraSystem();
    } else {
        cameraSelect.innerHTML = '<option value="">-- Камера не підтримується --</option>';
        cameraSelect.disabled = true;
        alert('Ваш браузер не підтримує доступ до камери.');
    }
});

cameraSelect.addEventListener('change', (e) => {
    if (e.target.value) {
        startCamera(e.target.value);
    } else {
        stopCamera();
    }
});

captureBtn.addEventListener('click', capturePhoto);

stopCameraBtn.addEventListener('click', () => {
    stopCamera();
    cameraSelect.value = '';
});

useCameraBtn.addEventListener('click', () => {
    if (camerasLoaded && cameraSelect.options.length > 0) {
        if (cameraSelect.value) {
            cameraPreview.classList.remove('d-none');
            preview.classList.add('d-none');
        } else {
            alert('Будь ласка, спочатку виберіть камеру зі списку');
        }
    } else {
        alert('Спочатку дозвольте доступ до камери та оновіть сторінку');
    }
});

useFileBtn.addEventListener('click', () => {
    cameraPreview.classList.add('d-none');
    preview.classList.remove('d-none');
    stopCamera();
});

// Original file upload functionality
fileInput.addEventListener("change", async e => {
    const file = e.target.files[0];
    if (!file) return;

    // Show loading
    const originalText = processBtn.innerHTML;
    processBtn.disabled = true;
    processBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Завантаження...';

    try {
        const form = new FormData();
        form.append("image", file);

        const res = await fetch("/upload", {
            method: "POST",
            body: form
        });

        const data = await res.json();
        if (res.ok) {
            currentFile = data.filename;
            currentImageType = 'file';

            preview.src = data.image_url;
            preview.classList.remove("d-none");
            cameraPreview.classList.add("d-none");

            baseImg.src = data.image_url;
            processBtn.disabled = false;
            
            showToast('Файл успішно завантажено!', 'success');
        } else {
            alert('Помилка завантаження файлу: ' + data.error);
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('Помилка завантаження файлу: ' + error.message);
    } finally {
        processBtn.innerHTML = originalText;
        processBtn.disabled = false;
    }
});

// Process button
processBtn.onclick = async () => {
    if (!currentFile) return;

    // Save original button state
    const originalText = processBtn.innerHTML;
    const originalDisabled = processBtn.disabled;

    // Show spinner and update text
    processBtn.disabled = true;
    processBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Обробляється';

    try {
        const res = await fetch("/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename: currentFile })
        });

        const data = await res.json();
        if (res.ok) {
            shots.innerText = data.stats.shots;
            total.innerText = data.stats.total_score;

            baseImg.src = data.images.overlay;
            idealImg.src = data.images.ideal;
            scoredImg.src = data.images.scored;

            jsonOut.textContent = JSON.stringify(data.json, null, 2);
            
            showToast('Обробка завершена успішно!', 'success');
        } else {
            alert('Помилка обробки: ' + data.error);
        }
    } catch (error) {
        console.error("Processing error:", error);
        alert('Помилка обробки: ' + error.message);
    } finally {
        // Restore button state
        processBtn.innerHTML = originalText;
        processBtn.disabled = originalDisabled;
    }
};

// Copy JSON
copyBtn.onclick = () => {
    navigator.clipboard.writeText(jsonOut.textContent).then(() => {
        showToast('JSON скопійовано в буфер обміну', 'info');
        copyBtn.innerHTML = '<i class="bi bi-check"></i> Copied';
        setTimeout(() => {
            copyBtn.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
        }, 2000);
    }).catch(err => {
        console.error('Copy failed:', err);
        alert('Не вдалося скопіювати текст');
    });
};

// Modal viewer
document.addEventListener("click", e => {
    if (e.target.tagName !== "IMG" || !e.target.src || e.target.id === 'preview') return;
    modalImg.src = e.target.src;
    imgModal.classList.remove("d-none");
});

imgModal.onclick = () => {
    imgModal.classList.add("d-none");
};

// Stop camera when leaving page
window.addEventListener('beforeunload', stopCamera);
window.addEventListener('pagehide', stopCamera);

// Handle camera permissions change
navigator.mediaDevices.addEventListener('devicechange', async () => {
    if (camerasLoaded) {
        await loadCameraList();
    }
});

// Request fullscreen for better camera experience
function requestFullscreen() {
    const elem = document.documentElement;
    if (elem.requestFullscreen) {
        elem.requestFullscreen();
    } else if (elem.webkitRequestFullscreen) { /* Safari */
        elem.webkitRequestFullscreen();
    } else if (elem.msRequestFullscreen) { /* IE11 */
        elem.msRequestFullscreen();
    }
}
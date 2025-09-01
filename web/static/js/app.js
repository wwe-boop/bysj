// LEO卫星网络仿真系统 - 主应用脚本

// 全局变量
let socket;
let isConnected = false;

// 初始化应用
document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
    updateConnectionStatus();
    initializeTooltips();
    
    // 每30秒检查连接状态
    setInterval(updateConnectionStatus, 30000);
});

// 初始化WebSocket连接
function initializeWebSocket() {
    try {
        socket = io();
        
        socket.on('connect', function() {
            console.log('WebSocket连接成功');
            isConnected = true;
            updateConnectionIndicator(true);
            showNotification('已连接到服务器', 'success');
            
            // 订阅仿真更新
            socket.emit('subscribe_simulation', {});
        });
        
        socket.on('disconnect', function() {
            console.log('WebSocket连接断开');
            isConnected = false;
            updateConnectionIndicator(false);
            showNotification('与服务器连接断开', 'warning');
        });
        
        socket.on('connect_error', function(error) {
            console.error('WebSocket连接错误:', error);
            isConnected = false;
            updateConnectionIndicator(false);
            showNotification('连接服务器失败', 'error');
        });
        
        socket.on('connection_established', function(data) {
            console.log('连接确认:', data);
        });
        
        socket.on('subscription_confirmed', function(data) {
            console.log('订阅确认:', data);
        });
        
    } catch (error) {
        console.error('初始化WebSocket失败:', error);
        isConnected = false;
        updateConnectionIndicator(false);
    }
}

// 更新连接状态指示器
function updateConnectionIndicator(connected) {
    const statusIcon = document.getElementById('connection-status');
    const statusText = document.getElementById('connection-text');
    
    if (statusIcon && statusText) {
        if (connected) {
            statusIcon.className = 'fas fa-circle text-success';
            statusText.textContent = '已连接';
        } else {
            statusIcon.className = 'fas fa-circle text-danger';
            statusText.textContent = '未连接';
        }
    }
}

// 更新连接状态
function updateConnectionStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'running') {
                if (!isConnected) {
                    // 尝试重新连接WebSocket
                    initializeWebSocket();
                }
            }
        })
        .catch(error => {
            console.error('检查服务器状态失败:', error);
            updateConnectionIndicator(false);
        });
}

// 初始化工具提示
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// 显示通知
function showNotification(message, type = 'info', duration = 3000) {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `alert alert-${getBootstrapAlertClass(type)} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="${getNotificationIcon(type)} me-2"></i>
            <span>${message}</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // 自动移除通知
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

// 获取Bootstrap警告类
function getBootstrapAlertClass(type) {
    const classMap = {
        'success': 'success',
        'error': 'danger',
        'warning': 'warning',
        'info': 'info'
    };
    return classMap[type] || 'info';
}

// 获取通知图标
function getNotificationIcon(type) {
    const iconMap = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-circle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle'
    };
    return iconMap[type] || 'fas fa-info-circle';
}

// 格式化数字
function formatNumber(num, decimals = 1) {
    if (num === null || num === undefined) return '0';
    
    if (num >= 1000000) {
        return (num / 1000000).toFixed(decimals) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(decimals) + 'K';
    } else {
        return num.toFixed(decimals);
    }
}

// 格式化时间
function formatTime(seconds) {
    if (seconds < 60) {
        return Math.round(seconds) + 's';
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.round(seconds % 60);
        return `${minutes}m ${remainingSeconds}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}

// 格式化字节
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// 获取状态颜色
function getStatusColor(value, thresholds) {
    if (value >= thresholds.excellent) return 'success';
    if (value >= thresholds.good) return 'info';
    if (value >= thresholds.warning) return 'warning';
    return 'danger';
}

// 创建进度条
function createProgressBar(value, max = 100, className = '') {
    const percentage = Math.min(100, (value / max) * 100);
    const color = getStatusColor(percentage, {
        excellent: 80,
        good: 60,
        warning: 40
    });
    
    return `
        <div class="progress ${className}">
            <div class="progress-bar bg-${color}" role="progressbar" 
                 style="width: ${percentage}%" 
                 aria-valuenow="${percentage}" 
                 aria-valuemin="0" 
                 aria-valuemax="100">
                ${percentage.toFixed(1)}%
            </div>
        </div>
    `;
}

// 创建状态徽章
function createStatusBadge(status, text) {
    const colorMap = {
        'running': 'success',
        'stopped': 'secondary',
        'error': 'danger',
        'warning': 'warning',
        'info': 'info'
    };
    
    const color = colorMap[status] || 'secondary';
    return `<span class="badge bg-${color}">${text}</span>`;
}

// 防抖函数
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 深拷贝对象
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime());
    if (obj instanceof Array) return obj.map(item => deepClone(item));
    if (typeof obj === 'object') {
        const clonedObj = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                clonedObj[key] = deepClone(obj[key]);
            }
        }
        return clonedObj;
    }
}

// 生成随机ID
function generateId(length = 8) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

// 验证表单
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
        }
    });
    
    return isValid;
}

// 清除表单验证状态
function clearFormValidation(formElement) {
    const inputs = formElement.querySelectorAll('.is-valid, .is-invalid');
    inputs.forEach(input => {
        input.classList.remove('is-valid', 'is-invalid');
    });
}

// 加载状态管理
function setLoadingState(element, loading = true) {
    if (loading) {
        element.disabled = true;
        element.dataset.originalText = element.innerHTML;
        element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 加载中...';
    } else {
        element.disabled = false;
        element.innerHTML = element.dataset.originalText || element.innerHTML;
    }
}

// 错误处理
function handleError(error, context = '') {
    console.error(`错误 ${context}:`, error);
    
    let message = '发生未知错误';
    if (error.message) {
        message = error.message;
    } else if (typeof error === 'string') {
        message = error;
    }
    
    showNotification(`${context ? context + ': ' : ''}${message}`, 'error');
}

// 成功处理
function handleSuccess(message, data = null) {
    console.log('成功:', message, data);
    showNotification(message, 'success');
}

// 导出全局函数
window.LEOSimulation = {
    showNotification,
    formatNumber,
    formatTime,
    formatBytes,
    getStatusColor,
    createProgressBar,
    createStatusBadge,
    debounce,
    throttle,
    deepClone,
    generateId,
    validateForm,
    clearFormValidation,
    setLoadingState,
    handleError,
    handleSuccess
};

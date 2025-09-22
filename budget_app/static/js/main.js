// File: budget_project/budget_app/static/js/main.js
// REVERTED VERSION (Simple, non-dynamic dropdowns)

lucide.createIcons();

const AppState = {
    entries: [],
    masters: {
        clients: [], // Will be a simple array of strings
        products: [], // Will be an array of objects
        productMap: {},
        pmtMap: {},
        gmMap: {}
    },
    filters: {},
    selectedEntries: new Set()
};
let sessionId = null;

function rebuildMasterLookups() {
    AppState.masters.productMap = {};
    AppState.masters.pmtMap = {};
    AppState.masters.gmMap = {};
    (AppState.masters.products || []).forEach(product => {
        if (product.Product) {
            AppState.masters.productMap[product.Product] = product.Category || '';
            if (product.Default_PMT) AppState.masters.pmtMap[product.Product] = parseFloat(product.Default_PMT);
            if (product['Default_GM%']) AppState.masters.gmMap[product.Product] = parseFloat(product['Default_GM%']);
        }
    });
    console.log("Master lookup maps have been rebuilt.");
}

const Utils = {
    formatCurrency: (amount) => new Intl.NumberFormat('en-JO', { style: 'currency', currency: 'JOD', minimumFractionDigits: 2 }).format(amount || 0),
    formatNumber: (num, decimals = 2) => {
        if (isNaN(num) || num === null) return (0).toFixed(decimals);
        return new Intl.NumberFormat('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(num);
    },
    monthNumToName: (num) => ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][num - 1] || '-',
    showNotification: (message, type = 'info') => {
        const container = document.getElementById('notificationContainer');
        const notification = document.createElement('div');
        const typeClasses = {
            success: 'border-green-500 text-green-600',
            error: 'border-red-500 text-red-600',
            warning: 'border-yellow-500 text-yellow-600',
            info: 'border-blue-500 text-blue-600'
        };
        const iconName = { success: 'check-circle', error: 'x-circle', warning: 'alert-triangle', info: 'info' };

        notification.className = `notification bg-white border-l-4 p-4 rounded-lg shadow-lg ${typeClasses[type] || typeClasses.info}`;
        notification.innerHTML = `
            <div class="flex items-start">
                <i data-lucide="${iconName[type] || 'info'}" class="w-5 h-5 mr-3 flex-shrink-0 mt-1"></i>
                <div class="text-gray-800">${message}</div>
                <button class="ml-auto text-gray-400 hover:text-gray-600" onclick="this.parentElement.parentElement.remove()">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            </div>`;
        container.appendChild(notification);
        lucide.createIcons();
        setTimeout(() => notification.remove(), 7000);
    },
    showLoading: (show = true) => document.getElementById('loadingOverlay').classList.toggle('hidden', !show),
};

const API = {
    async _fetchWithSession(url, options = {}) {
        const headers = { 'Content-Type': 'application/json', ...options.headers };
        if (sessionId) headers['X-Session-ID'] = sessionId;
        const response = await fetch(url, { ...options, headers });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'An API error occurred');
        }
        return response.json();
    },
    async loadState() {
        const data = await this._fetchWithSession('/api/state');
        sessionId = data.session_id;
        AppState.entries = data.entries || [];
        AppState.masters.clients = data.masters?.clients || [];
        AppState.masters.products = data.masters?.products || [];
        rebuildMasterLookups();
        return data;
    },
    async addEntry(entryData) {
        return this._fetchWithSession('/api/add', { method: 'POST', body: JSON.stringify(entryData) });
    },
};

const UI = {
    initializeTabs() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabPanels = document.querySelectorAll('.tab-panel');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetId = button.id.replace('tab', 'panel');
                tabButtons.forEach(btn => {
                    btn.classList.remove('border-primary-500', 'text-primary-600');
                    btn.classList.add('border-transparent', 'text-gray-500');
                });
                button.classList.add('border-primary-500', 'text-primary-600');
                tabPanels.forEach(panel => panel.classList.add('hidden'));
                document.getElementById(targetId).classList.remove('hidden');
            });
        });
    },

    initializeForm() {
        const clientSelect = document.getElementById('client');
        clientSelect.innerHTML = '';
        AppState.masters.clients.forEach(client => {
            const option = document.createElement('option');
            option.value = client;
            option.textContent = client;
            clientSelect.appendChild(option);
        });

        const productSelect = document.getElementById('product');
        productSelect.innerHTML = '';
        AppState.masters.products.forEach(product => {
            const option = document.createElement('option');
            option.value = product.Product;
            option.textContent = product.Product;
            productSelect.appendChild(option);
        });

        productSelect.addEventListener('change', () => this.updateProductDefaults());
        
        const previewFields = ['pmtQ1', 'pmtQ2', 'pmtQ3', 'pmtQ4', 'gmPercent', 'qtyJan', 'qtyFeb', 'qtyMar', 'qtyApr', 'qtyMay', 'qtyJun', 'qtyJul', 'qtyAug', 'qtySep', 'qtyOct', 'qtyNov', 'qtyDec'];
        previewFields.forEach(id => {
            document.getElementById(id)?.addEventListener('input', () => this.updatePreview());
        });
        
        this.updateProductDefaults();
        this.updatePreview();
    },

    updateProductDefaults() {
        const productSelect = document.getElementById('product');
        const categoryDisplay = document.getElementById('categoryDisplay');
        const selectedProduct = productSelect.value;
        
        categoryDisplay.value = AppState.masters.productMap[selectedProduct] || 'Unknown';
        const defaultPMT = AppState.masters.pmtMap[selectedProduct] ?? '';
        const defaultGM = AppState.masters.gmMap[selectedProduct] ?? '';

        ['pmtQ1', 'pmtQ2', 'pmtQ3', 'pmtQ4'].forEach(id => {
            const field = document.getElementById(id);
            if (field && !field.value) field.value = defaultPMT;
        });
        const gmField = document.getElementById('gmPercent');
        if (gmField && !gmField.value) gmField.value = defaultGM;

        this.updatePreview();
    },
    
    updatePreview() {
        const pmtQ1 = parseFloat(document.getElementById('pmtQ1')?.value) || 0;
        const pmtQ2 = parseFloat(document.getElementById('pmtQ2')?.value) || 0;
        const pmtQ3 = parseFloat(document.getElementById('pmtQ3')?.value) || 0;
        const pmtQ4 = parseFloat(document.getElementById('pmtQ4')?.value) || 0;
        const gm = parseFloat(document.getElementById('gmPercent')?.value) || 0;
        const getQty = (id) => parseFloat(document.getElementById(id)?.value) || 0;
        const salesQ1 = (getQty('qtyJan') + getQty('qtyFeb') + getQty('qtyMar')) * pmtQ1;
        const salesQ2 = (getQty('qtyApr') + getQty('qtyMay') + getQty('qtyJun')) * pmtQ2;
        const salesQ3 = (getQty('qtyJul') + getQty('qtyAug') + getQty('qtySep')) * pmtQ3;
        const salesQ4 = (getQty('qtyOct') + getQty('qtyNov') + getQty('qtyDec')) * pmtQ4;
        const totalSales = salesQ1 + salesQ2 + salesQ3 + salesQ4;
        const gmFactor = gm / 100;
        const gpQ1 = salesQ1 * gmFactor;
        const gpQ2 = salesQ2 * gmFactor;
        const gpQ3 = salesQ3 * gmFactor;
        const gpQ4 = salesQ4 * gmFactor;
        const totalGP = gpQ1 + gpQ2 + gpQ3 + gpQ4;
        const u = (val) => Utils.formatNumber(val, 0) + ' JOD';
        document.getElementById('previewQ1Sales').textContent = u(salesQ1);
        document.getElementById('previewQ2Sales').textContent = u(salesQ2);
        document.getElementById('previewQ3Sales').textContent = u(salesQ3);
        document.getElementById('previewQ4Sales').textContent = u(salesQ4);
        document.getElementById('previewTotalSales').textContent = u(totalSales);
        document.getElementById('previewQ1GP').textContent = u(gpQ1);
        document.getElementById('previewQ2GP').textContent = u(gpQ2);
        document.getElementById('previewQ3GP').textContent = u(gpQ3);
        document.getElementById('previewQ4GP').textContent = u(gpQ4);
        document.getElementById('previewTotalGP').textContent = u(totalGP);
    },
};

async function initializeApp() {
    try {
        await API.loadState();
        UI.initializeTabs();
        UI.initializeForm();
        // UI.updateStats(); // Can add this and other UI calls back
        Utils.showNotification('Application ready', 'success');
    } catch (error) {
        console.error('Failed to initialize application:', error);
        Utils.showNotification('Could not load application data. Please refresh.', 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});
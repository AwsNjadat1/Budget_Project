// Initialize Lucide icons
lucide.createIcons();

// Application State
const AppState = {
    entries: [],
    masters: {
        // These will now be arrays of objects, e.g., [{Client: 'ACME', 'Business Unit': 'Oils'}]
        clients: [],
        products: [],
        productMap: {}, // Will still be used for category lookup
    },
    filters: {},
    selectedEntries: new Set()
};
let sessionId = null;

// This function is now simplified, as defaults are part of the main product object
function rebuildMasterLookups() {
    AppState.masters.productMap = {};
    (AppState.masters.products || []).forEach(product => {
        if (product.Product) {
            AppState.masters.productMap[product.Product] = product;
        }
    });
    console.log("Master product lookup map has been rebuilt.");
}

// --- Utility Functions (Unchanged) ---
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
        notification.className = `notification bg-white border-l-4 p-4 rounded-lg shadow-lg ${ type === 'success' ? 'border-green-500' : type === 'error' ? 'border-red-500' : 'border-blue-500' }`;
        const icon = type === 'success' ? 'check-circle' : 'x-circle';
        notification.innerHTML = `<div class="flex items-start"><i data-lucide="${icon}" class="w-5 h-5 mr-3"></i><div>${message}</div></div>`;
        container.appendChild(notification);
        lucide.createIcons();
        setTimeout(() => notification.remove(), 7000);
    },
    showLoading: (show = true) => document.getElementById('loadingOverlay').classList.toggle('hidden', !show),
};

// --- API Functions (Unchanged) ---
const API = {
    async _fetchWithSession(url, options = {}) {
        const headers = { 'Content-Type': 'application/json', ...options.headers };
        if (sessionId) headers['X-Session-ID'] = sessionId;
        const response = await fetch(url, { ...options, headers });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'API error');
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
        const data = await this._fetchWithSession('/api/add', { method: 'POST', body: JSON.stringify(entryData) });
        AppState.entries = data.entries || [];
        return data;
    },
    // ... other API functions are the same ...
};

// --- UI Component (HEAVILY MODIFIED) ---
const UI = {
    initializeTabs() { /* ... unchanged ... */ },

    // NEW: This function handles all the dynamic dropdown logic
    updateDependentDropdowns() {
        const buSelect = document.getElementById('businessUnit');
        const clientSelect = document.getElementById('client');
        const productSelect = document.getElementById('product');
        const newClientInput = document.getElementById('newClient');

        const selectedBU = buSelect.value;

        // Clear and disable dropdowns if no BU is selected
        if (!selectedBU) {
            clientSelect.innerHTML = '<option value="">-- Select a Business Unit First --</option>';
            productSelect.innerHTML = '<option value="">-- Select a Business Unit First --</option>';
            clientSelect.disabled = true;
            productSelect.disabled = true;
            newClientInput.disabled = true;
            return;
        }

        // Enable dropdowns
        clientSelect.disabled = false;
        productSelect.disabled = false;
        newClientInput.disabled = false;

        // Filter clients based on selected Business Unit
        const filteredClients = AppState.masters.clients.filter(
            c => c['Business Unit'] === selectedBU || c['Business Unit'] === 'All'
        );
        const uniqueClients = [...new Set(filteredClients.map(c => c.Client))]; // Get unique names
        clientSelect.innerHTML = '<option value="">Select Client</option>';
        uniqueClients.sort().forEach(client => {
            clientSelect.innerHTML += `<option value="${client}">${client}</option>`;
        });

        // Filter products based on selected Business Unit
        const filteredProducts = AppState.masters.products.filter(
            p => p['Business Unit'] === selectedBU || p['Business Unit'] === 'All'
        );
        productSelect.innerHTML = '<option value="">Select Product</option>';
        filteredProducts.forEach(product => {
            productSelect.innerHTML += `<option value="${product.Product}">${product.Product}</option>`;
        });

        // Trigger an update to clear old values
        this.updateProductDefaults();
    },

    // MODIFIED: This function now sets up the initial state and listeners
    initializeForm() {
        // Add "Select" option to Business Unit
        const buSelect = document.getElementById('businessUnit');
        buSelect.insertAdjacentHTML('afterbegin', '<option value="" selected>Select Business Unit</option>');
        
        // Add event listeners that trigger the dynamic updates
        buSelect.addEventListener('change', () => this.updateDependentDropdowns());
        document.getElementById('product').addEventListener('change', () => this.updateProductDefaults());
        
        // Add listeners for live preview
        const previewFields = ['pmtQ1', 'pmtQ2', 'pmtQ3', 'pmtQ4', 'gmPercent', 'qtyJan', 'qtyFeb', 'qtyMar', 'qtyApr', 'qtyMay', 'qtyJun', 'qtyJul', 'qtyAug', 'qtySep', 'qtyOct', 'qtyNov', 'qtyDec'];
        previewFields.forEach(id => {
            document.getElementById(id)?.addEventListener('input', () => this.updatePreview());
        });

        // Initial call to set the disabled state
        this.updateDependentDropdowns();
        this.updatePreview();
    },

    // MODIFIED: This function now gets defaults from the productMap
    updateProductDefaults() {
        const productSelect = document.getElementById('product');
        const categoryDisplay = document.getElementById('categoryDisplay');
        const selectedProduct = productSelect.value;
        const productData = AppState.masters.productMap[selectedProduct];

        if (productData) {
            categoryDisplay.value = productData.Category || 'Unknown';
            const defaultPMT = productData.Default_PMT ?? '';
            const defaultGM = productData['Default_GM%'] ?? '';

            ['pmtQ1', 'pmtQ2', 'pmtQ3', 'pmtQ4'].forEach(id => {
                const field = document.getElementById(id);
                if (field && !field.value) field.value = defaultPMT;
            });
            const gmField = document.getElementById('gmPercent');
            if (gmField && !gmField.value) gmField.value = defaultGM;

        } else {
            categoryDisplay.value = '';
        }
        this.updatePreview();
    },
    
    updatePreview() { /* ... unchanged ... */ },
    updateStats() { /* ... unchanged ... */ },
    // ... rest of UI functions are mostly unchanged ...
};

// --- Event Handlers (Unchanged) ---
const EventHandlers = {
    setupFormHandlers() { /* ... unchanged ... */ },
    setupManageHandlers() { /* ... unchanged ... */ },
    setupFileHandlers() { /* ... unchanged ... */ },
    resetForm() { /* ... unchanged ... */ },
};

// --- Application Initialization (Unchanged) ---
async function initializeApp() {
    try {
        await API.loadState();
        UI.initializeTabs();
        UI.initializeForm(); // This now sets up the dynamic behavior
        UI.updateStats();
        // UI.initializeFilters(); // Filters will need updating for this logic too
        // UI.updateMasterDataDisplay();
        EventHandlers.setupFormHandlers();
        EventHandlers.setupManageHandlers();
        EventHandlers.setupFileHandlers();
        Utils.showNotification('Application ready', 'success');
    } catch (error) {
        console.error('Failed to initialize application:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    // File save logic remains the same
});
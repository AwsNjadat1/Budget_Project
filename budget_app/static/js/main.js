// static/js/main.js

// Initialize Lucide icons
lucide.createIcons();

// Application State
const AppState = {
    entries: [],
    masters: {
        clients: [],
        products: [],
        productMap: {},
    },
    filters: {
        businessUnit: '',
        section: '',
        client: '',
        product: '',
        search: ''
    },
    selectedEntries: new Set(),
    exchangeRates: window.EXCHANGE_RATES || { 'USD': 1.0, 'JOD': 0.71, 'EUR': 0.86 }
};
let sessionId = null;

function rebuildMasterLookups() {
    AppState.masters.productMap = {};
    (AppState.masters.products || []).forEach(product => {
        const p = product?.Product;
        if (!p) return;
        AppState.masters.productMap[p] = product?.Category ?? '';
    });
    console.log("Master product->category lookup map has been rebuilt.");
}

// Utility Functions
const Utils = {
    formatCurrency: (amount) => {
        return new Intl.NumberFormat('en-JO', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(amount || 0);
    },
    formatNumber: (num, decimals = 2) => {
        if (isNaN(num) || num === null) return (0).toFixed(decimals);
        return new Intl.NumberFormat('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(num);
    },
    monthNameToNum: (name) => {
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return months.indexOf(name) + 1 || parseInt(name) || 1;
    },
    monthNumToName: (num) => {
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return (num >= 1 && num <= 12) ? months[num - 1] : '-';
    },
    showNotification: (message, type = 'info') => {
        const container = document.getElementById('notificationContainer');
        const notification = document.createElement('div');
        notification.className = `notification bg-white border-l-4 p-4 rounded-lg shadow-lg ${
            type === 'success' ? 'border-green-500' : 
            type === 'error' ? 'border-red-500' : 
            type === 'warning' ? 'border-yellow-500' : 'border-blue-500'
        }`;
        const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'x-circle' : type === 'warning' ? 'alert-triangle' : 'info';
        const color = type === 'success' ? 'text-green-600' : type === 'error' ? 'text-red-600' : type === 'warning' ? 'text-yellow-600' : 'text-blue-600';
        notification.innerHTML = `
            <div class="flex items-start">
                <i data-lucide="${icon}" class="w-5 h-5 ${color} mr-3 flex-shrink-0 mt-1"></i>
                <div class="text-gray-800">${message}</div>
                <button class="ml-auto text-gray-400 hover:text-gray-600" onclick="this.parentElement.parentElement.remove()">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            </div>`;
        container.appendChild(notification);
        lucide.createIcons();
        setTimeout(() => { if (notification.parentElement) { notification.remove(); } }, 7000);
    },
    showLoading: (show = true) => {
        document.getElementById('loadingOverlay').classList.toggle('hidden', !show);
    }
};

// API Functions
const API = {
    async _fetchWithSession(url, options = {}) {
        const headers = { 'Content-Type': 'application/json', ...options.headers };
        const response = await fetch(url, { ...options, headers });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || errorData.message || 'An API error occurred');
        }
        return response.json();
    },
    async loadState() {
        try {
            const data = await this._fetchWithSession('/api/state');
            AppState.entries = data.entries || [];
            AppState.masters.clients = data.masters?.clients || [];
            AppState.masters.products = data.masters?.products || [];
            rebuildMasterLookups();
            return data;
        } catch (error) {
            Utils.showNotification('Failed to load application state: ' + error.message, 'error');
            throw error;
        }
    },
    async addEntry(entryData) {
        try {
            const data = await this._fetchWithSession('/api/add', { method: 'POST', body: JSON.stringify(entryData) });
            AppState.entries = data.entries || [];
            return data;
        } catch (error) {
            Utils.showNotification('Failed to add entry: ' + error.message, 'error');
            throw error;
        }
    },
    async commitChanges(editedRows, deleteIds) {
        try {
            Utils.showLoading(true);
            const data = await this._fetchWithSession('/api/commit', { method: 'POST', body: JSON.stringify({ editedRows, deleteIds }) });
            AppState.entries = data.entries || [];
            Utils.showNotification('Changes saved successfully', 'success');
            return data;
        } catch (error) {
            Utils.showNotification('Failed to save changes: ' + error.message, 'error');
            throw error;
        } finally {
            Utils.showLoading(false);
        }
    },
    async addMasterData(masterData) {
        try {
            Utils.showLoading(true);
            const data = await this._fetchWithSession('/api/add_master', { method: 'POST', body: JSON.stringify(masterData) });
            AppState.masters.clients = data.masters.clients || [];
            AppState.masters.products = data.masters.products || [];
            rebuildMasterLookups();
            UI.initializeForm();
            Utils.showNotification(data.message, 'success');
            return data;
        } catch (error) {
            Utils.showNotification('Failed to add new master data: ' + error.message, 'error');
            throw error;
        } finally {
            Utils.showLoading(false);
        }
    },
    async updateEntry(entryId, field, value) {
        try {
            Utils.showLoading(true);
            const data = await this._fetchWithSession('/api/update_entry', {
                method: 'POST',
                body: JSON.stringify({ entry_id: entryId, field: field, value: value })
            });
            AppState.entries = data.entries || [];
            Utils.showNotification('Entry updated successfully!', 'success');
            return data;
        } catch (error) {
            Utils.showNotification('Failed to update entry: ' + error.message, 'error');
            throw error;
        } finally {
            Utils.showLoading(false);
        }
    }
};

// UI Components
const UI = {

    _getQuarterlyPmtsInUSD() {
        // Find which currency radio button is currently checked.
        const selectedCurrency = document.querySelector('input[name="pmt_currency"]:checked').value || 'USD';
        const rate = AppState.exchangeRates[selectedCurrency] || 1.0;

        // Read the raw input values from the form.
        const pmtQ1_raw = parseFloat(document.getElementById('pmtQ1')?.value) || 0;
        const pmtQ2_raw = parseFloat(document.getElementById('pmtQ2')?.value) || 0;
        const pmtQ3_raw = parseFloat(document.getElementById('pmtQ3')?.value) || 0;
        const pmtQ4_raw = parseFloat(document.getElementById('pmtQ4')?.value) || 0;
        
        // If the selected currency is already USD, the rate is 1, so no conversion happens.
        // If it's JOD or EUR, we divide by the rate to get the USD equivalent.
        // Formula: AmountInUSD = AmountInForeignCurrency / RateToGetThatCurrencyFrom1USD
        // Example JOD: 10 JOD / 0.77 = 12.98 USD
        // Example EUR: 10 EUR / 0.86 = 11.62 USD
        return {
            pmtQ1: pmtQ1_raw / rate,
            pmtQ2: pmtQ2_raw / rate,
            pmtQ3: pmtQ3_raw / rate,
            pmtQ4: pmtQ4_raw / rate
        };
    },

    _getProfitPerTonInUSD() {
        // Find which currency radio button is currently checked.
        const selectedCurrency = document.querySelector('input[name="profit_currency"]:checked').value || 'USD';
        const rate = AppState.exchangeRates[selectedCurrency] || 1.0;

        // Read the raw input value from the form.
        const profitPerTon_raw = parseFloat(document.getElementById('profitPerTon')?.value) || 0;

        // Convert the raw value to its USD equivalent.
        return profitPerTon_raw / rate;
    },

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
                button.classList.remove('border-transparent', 'text-gray-500');
                button.classList.add('border-primary-500', 'text-primary-600');
                tabPanels.forEach(panel => panel.classList.add('hidden'));
                document.getElementById(targetId).classList.remove('hidden');
                if (targetId === 'panelManage') { this.renderDataTable(); }
            });
        });
    },
    
    initializeForm() {
        const clientSelect = document.getElementById('client');
        if (clientSelect) {
            clientSelect.innerHTML = '';
            AppState.masters.clients.forEach(client => {
                const option = document.createElement('option');
                option.value = client;
                option.textContent = client;
                clientSelect.appendChild(option);
            });
        }
        
        const productSelect = document.getElementById('product');
        if (productSelect) {
            productSelect.innerHTML = '';
            AppState.masters.products.forEach(product => {
                const option = document.createElement('option');
                option.value = product.Product;
                option.textContent = product.Product;
                productSelect.appendChild(option);
            });
        }
        
        const productField = document.getElementById('product');
        if (productField && !productField.dataset.listenerAttached) {
            productField.addEventListener('change', this.updateProductDefaults.bind(this));
            productField.dataset.listenerAttached = 'true';
        }

        const sectionField = document.getElementById('section');
        if (sectionField && !sectionField.dataset.listenerAttached) {
            sectionField.addEventListener('change', this.toggleInputMode.bind(this));
            sectionField.dataset.listenerAttached = 'true';
        }

        ['pmtQ1', 'pmtQ2', 'pmtQ3', 'pmtQ4', 'gmPercent', 'profitPerTon'].forEach(id => {
            const element = document.getElementById(id);
            if (element && !element.dataset.listenerAttached) {
                element.addEventListener('input', this.updatePreview.bind(this));
                element.dataset.listenerAttached = 'true';
            }
        });
        
        ['qtyJan', 'qtyFeb', 'qtyMar', 'qtyApr', 'qtyMay', 'qtyJun', 'qtyJul', 'qtyAug', 'qtySep', 'qtyOct', 'qtyNov', 'qtyDec'].forEach(id => {
            const element = document.getElementById(id);
            if (element && !element.dataset.listenerAttached) {
                element.addEventListener('input', this.updatePreview.bind(this));
                element.dataset.listenerAttached = 'true';
            }
        });
        
        this.updateProductDefaults();
        this.toggleInputMode();
        this.updatePreview();
    },

    toggleInputMode() {
        const section = document.getElementById('section').value;
        const isBrokerOrMining = (section === 'Broker' || section === 'Mining');
        document.getElementById('pmtSection').classList.toggle('hidden', isBrokerOrMining);
        document.getElementById('gpSection').classList.toggle('hidden', isBrokerOrMining);
        document.getElementById('profitSection').classList.toggle('hidden', !isBrokerOrMining);
        this.updatePreview();
    },
    
    updateProductDefaults() {
        const productField = document.getElementById('product');
        const categoryField = document.getElementById('categoryDisplay');
        if (!productField || !categoryField) return;
        const product = productField.value;
        const category = AppState.masters.productMap[product] || 'Unknown';
        categoryField.value = category;
        this.updatePreview();
    },
    
    updatePreview() {
        const section = document.getElementById('section').value;
        const isBrokerOrMining = (section === 'Broker' || section === 'Mining');
        const qtyJan = parseFloat(document.getElementById('qtyJan')?.value) || 0;
        const qtyFeb = parseFloat(document.getElementById('qtyFeb')?.value) || 0;
        const qtyMar = parseFloat(document.getElementById('qtyMar')?.value) || 0;
        const qtyApr = parseFloat(document.getElementById('qtyApr')?.value) || 0;
        const qtyMay = parseFloat(document.getElementById('qtyMay')?.value) || 0;
        const qtyJun = parseFloat(document.getElementById('qtyJun')?.value) || 0;
        const qtyJul = parseFloat(document.getElementById('qtyJul')?.value) || 0;
        const qtyAug = parseFloat(document.getElementById('qtyAug')?.value) || 0;
        const qtySep = parseFloat(document.getElementById('qtySep')?.value) || 0;
        const qtyOct = parseFloat(document.getElementById('qtyOct')?.value) || 0;
        const qtyNov = parseFloat(document.getElementById('qtyNov')?.value) || 0;
        const qtyDec = parseFloat(document.getElementById('qtyDec')?.value) || 0;
        let salesQ1 = 0, salesQ2 = 0, salesQ3 = 0, salesQ4 = 0;
        let gpQ1 = 0, gpQ2 = 0, gpQ3 = 0, gpQ4 = 0;
        if (isBrokerOrMining) {
            const profitPerTon = this._getProfitPerTonInUSD();
            gpQ1 = (qtyJan + qtyFeb + qtyMar) * profitPerTon;
            gpQ2 = (qtyApr + qtyMay + qtyJun) * profitPerTon;
            gpQ3 = (qtyJul + qtyAug + qtySep) * profitPerTon;
            gpQ4 = (qtyOct + qtyNov + qtyDec) * profitPerTon;
        } else {
            const { pmtQ1, pmtQ2, pmtQ3, pmtQ4 } = this._getQuarterlyPmtsInUSD();
            
            const gm = parseFloat(document.getElementById('gmPercent')?.value) || 0;
            const gmFactor = gm / 100;
            
            // All calculations from this point on are guaranteed to be in USD.
            salesQ1 = (qtyJan + qtyFeb + qtyMar) * pmtQ1;
            salesQ2 = (qtyApr + qtyMay + qtyJun) * pmtQ2;
            salesQ3 = (qtyJul + qtyAug + qtySep) * pmtQ3;
            salesQ4 = (qtyOct + qtyNov + qtyDec) * pmtQ4;
            gpQ1 = salesQ1 * gmFactor;
            gpQ2 = salesQ2 * gmFactor;
            gpQ3 = salesQ3 * gmFactor;
            gpQ4 = salesQ4 * gmFactor;
        }
        const totalSales = salesQ1 + salesQ2 + salesQ3 + salesQ4;
        const totalGP = gpQ1 + gpQ2 + gpQ3 + gpQ4;
        const u = Utils.formatNumber;
        document.getElementById('previewQ1Sales').textContent = u(salesQ1, 0) + ' USD';
        document.getElementById('previewQ2Sales').textContent = u(salesQ2, 0) + ' USD';
        document.getElementById('previewQ3Sales').textContent = u(salesQ3, 0) + ' USD';
        document.getElementById('previewQ4Sales').textContent = u(salesQ4, 0) + ' USD';
        document.getElementById('previewTotalSales').textContent = u(totalSales, 0) + ' USD';
        document.getElementById('previewQ1GP').textContent = u(gpQ1, 0) + ' USD';
        document.getElementById('previewQ2GP').textContent = u(gpQ2, 0) + ' USD';
        document.getElementById('previewQ3GP').textContent = u(gpQ3, 0) + ' USD';
        document.getElementById('previewQ4GP').textContent = u(gpQ4, 0) + ' USD';
        document.getElementById('previewTotalGP').textContent = u(totalGP, 0) + ' USD';
    },
    
    updateStats() {
        const totalEntries = AppState.entries.length;
        const totalSales = AppState.entries.reduce((sum, entry) => sum + (parseFloat(entry['Sales (USD)']) || 0), 0);
        const totalGP = AppState.entries.reduce((sum, entry) => sum + (parseFloat(entry['GP (USD)']) || 0), 0);
        const avgGM = totalSales > 0 ? (totalGP / totalSales) * 100 : 0;
        document.getElementById('totalEntries').textContent = totalEntries;
        document.getElementById('totalSales').textContent = Utils.formatNumber(totalSales, 0) + ' USD';
        document.getElementById('totalGP').textContent = Utils.formatNumber(totalGP, 0) + ' USD';
        document.getElementById('avgGM').textContent = Utils.formatNumber(avgGM, 1) + '%';
    },
    
    initializeFilters() {
        const businessUnits = [...new Set(AppState.entries.map(e => e['Business Unit']).filter(Boolean))];
        const sections = [...new Set(AppState.entries.map(e => e.Section).filter(Boolean))];
        const clients = [...new Set(AppState.entries.map(e => e.Client).filter(Boolean))];
        const products = [...new Set(AppState.entries.map(e => e.Product).filter(Boolean))];
        this.populateFilter('filterBU', businessUnits, '(All Business Units)');
        this.populateFilter('filterSection', sections, '(All Sections)');
        this.populateFilter('filterClient', clients, '(All Clients)');
        this.populateFilter('filterProduct', products, '(All Products)');
        ['filterBU', 'filterSection', 'filterClient', 'filterProduct', 'filterSearch'].forEach(id => {
            const el = document.getElementById(id);
            if (el && !el.dataset.listenerAttached) {
                el.addEventListener('input', this.renderDataTable.bind(this));
                el.dataset.listenerAttached = 'true';
            }
        });
    },
    
    populateFilter(selectId, options, defaultText) {
        const select = document.getElementById(selectId);
        select.innerHTML = `<option value="">${defaultText}</option>`;
        options.sort().forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option;
            optionElement.textContent = option;
            select.appendChild(optionElement);
        });
    },
    
    getFilteredEntries() {
        const filters = {
            businessUnit: document.getElementById('filterBU').value,
            section: document.getElementById('filterSection').value,
            client: document.getElementById('filterClient').value,
            product: document.getElementById('filterProduct').value,
            search: document.getElementById('filterSearch').value.toLowerCase()
        };
        return AppState.entries.filter(entry => {
            if (filters.businessUnit && entry['Business Unit'] !== filters.businessUnit) return false;
            if (filters.section && entry.Section !== filters.section) return false;
            if (filters.client && entry.Client !== filters.client) return false;
            if (filters.product && entry.Product !== filters.product) return false;
            if (filters.search && !`${entry.Client} ${entry.Product}`.toLowerCase().includes(filters.search)) return false;
            return true;
        });
    },
    
    renderDataTable() {
        const filteredEntries = this.getFilteredEntries();
        const tbody = document.getElementById('dataTableBody');
        tbody.innerHTML = '';
        filteredEntries.forEach(entry => {
            const row = document.createElement('tr');
            row.className = 'table-row transition-all duration-150';
            const u = Utils.formatNumber;
            const isBrokerOrMining = (entry.Section === 'Broker' || entry.Section === 'Mining');

            row.innerHTML = `
                <td class="px-4 py-3"><input type="checkbox" class="entry-checkbox rounded" data-id="${entry._rid}"></td>
                <td class="px-4 py-3 text-sm">${entry['Business Unit'] || ''}</td>
                <td class="px-4 py-3 text-sm">${entry['User Name'] || ''}</td>
                <td class="px-4 py-3 text-sm">${entry.Section || ''}</td>
                <td class="px-4 py-3 text-sm">${entry.Client || ''}</td>
                <td class="px-4 py-3 text-sm">${entry.Category || ''}</td>
                <td class="px-4 py-3 text-sm">${entry.Product || ''}</td>
                <td class="px-4 py-3 text-sm">${Utils.monthNumToName(entry.Month)}</td>
                <td class="editable-cell px-4 py-3 text-sm text-left" data-entry-id="${entry._rid}" data-field-name="Qty (MT)">${u(entry['Qty (MT)'])}</td>
                <td class="${!isBrokerOrMining ? 'editable-cell' : ''} px-4 py-3 text-sm text-left" ${!isBrokerOrMining ? `data-entry-id="${entry._rid}" data-field-name="PMT (USD)"` : ''}>${u(entry['PMT (USD)'])}</td>
                <td class="px-4 py-3 text-sm text-green-600 font-medium text-left">${u(entry['Sales (USD)'], 0)}</td>
                <td class="px-4 py-3 text-sm text-blue-600 font-medium text-left">${u(entry['GP (USD)'], 0)}</td>
                <td class="${!isBrokerOrMining ? 'editable-cell' : ''} px-4 py-3 text-sm text-left" ${!isBrokerOrMining ? `data-entry-id="${entry._rid}" data-field-name="GP %"` : ''}>${u(entry['GP %'], 1)}%</td>
                <td class="${isBrokerOrMining ? 'editable-cell' : ''} px-4 py-3 text-sm text-left" ${isBrokerOrMining ? `data-entry-id="${entry._rid}" data-field-name="Profit per Ton"` : ''}>${u(entry['Profit per Ton'])}</td>                
                <td class="px-4 py-3 text-sm"><span class="px-2 py-1 text-xs rounded-full ${entry.Booked === 'Yes' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">${entry.Booked || 'No'}</span></td>
            `;
            tbody.appendChild(row);
        });
        
        const filteredSales = filteredEntries.reduce((sum, entry) => sum + (parseFloat(entry['Sales (USD)']) || 0), 0);
        const filteredGP = filteredEntries.reduce((sum, entry) => sum + (parseFloat(entry['GP (USD)']) || 0), 0);
        
        document.getElementById('filteredCount').textContent = filteredEntries.length;
        document.getElementById('filteredSales').textContent = Utils.formatNumber(filteredSales, 0) + ' USD';
        document.getElementById('filteredGP').textContent = Utils.formatNumber(filteredGP, 0) + ' USD';
        
        const selectAllCheckbox = document.getElementById('selectAll');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                document.querySelectorAll('.entry-checkbox').forEach(cb => cb.checked = e.target.checked);
            });
        }
    },

    makeCellEditable(cell) {
        if (cell.querySelector('input')) return;
        const originalValue = cell.textContent.replace(/[,%]/g, '');
        cell.dataset.originalValue = originalValue;
        const input = document.createElement('input');
        input.type = 'number';
        input.step = '0.01';
        input.className = 'w-full px-1 py-0 border rounded';
        input.value = originalValue;
        cell.innerHTML = '';
        cell.appendChild(input);
        input.focus();
        input.addEventListener('blur', () => this.saveCellEdit(input));
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                input.blur();
            } else if (e.key === 'Escape') {
                this.cancelCellEdit(input);
            }
        });
    },

    async saveCellEdit(input) {
        const cell = input.parentElement;
        const entryId = cell.dataset.entryId;
        const fieldName = cell.dataset.fieldName;
        const newValue = input.value;
        try {
            await API.updateEntry(entryId, fieldName, newValue);
            UI.updateStats();
            UI.renderDataTable(); 
        } catch (error) {
            console.error("Failed to save cell edit:", error);
            cell.textContent = cell.dataset.originalValue;
        }
    },

    cancelCellEdit(input) {
        const cell = input.parentElement;
        const originalFormattedValue = Utils.formatNumber(parseFloat(cell.dataset.originalValue), cell.dataset.fieldName === 'GP %' ? 1 : 2);
        cell.innerHTML = cell.dataset.fieldName === 'GP %' ? originalFormattedValue + '%' : originalFormattedValue;
    },
    
    updateMasterDataDisplay() {
        const clientsList = document.getElementById('clientsList');
        const clientCount = document.getElementById('clientCount');
        clientCount.textContent = AppState.masters.clients.length;
        clientsList.innerHTML = AppState.masters.clients.map(client => `<div class="py-1">${client}</div>`).join('') || '<div class="italic">No clients loaded</div>';
        
        const productsList = document.getElementById('productsList');
        const productCount = document.getElementById('productCount');
        productCount.textContent = AppState.masters.products.length;
        productsList.innerHTML = AppState.masters.products.map(product => `<div class="py-1">${product.Product} <span class="text-gray-500">(${product.Category})</span></div>`).join('') || '<div class="italic">No products loaded</div>';
    }
};

// Event Handlers
const EventHandlers = {
    setupPmtCurrencyHandlers() {
        const currencyRadios = document.querySelectorAll('input[name="pmt_currency"]');
        const currencyLabel = document.getElementById('pmtCurrencyLabel');
        
        currencyRadios.forEach(radio => {
            // Check if a listener has already been attached to prevent duplicates
            if (!radio.dataset.listenerAttached) {
                radio.addEventListener('change', (event) => {
                    const selectedCurrency = event.target.value;
                    // Update the label in the section title
                    if (currencyLabel) {
                        currencyLabel.textContent = selectedCurrency;
                    }
                    // Trigger a recalculation of the live preview
                    UI.updatePreview(); 
                });
                radio.dataset.listenerAttached = 'true';
            }
        });
    },
    setupProfitCurrencyHandlers() {
        const currencyRadios = document.querySelectorAll('input[name="profit_currency"]');
        const currencyLabel = document.getElementById('profitCurrencyLabel');
        
        currencyRadios.forEach(radio => {
            if (!radio.dataset.listenerAttached) {
                radio.addEventListener('change', (event) => {
                    const selectedCurrency = event.target.value;
                    if (currencyLabel) {
                        currencyLabel.textContent = selectedCurrency;
                    }
                    UI.updatePreview(); 
                });
                radio.dataset.listenerAttached = 'true';
            }
        });
    },
    setupFormHandlers() {
        const btnAddEntry = document.getElementById('btnAddEntry');
        if (btnAddEntry && !btnAddEntry.dataset.listenerAttached) {
            btnAddEntry.addEventListener('click', async () => {
                Utils.showLoading(true);
                let selectedClient = document.getElementById('client').value;
                let selectedProduct = document.getElementById('product').value;
                
                try {
                    const newClient = document.getElementById('newClient').value.trim();
                    if (newClient) {
                        await API.addMasterData({ new_client: newClient });
                        selectedClient = newClient;
                        document.getElementById('client').value = newClient;
                        document.getElementById('newClient').value = '';
                    }

                    const newProductName = document.getElementById('newProductName').value.trim();
                    if (newProductName) {
                        const newCategory = document.getElementById('newProductCategory').value.trim() || 'Uncategorized';
                        await API.addMasterData({ new_product: { name: newProductName, category: newCategory } });
                        selectedProduct = newProductName;
                        document.getElementById('product').value = newProductName;
                        UI.updateProductDefaults();
                        document.getElementById('newProductName').value = '';
                        document.getElementById('newProductCategory').value = '';
                    }

                    // --- DETAILED FRONTEND VALIDATION LOGIC ---
                    const section = document.getElementById('section').value;
                    const isBrokerOrMining = (section === 'Broker' || section === 'Mining');
                    const warnings = new Set(); // Use a Set to avoid duplicate messages

                    // Get PMT values already converted to USD for validation and submission.
                    const { pmtQ1, pmtQ2, pmtQ3, pmtQ4 } = UI._getQuarterlyPmtsInUSD();

                    const gm_percent = parseFloat(document.getElementById('gmPercent').value);
                    const profitPerTon_USD = UI._getProfitPerTonInUSD();

                    const monthQuarterMap = {Jan:'Q1', Feb:'Q1', Mar:'Q1', Apr:'Q2', May:'Q2', Jun:'Q2', Jul:'Q3', Aug:'Q3', Sep:'Q3', Oct:'Q4', Nov:'Q4', Dec:'Q4'};
                    
                    // The pmtMap now uses the USD-converted values.
                    const pmtMap = {Q1: pmtQ1, Q2: pmtQ2, Q3: pmtQ3, Q4: pmtQ4};

                    let hasQuantity = false;
                    for (const monthName of ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']) {
                        const qty = parseFloat(document.getElementById(`qty${monthName}`).value);
                        if (!isNaN(qty) && qty !== 0) {
                            hasQuantity = true;
                            if (isBrokerOrMining) {
                                if (isNaN(profitPerTon_USD) || profitPerTon_USD === 0) {
                                    warnings.add('Profit per Ton cannot be 0.');
                                }
                            } else {
                                const quarter = monthQuarterMap[monthName];
                                const pmtForMonth = pmtMap[quarter]; // This is now a USD value
                                if (isNaN(pmtForMonth) || pmtForMonth === 0) {
                                    warnings.add(`PMT for ${quarter} (covering ${monthName}) cannot be 0.`);
                                }
                                
                                if (isNaN(gm_percent) || gm_percent === 0) {
                                    warnings.add('Annual GP % cannot be 0.');
                                }
                            }
                        }
                    }
                    
                    if (!hasQuantity) {
                         warnings.add('At least one month must have a quantity.');
                    }

                    if (warnings.size > 0) {
                        Utils.showNotification(Array.from(warnings).join('<br>'), 'warning');
                        return; // Stop execution
                    }
                    // --- END OF VALIDATION ---

                    const baseData = {
                        business_unit: document.getElementById('businessUnit').value,
                        section: section, client: selectedClient, product: selectedProduct,
                        category: AppState.masters.productMap[selectedProduct] || 'Uncategorized', 
                        sector: document.getElementById('sector').value
                    };
                    
                    const entriesToAdd = [];
                    for (const monthName of ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']) {
                        const qtyInput = document.getElementById(`qty${monthName}`);
                        if (qtyInput.value.trim() !== '') {
                            const qty = parseFloat(qtyInput.value);
                            if (qty === 0) continue; // Skip zero-quantity entries, already validated

                            const isBooked = document.getElementById(`check${monthName}`).checked;
                            if (isBrokerOrMining) {
                                entriesToAdd.push({ ...baseData, month_name: monthName, qty, pmt: 0, gm_percent: 0, profit_per_ton: profitPerTon_USD, booked: isBooked ? "Yes" : "No" });
                            } else {
                                const quarter = monthQuarterMap[monthName];
                                const pmtForMonth = pmtMap[quarter];
                                entriesToAdd.push({ ...baseData, month_name: monthName, qty, pmt: pmtForMonth, gm_percent, profit_per_ton: 0, booked: isBooked ? "Yes" : "No" });
                            }
                        }
                    }
                    
                    let entriesAdded = 0;
                    for (const entryData of entriesToAdd) {
                        await API.addEntry(entryData);
                        entriesAdded++;
                    }
                    
                    if (entriesAdded > 0) {
                        Utils.showNotification(`Successfully added ${entriesAdded} monthly entries`, 'success');
                        UI.updateStats();
                        UI.initializeFilters();
                        this.resetForm();
                    }

                } catch (error) {
                    console.error("Failed to add new entry:", error);
                } finally {
                    Utils.showLoading(false);
                }
            });
            btnAddEntry.dataset.listenerAttached = 'true';
        }
        
        const btnResetForm = document.getElementById('btnResetForm');
        if (btnResetForm && !btnResetForm.dataset.listenerAttached) {
            btnResetForm.addEventListener('click', this.resetForm);
            btnResetForm.dataset.listenerAttached = 'true';
        }
    },
    
    setupManageHandlers() {
        const btnRecalculate = document.getElementById('btnRecalculate');
        if (btnRecalculate && !btnRecalculate.dataset.listenerAttached) {
            btnRecalculate.addEventListener('click', async () => {
                await API.recalculate();
                UI.updateStats();
                UI.renderDataTable();
            });
            btnRecalculate.dataset.listenerAttached = 'true';
        }
        
        const btnDeleteSelected = document.getElementById('btnDeleteSelected');
        if (btnDeleteSelected && !btnDeleteSelected.dataset.listenerAttached) {
            btnDeleteSelected.addEventListener('click', async () => {
                const selectedIds = Array.from(document.querySelectorAll('.entry-checkbox:checked')).map(cb => cb.dataset.id);
                if (selectedIds.length === 0) {
                    Utils.showNotification('No entries selected for deletion', 'warning');
                    return;
                }
                if (confirm(`Delete ${selectedIds.length} selected entries?`)) {
                    await API.commitChanges([], selectedIds);
                    UI.updateStats();
                    UI.initializeFilters();
                    UI.renderDataTable();
                }
            });
            btnDeleteSelected.dataset.listenerAttached = 'true';
        }
    },
    
    setupFileHandlers() {
        const btnUploadMasters = document.getElementById('btnUploadMasters');
        if (btnUploadMasters && !btnUploadMasters.dataset.listenerAttached) {
            btnUploadMasters.addEventListener('click', async () => {
                const fileInput = document.getElementById('mastersFile');
                const file = fileInput.files[0];
                if (!file) { Utils.showNotification('Please select a masters file', 'warning'); return; }
                const formData = new FormData();
                formData.append('file', file);
                try {
                    Utils.showLoading(true);
                    const response = await fetch('/api/load_masters', { method: 'POST', body: formData });
                    const data = await response.json();
                    if (data.error || data.status === 'error') {
                        Utils.showNotification(data.error || data.message, 'error');
                    } else {
                        AppState.masters.clients = data.masters.clients || [];
                        AppState.masters.products = data.masters.products || [];
                        rebuildMasterLookups();
                        UI.initializeForm();
                        UI.updateMasterDataDisplay();
                        Utils.showNotification('Master data uploaded successfully', 'success');
                    }
                } catch (error) { Utils.showNotification('Failed to upload master data', 'error'); } 
                finally { Utils.showLoading(false); }
            });
            btnUploadMasters.dataset.listenerAttached = 'true';
        }
        
        const btnUploadBudget = document.getElementById('btnUploadBudget');
        if (btnUploadBudget && !btnUploadBudget.dataset.listenerAttached) {
            btnUploadBudget.addEventListener('click', async () => {
                const file = document.getElementById('budgetFile').files[0];
                const sheetName = document.getElementById('sheetName').value || 'Budget';
                if (!file) { Utils.showNotification('Please select a budget file', 'warning'); return; }
                const formData = new FormData();
                formData.append('file', file);
                formData.append('sheet', sheetName);
                try {
                    Utils.showLoading(true);
                    const response = await fetch('/api/load_budget', { method: 'POST', body: formData });
                    const data = await response.json();
                    if (data.error) Utils.showNotification(data.error, 'error');
                    else {
                        AppState.entries = data.entries || [];
                        UI.updateStats();
                        UI.initializeFilters();
                        UI.renderDataTable();
                        Utils.showNotification('Budget file loaded successfully', 'success');
                        if(window.ClientFileHandler) window.ClientFileHandler.resetFileHandle();
                    }
                } catch (error) { Utils.showNotification('Failed to load budget file', 'error'); } 
                finally { Utils.showLoading(false); }
            });
            btnUploadBudget.dataset.listenerAttached = 'true';
        }
        
        const btnRemoveFile = document.getElementById('btnRemoveFile');
        if (btnRemoveFile && !btnRemoveFile.dataset.listenerAttached) {
            btnRemoveFile.addEventListener('click', async () => {
                if (confirm('Are you sure you want to clear all data in your session?')) {
                    try {
                        Utils.showLoading(true);
                        const data = await API._fetchWithSession('/api/clear_data', { method: 'POST' });
                        if (data.status === 'success') {
                            AppState.entries = [];
                            UI.updateStats();
                            UI.initializeFilters();
                            UI.renderDataTable();
                            Utils.showNotification('All session data cleared.', 'success');
                            document.getElementById('budgetFile').value = '';
                            if(window.ClientFileHandler) window.ClientFileHandler.resetFileHandle();
                        } else {
                            Utils.showNotification(data.message || 'Failed to clear data.', 'error');
                        }
                    } catch (error) { Utils.showNotification('An error occurred.', 'error'); } 
                    finally { Utils.showLoading(false); }
                }
            });
            btnRemoveFile.dataset.listenerAttached = 'true';
        }
    },
    
    resetForm() {
        ['pmtQ1', 'pmtQ2', 'pmtQ3', 'pmtQ4', 'gmPercent', 'profitPerTon'].forEach(id => document.getElementById(id).value = '');
        ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].forEach(m => {
            document.getElementById(`qty${m}`).value = '';
            document.getElementById(`check${m}`).checked = false;
        });
        document.getElementById('newClient').value = '';
        document.getElementById('newProductName').value = '';
        document.getElementById('newProductCategory').value = '';
        UI.updateProductDefaults();
    }
};

// Application Initialization
async function initializeApp() {
    try {
        
        window.addEventListener('beforeunload', (event) => { if (AppState.entries.length > 0) { event.preventDefault(); event.returnValue = ''; return ''; } });
        
        const logoutButton = document.getElementById('logoutButton');
        if (logoutButton) {
            logoutButton.addEventListener('click', function(event) {
                event.preventDefault(); 
                if (confirm('Are you sure you want to sign out?')) {
                    window.location.href = this.href;
                }
            });
        }

        const dataTableBody = document.getElementById('dataTableBody');
        if (dataTableBody) {
            dataTableBody.addEventListener('dblclick', (event) => {
                const cell = event.target.closest('.editable-cell');
                if (cell) {
                    UI.makeCellEditable(cell);
                }
            });
        }
        
        await API.loadState();
        UI.initializeTabs();
        UI.initializeForm();
        UI.updateStats();
        UI.initializeFilters();
        UI.updateMasterDataDisplay();
        EventHandlers.setupPmtCurrencyHandlers();
        EventHandlers.setupProfitCurrencyHandlers();
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
    let currentFileHandle = null;

    const writeFile = async (fileHandle) => {
        try {
            Utils.showLoading(true);
            const response = await fetch('/api/download_current');
            if (!response.ok) throw new Error('Failed to fetch file data from server.');
            const blob = await response.blob();
            const writable = await fileHandle.createWritable();
            await writable.write(blob);
            await writable.close();
        } catch (err) {
            console.error('Error writing to file:', err);
            Utils.showNotification('Failed to write to file.', 'error');
            throw err;
        } finally {
            Utils.showLoading(false);
        }
    };
    
    const handleSaveAs = async () => {
        const fileOptions = {
            suggestedName: `Budget_${new Date().toISOString().slice(0,10)}.xlsx`,
            types: [{ description: 'Excel Workbook', accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] } }],
        };
        try {
            const handle = await window.showSaveFilePicker(fileOptions);
            await writeFile(handle);
            currentFileHandle = handle;
            Utils.showNotification(`File saved as "${handle.name}"`, 'success');
        } catch (err) {
            if (err.name !== 'AbortError') { Utils.showNotification('Could not save the file.', 'error'); }
        }
    };
    
    const handleSave = async () => {
        if (currentFileHandle) {
            try {
                await writeFile(currentFileHandle);
                Utils.showNotification(`File "${currentFileHandle.name}" saved successfully.`, 'success');
            } catch (err) {}
        } else {
            await handleSaveAs();
        }
    };

    const fallbackDownload = () => {
        const link = document.createElement('a');
        link.href = '/api/download_current';
        link.download = `Budget_Export.xlsx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };
    
    window.ClientFileHandler = { resetFileHandle: () => { currentFileHandle = null; console.log("File handle has been reset."); } };

    const hasFSApi = 'showSaveFilePicker' in window;
    document.getElementById('btnSave').addEventListener('click', async (e) => { e.preventDefault(); if (hasFSApi) { await handleSave(); } else { fallbackDownload(); } });
    document.getElementById('btnSaveAs').addEventListener('click', async (e) => { e.preventDefault(); if (hasFSApi) { await handleSaveAs(); } else { fallbackDownload(); } });
});

        // Initialize Lucide icons
        lucide.createIcons();
        
        // Application State
        const AppState = {
            entries: [],
            masters: {
                clients: [],
                products: [],
                productMap: {},
                pmtMap: {},
                gmMap: {}
            },
            filters: {
                businessUnit: '',
                section: '',
                client: '',
                product: '',
                search: ''
            },
            selectedEntries: new Set()
        };
        let sessionId = null;

        function rebuildMasterLookups() {
            // Reset the maps to ensure they are clean from old data
            AppState.masters.productMap = {};
            AppState.masters.pmtMap = {};
            AppState.masters.gmMap = {};

            (AppState.masters.products || []).forEach(product => {
                const p = product?.Product;
                if (!p) return; // Skip if product name is missing

                AppState.masters.productMap[p] = product?.Category ?? '';

                const pmtVal = parseFloat(product?.Default_PMT);
                const gmVal = parseFloat(product?.['Default_GM%']);

                if (!isNaN(pmtVal)) {
                    AppState.masters.pmtMap[p] = pmtVal;
                }
                if (!isNaN(gmVal)) {
                    AppState.masters.gmMap[p] = gmVal;
                }
            });
            console.log("Master lookup maps have been rebuilt.");
        }

        // Utility Functions
        const Utils = {
            formatCurrency: (amount) => {
                return new Intl.NumberFormat('en-JO', {
                    style: 'currency',
                    currency: 'JOD',
                    minimumFractionDigits: 2
                }).format(amount || 0);
            },
            
            formatNumber: (num, decimals = 2) => {
                // Return a default formatted string for invalid inputs
                if (isNaN(num) || num === null) {
                    return (0).toFixed(decimals);
                }
                // Use the Internationalization API for robust number formatting
                return new Intl.NumberFormat('en-US', {
                    minimumFractionDigits: decimals,
                    maximumFractionDigits: decimals
                }).format(num);
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
                
                const icon = type === 'success' ? 'check-circle' : 
                           type === 'error' ? 'x-circle' : 
                           type === 'warning' ? 'alert-triangle' : 'info';
                
                const color = type === 'success' ? 'text-green-600' : 
                            type === 'error' ? 'text-red-600' : 
                            type === 'warning' ? 'text-yellow-600' : 'text-blue-600';
                
                notification.innerHTML = `
                    <div class="flex items-start">
                        <i data-lucide="${icon}" class="w-5 h-5 ${color} mr-3 flex-shrink-0 mt-1"></i>
                        <div class="text-gray-800">${message}</div>
                        <button class="ml-auto text-gray-400 hover:text-gray-600" onclick="this.parentElement.parentElement.remove()">
                            <i data-lucide="x" class="w-4 h-4"></i>
                        </button>
                    </div>
                `;
                
                container.appendChild(notification);
                lucide.createIcons();
                
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, 7000); // Increased timeout for potentially longer messages
            },
            
            showLoading: (show = true) => {
                document.getElementById('loadingOverlay').classList.toggle('hidden', !show);
            }
        };

        // API Functions
        const API = {
            // Helper function to include the session ID in all API calls
            async _fetchWithSession(url, options = {}) {
                const headers = {
                    'Content-Type': 'application/json',
                    ...options.headers,
                };

                // Add the session ID to the header if we have one
                if (sessionId) {
                    headers['X-Session-ID'] = sessionId;
                }

                const response = await fetch(url, { ...options, headers });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || errorData.message || 'An API error occurred');
                }
                return response.json();
            },

            async loadState() {
                try {
                    // The first call to loadState will not have a session ID.
                    // The server will create a new session and return the ID.
                    const data = await this._fetchWithSession('/api/state');
                    
                    sessionId = data.session_id; // <-- CRITICAL: Store the session ID
                    console.log("Obtained session ID:", sessionId);

                    AppState.entries = data.entries || [];
                    AppState.masters.clients = data.masters?.clients || [];
                    AppState.masters.products = data.masters?.products || [];

                    // Build lookup maps
                    rebuildMasterLookups();

                    return data;
                } catch (error) {
                    Utils.showNotification('Failed to load application state: ' + error.message, 'error');
                    throw error;
                }
            },

            async addEntry(entryData) {
                try {
                    Utils.showLoading?.(true);
                    const data = await this._fetchWithSession('/api/add', {
                        method: 'POST',
                        body: JSON.stringify(entryData)
                    });
                    AppState.entries = data.entries || [];
                    return data;
                } catch (error) {
                    Utils.showNotification('Failed to add entry: ' + error.message, 'error');
                    throw error;
                } finally {
                    Utils.showLoading?.(false);
                }
            },

            async commitChanges(editedRows, deleteIds) {
                try {
                    Utils.showLoading?.(true);
                    const data = await this._fetchWithSession('/api/commit', {
                        method: 'POST',
                        body: JSON.stringify({ editedRows, deleteIds })
                    });
                    AppState.entries = data.entries || [];
                    Utils.showNotification('Changes saved successfully', 'success');
                    return data;
                } catch (error) {
                    Utils.showNotification('Failed to save changes: ' + error.message, 'error');
                    throw error;
                } finally {
                    Utils.showLoading?.(false);
                }
            },

            async recalculate() {
                try {
                    Utils.showLoading?.(true);
                    const data = await this._fetchWithSession('/api/recalc', { method: 'POST' });
                    AppState.entries = data.entries || [];
                    Utils.showNotification('Data recalculated successfully', 'success');
                    return data;
                } catch (error) {
                    Utils.showNotification('Failed to recalculate data: ' + error.message, 'error');
                    throw error;
                } finally {
                    Utils.showLoading?.(false);
                }
            }
        };

        // UI Components
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
                        button.classList.remove('border-transparent', 'text-gray-500');
                        button.classList.add('border-primary-500', 'text-primary-600');
                        
                        tabPanels.forEach(panel => panel.classList.add('hidden'));
                        document.getElementById(targetId).classList.remove('hidden');
                        
                        if (targetId === 'panelManage') {
                            this.renderDataTable();
                        }
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
                if (productField) {
                    productField.addEventListener('change', this.updateProductDefaults.bind(this));
                }
                
                ['pmtQ1', 'pmtQ2', 'pmtQ3', 'pmtQ4', 'gmPercent'].forEach(id => {
                    const element = document.getElementById(id);
                    if (element) {
                        element.addEventListener('input', this.updatePreview.bind(this));
                    }
                });
                
                ['qtyJan', 'qtyFeb', 'qtyMar', 'qtyApr', 'qtyMay', 'qtyJun',
                 'qtyJul', 'qtyAug', 'qtySep', 'qtyOct', 'qtyNov', 'qtyDec'].forEach(id => {
                    const element = document.getElementById(id);
                    if (element) {
                        element.addEventListener('input', this.updatePreview.bind(this));
                    }
                });
                
                this.updateProductDefaults();
                this.updatePreview();
            },
            
            updateProductDefaults() {
                const productField = document.getElementById('product');
                const categoryField = document.getElementById('categoryDisplay');
                
                if (!productField || !categoryField) return;
                
                const product = productField.value;
                const category = AppState.masters.productMap[product] || 'Unknown';
                // Get the defaults. They will be a number or undefined.
                const defaultPMT = AppState.masters.pmtMap[product];
                const defaultGM = AppState.masters.gmMap[product];
                
                categoryField.value = category;
                
                ['pmtQ1', 'pmtQ2', 'pmtQ3', 'pmtQ4'].forEach(id => {
                    const field = document.getElementById(id);
                    if (field && !field.value) {
                         // Use the nullish coalescing operator '??'
                        // It sets the value to '' ONLY if defaultPMT is null or undefined
                        field.value = defaultPMT ?? '';
                    }
                });
                
                const gmField = document.getElementById('gmPercent');
                if (gmField && !gmField.value) {
                    gmField.value = defaultGM ?? '';
                }
                
                this.updatePreview();
            },
            
            updatePreview() {
                const pmtQ1 = parseFloat(document.getElementById('pmtQ1')?.value) || 0;
                const pmtQ2 = parseFloat(document.getElementById('pmtQ2')?.value) || 0;
                const pmtQ3 = parseFloat(document.getElementById('pmtQ3')?.value) || 0;
                const pmtQ4 = parseFloat(document.getElementById('pmtQ4')?.value) || 0;
                const gm = parseFloat(document.getElementById('gmPercent')?.value) || 0;
                
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
                
                const salesQ1 = (qtyJan + qtyFeb + qtyMar) * pmtQ1;
                const salesQ2 = (qtyApr + qtyMay + qtyJun) * pmtQ2;
                const salesQ3 = (qtyJul + qtyAug + qtySep) * pmtQ3;
                const salesQ4 = (qtyOct + qtyNov + qtyDec) * pmtQ4;
                const totalSales = salesQ1 + salesQ2 + salesQ3 + salesQ4;
                
                const gmFactor = gm / 100;
                const gpQ1 = salesQ1 * gmFactor;
                const gpQ2 = salesQ2 * gmFactor;
                const gpQ3 = salesQ3 * gmFactor;
                const gpQ4 = salesQ4 * gmFactor;
                const totalGP = gpQ1 + gpQ2 + gpQ3 + gpQ4;
                
                const u = Utils.formatNumber;
                document.getElementById('previewQ1Sales').textContent = u(salesQ1, 0) + ' JOD';
                document.getElementById('previewQ2Sales').textContent = u(salesQ2, 0) + ' JOD';
                document.getElementById('previewQ3Sales').textContent = u(salesQ3, 0) + ' JOD';
                document.getElementById('previewQ4Sales').textContent = u(salesQ4, 0) + ' JOD';
                document.getElementById('previewTotalSales').textContent = u(totalSales, 0) + ' JOD';
                document.getElementById('previewQ1GP').textContent = u(gpQ1, 0) + ' JOD';
                document.getElementById('previewQ2GP').textContent = u(gpQ2, 0) + ' JOD';
                document.getElementById('previewQ3GP').textContent = u(gpQ3, 0) + ' JOD';
                document.getElementById('previewQ4GP').textContent = u(gpQ4, 0) + ' JOD';
                document.getElementById('previewTotalGP').textContent = u(totalGP, 0) + ' JOD';
            },
            
            updateStats() {
                const totalEntries = AppState.entries.length;
                const totalSales = AppState.entries.reduce((sum, entry) => sum + (parseFloat(entry['Sales (JOD)']) || 0), 0);
                const totalGP = AppState.entries.reduce((sum, entry) => sum + (parseFloat(entry['GP (JOD)']) || 0), 0);
                const avgGM = totalSales > 0 ? (totalGP / totalSales) * 100 : 0;
                
                document.getElementById('totalEntries').textContent = totalEntries;
                document.getElementById('totalSales').textContent = Utils.formatNumber(totalSales, 0) + ' JOD';
                document.getElementById('totalGP').textContent = Utils.formatNumber(totalGP, 0) + ' JOD';
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
                    document.getElementById(id).addEventListener('input', this.renderDataTable.bind(this));
                });
            },
            
            populateFilter(selectId, options, defaultText) {
                const select = document.getElementById(selectId);
                select.innerHTML = `<option value="">${defaultText}</option>`;
                options.forEach(option => {
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
                    row.innerHTML = `
                        <td class="px-4 py-3"><input type="checkbox" class="entry-checkbox rounded" data-id="${entry._rid}"></td>
                        <td class="px-4 py-3 text-sm">${entry['Business Unit'] || ''}</td>
                        <td class="px-4 py-3 text-sm">${entry.Section || ''}</td>
                        <td class="px-4 py-3 text-sm">${entry.Client || ''}</td>
                        <td class="px-4 py-3 text-sm">${entry.Product || ''}</td>
                        <td class="px-4 py-3 text-sm">${Utils.monthNumToName(entry.Month)}</td>
                        <td class="px-4 py-3 text-sm text-right">${u(entry['Qty (MT)'])}</td>
                        <td class="px-4 py-3 text-sm text-right">${u(entry['PMT (JOD)'])}</td>
                        <td class="px-4 py-3 text-sm text-right">${u(entry['GM %'], 1)}%</td>
                        <td class="px-4 py-3 text-sm text-green-600 font-medium text-right">${u(entry['Sales (JOD)'], 0)}</td>
                        <td class="px-4 py-3 text-sm text-blue-600 font-medium text-right">${u(entry['GP (JOD)'], 0)}</td>
                        <td class="px-4 py-3 text-sm"><span class="px-2 py-1 text-xs rounded-full ${entry.Booked === 'Yes' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">${entry.Booked || 'No'}</span></td>
                    `;
                    tbody.appendChild(row);
                });
                
                const filteredSales = filteredEntries.reduce((sum, entry) => sum + (parseFloat(entry['Sales (JOD)']) || 0), 0);
                const filteredGP = filteredEntries.reduce((sum, entry) => sum + (parseFloat(entry['GP (JOD)']) || 0), 0);
                
                document.getElementById('filteredCount').textContent = filteredEntries.length;
                document.getElementById('filteredSales').textContent = Utils.formatNumber(filteredSales, 0) + ' JOD';
                document.getElementById('filteredGP').textContent = Utils.formatNumber(filteredGP, 0) + ' JOD';
                
                const selectAllCheckbox = document.getElementById('selectAll');
                if (selectAllCheckbox) {
                    selectAllCheckbox.addEventListener('change', (e) => {
                        document.querySelectorAll('.entry-checkbox').forEach(cb => cb.checked = e.target.checked);
                    });
                }
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
            setupFormHandlers() {
                document.getElementById('btnAddEntry').addEventListener('click', async () => {
                    let selectedClient = document.getElementById('client').value;
                    const newClient = document.getElementById('newClient').value.trim();
                    if (newClient && !AppState.masters.clients.includes(newClient)) {
                        AppState.masters.clients.push(newClient);
                        selectedClient = newClient;
                        document.getElementById('newClient').value = '';
                        UI.initializeForm();
                        document.getElementById('client').value = selectedClient;
                    }
                    
                    const baseData = {
                        business_unit: document.getElementById('businessUnit').value,
                        section: document.getElementById('section').value,
                        client: selectedClient,
                        product: document.getElementById('product').value,
                        gm_percent: parseFloat(document.getElementById('gmPercent').value),
                        sector: document.getElementById('sector').value
                    };
                    
                    const pmtQ1 = parseFloat(document.getElementById('pmtQ1').value);
                    const pmtQ2 = parseFloat(document.getElementById('pmtQ2').value);
                    const pmtQ3 = parseFloat(document.getElementById('pmtQ3').value);
                    const pmtQ4 = parseFloat(document.getElementById('pmtQ4').value);
                    const monthQuarterMap = {Jan:{q:'Q1',p:pmtQ1},Feb:{q:'Q1',p:pmtQ1},Mar:{q:'Q1',p:pmtQ1},Apr:{q:'Q2',p:pmtQ2},May:{q:'Q2',p:pmtQ2},Jun:{q:'Q2',p:pmtQ2},Jul:{q:'Q3',p:pmtQ3},Aug:{q:'Q3',p:pmtQ3},Sep:{q:'Q3',p:pmtQ3},Oct:{q:'Q4',p:pmtQ4},Nov:{q:'Q4',p:pmtQ4},Dec:{q:'Q4',p:pmtQ4}};

                    let entriesToAdd = [];
                    for (const [monthName, info] of Object.entries(monthQuarterMap)) {
                        const qtyInput = document.getElementById(`qty${monthName}`);
                        if (qtyInput.value.trim() !== '') { // Only process months with entered quantities
                            const qty = parseFloat(qtyInput.value);
                            const isBooked = document.getElementById(`check${monthName}`).checked;
                            entriesToAdd.push({ ...baseData, month_name: monthName, qty: qty, pmt: info.p, booked: isBooked ? "Yes" : "No" });
                        }
                    }

                    // --- Start Validation ---
                    if (entriesToAdd.length === 0) {
                        Utils.showNotification('No quantities entered to add.', 'info');
                        return;
                    }
                    const warnings = [];
                    if (isNaN(baseData.gm_percent) || baseData.gm_percent === 0) {
                        warnings.push("Annual GM % cannot be 0.");
                    }
                    
                    entriesToAdd.forEach(entry => {
                        const month = entry.month_name;
                        const quarter = monthQuarterMap[month].q;
                        
                        if (isNaN(entry.qty) || entry.qty === 0) {
                             warnings.push(`Quantity for ${month} cannot be 0.`);
                        }
                        if (isNaN(entry.pmt) || entry.pmt === 0) {
                             warnings.push(`PMT for ${quarter} (covering ${month}) cannot be 0.`);
                        }
                    });

                    if (warnings.length > 0) {
                        Utils.showNotification(warnings.join('<br>'), 'warning');
                        return; // Stop execution if there are validation errors
                    }
                    // --- End Validation ---

                    let entriesAdded = 0;
                    for (const entryData of entriesToAdd) {
                        try {
                           await API.addEntry(entryData);
                           entriesAdded++;
                        } catch (e) {
                           // Error is already shown by API handler, so just break the loop
                           break;
                        }
                    }
                    
                    if (entriesAdded > 0) {
                        Utils.showNotification(`Successfully added ${entriesAdded} monthly entries`, 'success');
                        UI.updateStats();
                        UI.initializeFilters();
                        this.resetForm();
                    }
                });
                
                document.getElementById('btnResetForm').addEventListener('click', this.resetForm);
            },
            
            setupManageHandlers() {
                document.getElementById('btnRecalculate').addEventListener('click', async () => {
                    await API.recalculate();
                    UI.updateStats();
                    UI.renderDataTable();
                });
                
                document.getElementById('btnDeleteSelected').addEventListener('click', async () => {
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
            },
            
            setupFileHandlers() {
                document.getElementById('btnUploadMasters').addEventListener('click', async () => {
                    const fileInput = document.getElementById('mastersFile');
                    const file = fileInput.files[0];
                    if (!file) { Utils.showNotification('Please select a masters file', 'warning'); return; }
                    
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    try {
                        Utils.showLoading(true);
                        const response = await fetch('/api/load_masters', { method: 'POST', body: formData, headers: { 'X-Session-ID': sessionId } });
                        const data = await response.json();
                        
                        if (data.error) Utils.showNotification(data.error, 'error');
                        else {
                            AppState.masters.clients = data.masters.clients || [];
                            AppState.masters.products = data.masters.products || [];
                            
                            // Rebuild the lookup maps with the new data
                            rebuildMasterLookups();
                            
                            UI.initializeForm();
                            UI.updateMasterDataDisplay();
                            Utils.showNotification('Master data uploaded to your session', 'success');
                        }
                    } catch (error) { Utils.showNotification('Failed to upload master data', 'error'); } 
                    finally { Utils.showLoading(false); }
                });
                
                document.getElementById('btnUploadBudget').addEventListener('click', async () => {
                    const file = document.getElementById('budgetFile').files[0];
                    const sheetName = document.getElementById('sheetName').value || 'Budget';
                    if (!file) { Utils.showNotification('Please select a budget file', 'warning'); return; }
                    
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('sheet', sheetName);
                    
                    try {
                        Utils.showLoading(true);
                        const response = await fetch('/api/load_budget', { method: 'POST', body: formData, headers: { 'X-Session-ID': sessionId } });
                        const data = await response.json();
                        
                        if (data.error) Utils.showNotification(data.error, 'error');
                        else {
                            AppState.entries = data.entries || [];
                            UI.updateStats();
                            UI.initializeFilters();
                            UI.renderDataTable();
                            Utils.showNotification('Budget file loaded into your session', 'success');
                            if(window.ClientFileHandler) window.ClientFileHandler.resetFileHandle();
                        }
                    } catch (error) { Utils.showNotification('Failed to load budget file', 'error'); } 
                    finally { Utils.showLoading(false); }
                });
                
                document.getElementById('btnRemoveFile').addEventListener('click', async () => {
                    if (confirm('Are you sure you want to clear all data in your session?')) {
                        try {
                            Utils.showLoading(true);
                            const response = await fetch('/api/clear_data', { method: 'POST', headers: { 'X-Session-ID': sessionId } });
                            const data = await response.json();
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
            },
            
            resetForm() {
                ['pmtQ1', 'pmtQ2', 'pmtQ3', 'pmtQ4', 'gmPercent'].forEach(id => document.getElementById(id).value = '');
                ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].forEach(m => {
                    document.getElementById(`qty${m}`).value = '';
                    document.getElementById(`check${m}`).checked = false;
                });
                document.getElementById('newClient').value = '';
                UI.updateProductDefaults();
            }
        };

        // Application Initialization
        async function initializeApp() {
            try {
                document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', {
                    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                });
                window.addEventListener('beforeunload', (event) => {
                    if (AppState.entries.length > 0) { event.preventDefault(); event.returnValue = ''; return ''; }
                });
                await API.loadState();
                UI.initializeTabs();
                UI.initializeForm();
                UI.updateStats();
                UI.initializeFilters();
                UI.updateMasterDataDisplay();
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
                    const response = await fetch('/api/download_current', { headers: { 'X-Session-ID': sessionId }});
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
                    types: [{
                        description: 'Excel Workbook',
                        accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] },
                    }],
                };
                try {
                    const handle = await window.showSaveFilePicker(fileOptions);
                    await writeFile(handle);
                    currentFileHandle = handle;
                    Utils.showNotification(`File saved as "${handle.name}"`, 'success');
                } catch (err) {
                    if (err.name !== 'AbortError') {
                        Utils.showNotification('Could not save the file.', 'error');
                    }
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
                link.href = '/api/download_current'; // This endpoint needs to be session aware on the backend now.
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
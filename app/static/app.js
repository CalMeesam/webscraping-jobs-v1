/**
 * Adaptive Career Job Extraction Engine Frontend Client
 */

let currentData = null;
let customersData = [];
let editingCustomerId = null;  // Track which customer is being edited

const PRESETS = {
    dell: "https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers/jobs?mode=location",
    broadcom: "https://broadcom.wd1.myworkdayjobs.com/External_Career",
    figma: "https://boards.greenhouse.io/figma",
    cisco: "https://careers.cisco.com/global/en/search-results",
    exl: "https://fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/jobs?location=India",
    hpe: "https://careers.hpe.com/us/en/search-results"
};

// ============================================
// CUSTOMER MANAGEMENT
// ============================================

async function loadCustomers() {
    try {
        const response = await fetch('/customers');
        if (!response.ok) {
            throw new Error('Failed to load customers');
        }
        const data = await response.json();
        customersData = data.customers || [];
        renderCustomerGrid(customersData);
    } catch (err) {
        console.error('Error loading customers:', err);
        document.getElementById('customerGrid').innerHTML = `
            <div class="error-state">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>Failed to load customers</p>
            </div>
        `;
    }
}

function renderCustomerGrid(customers) {
    const grid = document.getElementById('customerGrid');
    
    if (!customers || customers.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-inbox"></i>
                <p>No customers registered yet</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = customers.map(customer => {
        const hasMultipleLinks = customer.career_links && customer.career_links.length > 1;
        
        return `
            <div class="customer-card" data-customer-id="${customer.customer_id}">
                <div class="customer-header">
                    <div class="customer-icon">
                        <i class="fa-solid fa-building"></i>
                    </div>
                    <div class="customer-info">
                        <h4>${customer.customer_name}</h4>
                        <span class="customer-meta">
                            <i class="fa-solid fa-user"></i> ${customer.director}
                        </span>
                    </div>
                    <button type="button" class="btn-edit-customer" onclick="openEditCustomerModal('${customer.customer_id}')" title="Edit customer">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </button>
                </div>
                ${hasMultipleLinks 
                    ? `<div class="customer-links-multi">
                        ${customer.career_links.map((link, idx) => `
                            <button type="button" class="link-btn" onclick="selectCustomerLink('${customer.customer_id}', ${idx})">
                                <i class="fa-solid fa-link"></i> ${link.label}
                            </button>
                        `).join('')}
                       </div>`
                    : `<button type="button" class="customer-select-btn" onclick="selectCustomerLink('${customer.customer_id}', 0)">
                        <i class="fa-solid fa-arrow-right"></i> Select
                       </button>`
                }
            </div>
        `;
    }).join('');
}

function selectCustomerLink(customerId, linkIndex) {
    const customer = customersData.find(c => c.customer_id === customerId);
    if (!customer || !customer.career_links || !customer.career_links[linkIndex]) {
        showToast('Customer link not found', 'error');
        return;
    }
    
    const link = customer.career_links[linkIndex];
    document.getElementById('urlInput').value = link.url;
    showToast(`Loaded ${customer.customer_name} - ${link.label}`);
    
    // Scroll to the form
    document.getElementById('urlInput').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ============================================
// ADD CUSTOMER MODAL
// ============================================

function openAddCustomerModal() {
    // Reset edit mode
    editingCustomerId = null;
    
    // Reset modal title for add mode
    document.querySelector('#addCustomerModal .modal-header h2').innerHTML = 
        '<i class="fa-solid fa-building-circle-arrow-right"></i> Add New Customer';
    document.querySelector('#addCustomerModal .modal-meta').textContent = 
        'Register a new customer career portal';
    document.querySelector('#addCustomerModal button[type="submit"]').innerHTML = 
        '<i class="fa-solid fa-check"></i> Add Customer';
    
    document.getElementById('addCustomerModal').style.display = 'flex';
    document.getElementById('addCustomerError').style.display = 'none';
}

function closeAddCustomerModal() {
    document.getElementById('addCustomerModal').style.display = 'none';
    document.getElementById('addCustomerForm').reset();
    editingCustomerId = null;  // Clear edit mode
    
    // Reset modal title
    document.querySelector('#addCustomerModal .modal-header h2').innerHTML = 
        '<i class="fa-solid fa-building-circle-arrow-right"></i> Add New Customer';
    document.querySelector('#addCustomerModal .modal-meta').textContent = 
        'Register a new customer career portal';
    document.querySelector('#addCustomerModal button[type="submit"]').innerHTML = 
        '<i class="fa-solid fa-check"></i> Add Customer';
    
    // Reset to single BizDev and Career Link inputs
    document.getElementById('bizdevContainer').innerHTML = `
        <div class="bizdev-input-row">
            <input type="text" class="bizdev-input" placeholder="Enter name" required>
            <button type="button" class="btn-icon-remove" onclick="removeBizDevInput(this)" disabled>
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `;
    
    document.getElementById('careerLinksContainer').innerHTML = `
        <div class="career-link-row">
            <input type="text" class="link-label-input" placeholder="Label (e.g. Main Portal)" required>
            <input type="url" class="link-url-input" placeholder="https://example.com/careers" required>
            <button type="button" class="btn-icon-remove" onclick="removeCareerLinkInput(this)" disabled>
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `;
}

function closeAddCustomerModalOnBackdrop(event) {
    if (event.target.id === 'addCustomerModal') {
        closeAddCustomerModal();
    }
}

function addBizDevInput() {
    const container = document.getElementById('bizdevContainer');
    const newRow = document.createElement('div');
    newRow.className = 'bizdev-input-row';
    newRow.innerHTML = `
        <input type="text" class="bizdev-input" placeholder="Enter name" required>
        <button type="button" class="btn-icon-remove" onclick="removeBizDevInput(this)">
            <i class="fa-solid fa-trash"></i>
        </button>
    `;
    container.appendChild(newRow);
    updateRemoveButtons('bizdevContainer', '.bizdev-input-row');
}

function removeBizDevInput(button) {
    const row = button.closest('.bizdev-input-row');
    row.remove();
    updateRemoveButtons('bizdevContainer', '.bizdev-input-row');
}

function addCareerLinkInput() {
    const container = document.getElementById('careerLinksContainer');
    const newRow = document.createElement('div');
    newRow.className = 'career-link-row';
    newRow.innerHTML = `
        <input type="text" class="link-label-input" placeholder="Label (e.g. Main Portal)" required>
        <input type="url" class="link-url-input" placeholder="https://example.com/careers" required>
        <button type="button" class="btn-icon-remove" onclick="removeCareerLinkInput(this)">
            <i class="fa-solid fa-trash"></i>
        </button>
    `;
    container.appendChild(newRow);
    updateRemoveButtons('careerLinksContainer', '.career-link-row');
}

function removeCareerLinkInput(button) {
    const row = button.closest('.career-link-row');
    row.remove();
    updateRemoveButtons('careerLinksContainer', '.career-link-row');
}

function updateRemoveButtons(containerId, rowSelector) {
    const container = document.getElementById(containerId);
    const rows = container.querySelectorAll(rowSelector);
    rows.forEach((row, index) => {
        const removeBtn = row.querySelector('.btn-icon-remove');
        removeBtn.disabled = rows.length === 1;
    });
}

async function handleAddCustomer(event) {
    event.preventDefault();
    
    const customerName = document.getElementById('customerName').value.trim();
    const director = document.getElementById('customerDirector').value.trim();
    
    // Collect BizDev contacts
    const bizdevInputs = document.querySelectorAll('.bizdev-input');
    const bizdev = Array.from(bizdevInputs).map(input => input.value.trim()).filter(v => v);
    
    // Collect Career Links
    const linkRows = document.querySelectorAll('.career-link-row');
    const careerLinks = Array.from(linkRows).map(row => ({
        label: row.querySelector('.link-label-input').value.trim(),
        url: row.querySelector('.link-url-input').value.trim()
    })).filter(link => link.label && link.url);
    
    if (careerLinks.length === 0) {
        showError('addCustomerError', 'At least one career link is required');
        return;
    }
    
    const errorDiv = document.getElementById('addCustomerError');
    errorDiv.style.display = 'none';
    
    try {
        const response = await fetch('/customers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                customer_name: customerName,
                director: director,
                bizdev: bizdev,
                career_links: careerLinks
            })
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Failed to add customer');
        }
        
        const result = await response.json();
        showToast(`Successfully added ${result.customer.customer_name}!`, 'success');
        
        // Refresh customer grid
        await loadCustomers();
        
        // Close modal
        closeAddCustomerModal();
        
    } catch (err) {
        showError('addCustomerError', err.message);
    }
}

// Unified form handler that routes to add or edit
async function handleCustomerForm(event) {
    event.preventDefault();
    
    if (editingCustomerId) {
        await handleEditCustomer(event);
    } else {
        await handleAddCustomer(event);
    }
}

function showError(elementId, message) {
    const errorDiv = document.getElementById(elementId);
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

// ============================================
// EDIT CUSTOMER MODAL
// ============================================

function openEditCustomerModal(customerId) {
    const customer = customersData.find(c => c.customer_id === customerId);
    if (!customer) {
        showToast('Customer not found', 'error');
        return;
    }
    
    // Set edit mode
    editingCustomerId = customerId;
    
    // Update modal title
    document.querySelector('#addCustomerModal .modal-header h2').innerHTML = 
        '<i class="fa-solid fa-pen-to-square"></i> Edit Customer';
    document.querySelector('#addCustomerModal .modal-meta').textContent = 
        'Update customer information';
    
    // Pre-fill form
    document.getElementById('customerName').value = customer.customer_name;
    document.getElementById('customerDirector').value = customer.director;
    
    // Pre-fill BizDev contacts
    const bizdevContainer = document.getElementById('bizdevContainer');
    bizdevContainer.innerHTML = customer.bizdev.map((contact, index) => `
        <div class="bizdev-input-row">
            <input type="text" class="bizdev-input" placeholder="Enter name" value="${contact}" required>
            <button type="button" class="btn-icon-remove" onclick="removeBizDevInput(this)" ${customer.bizdev.length === 1 ? 'disabled' : ''}>
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `).join('');
    
    // Pre-fill Career Links
    const careerLinksContainer = document.getElementById('careerLinksContainer');
    careerLinksContainer.innerHTML = customer.career_links.map((link, index) => `
        <div class="career-link-row">
            <input type="text" class="link-label-input" placeholder="Label (e.g. Main Portal)" value="${link.label}" required>
            <input type="url" class="link-url-input" placeholder="https://example.com/careers" value="${link.url}" required>
            <button type="button" class="btn-icon-remove" onclick="removeCareerLinkInput(this)" ${customer.career_links.length === 1 ? 'disabled' : ''}>
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `).join('');
    
    // Change submit button text
    document.querySelector('#addCustomerModal button[type="submit"]').innerHTML = 
        '<i class="fa-solid fa-check"></i> Update Customer';
    
    // Show modal
    document.getElementById('addCustomerModal').style.display = 'flex';
    document.getElementById('addCustomerError').style.display = 'none';
}

async function handleEditCustomer(event) {
    event.preventDefault();
    
    if (!editingCustomerId) {
        showError('addCustomerError', 'No customer selected for editing');
        return;
    }
    
    const customerName = document.getElementById('customerName').value.trim();
    const director = document.getElementById('customerDirector').value.trim();
    
    // Collect BizDev contacts
    const bizdevInputs = document.querySelectorAll('.bizdev-input');
    const bizdev = Array.from(bizdevInputs).map(input => input.value.trim()).filter(v => v);
    
    // Collect Career Links
    const linkRows = document.querySelectorAll('.career-link-row');
    const careerLinks = Array.from(linkRows).map(row => ({
        label: row.querySelector('.link-label-input').value.trim(),
        url: row.querySelector('.link-url-input').value.trim()
    })).filter(link => link.label && link.url);
    
    if (careerLinks.length === 0) {
        showError('addCustomerError', 'At least one career link is required');
        return;
    }
    
    const errorDiv = document.getElementById('addCustomerError');
    errorDiv.style.display = 'none';
    
    try {
        const response = await fetch(`/customers/${editingCustomerId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                customer_name: customerName,
                director: director,
                bizdev: bizdev,
                career_links: careerLinks
            })
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Failed to update customer');
        }
        
        const result = await response.json();
        showToast(`Successfully updated ${result.customer.customer_name}!`, 'success');
        
        // Refresh customer grid
        await loadCustomers();
        
        // Close modal
        closeAddCustomerModal();
        
    } catch (err) {
        showError('addCustomerError', err.message);
    }
}

// ============================================
// PRESET AND URL HANDLING
// ============================================

function loadPreset(key) {
    if (PRESETS[key]) {
        document.getElementById('urlInput').value = PRESETS[key];
        showToast(`Loaded preset URL for ${key.toUpperCase()}`);
    }
}

function clearUrlInput() {
    document.getElementById('urlInput').value = '';
}

// ============================================
// JOB EXTRACTION
// ============================================

async function handleExtraction(event) {
    event.preventDefault();
    
    const url = document.getElementById('urlInput').value.trim();
    const maxJobs = parseInt(document.getElementById('maxJobsInput').value);
    const preferredLoc = document.getElementById('preferredLocInput').value.trim() || null;
    const includeDetails = document.getElementById('includeDetailsToggle').checked;
    
    if (!url) {
        showToast('Please enter a valid URL');
        return;
    }
    
    // UI State: Loading
    setLoadingState(true);
    const startTime = performance.now();
    
    try {
        const response = await fetch('/extract-jobs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                max_jobs: maxJobs,
                include_details: includeDetails,
                preferred_location: preferredLoc
            })
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || `Server returned HTTP ${response.status}`);
        }
        
        const data = await response.json();
        const elapsedTime = ((performance.now() - startTime) / 1000).toFixed(2);
        
        currentData = data;
        renderResults(data, elapsedTime);
        showToast(`Extraction complete! Returned ${data.jobs.length} jobs.`);
        
    } catch (err) {
        showToast(`Extraction Failed: ${err.message}`);
        console.error(err);
    } finally {
        setLoadingState(false);
    }
}

function setLoadingState(isLoading) {
    const submitBtn = document.getElementById('submitBtn');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const resultsSection = document.getElementById('resultsSection');
    
    if (isLoading) {
        submitBtn.disabled = true;
        submitBtn.querySelector('.btn-text').style.display = 'none';
        submitBtn.querySelector('.btn-loader').style.display = 'inline-block';
        loadingOverlay.style.display = 'block';
        resultsSection.style.display = 'none';
    } else {
        submitBtn.disabled = false;
        submitBtn.querySelector('.btn-text').style.display = 'inline-block';
        submitBtn.querySelector('.btn-loader').style.display = 'none';
        loadingOverlay.style.display = 'none';
    }
}

function renderResults(data, elapsedTime) {
    const meta = data.metadata || {};
    const jobs = data.jobs || [];
    
    // Update Metrics Ribbon
    document.getElementById('metricReturned').innerText = jobs.length;
    
    // Show if results are limited by max_jobs
    const totalFound = meta.total_jobs_found || jobs.length;
    const isLimited = jobs.length < totalFound;
    const metricTotalFoundEl = document.getElementById('metricTotalFound');
    
    if (isLimited) {
        metricTotalFoundEl.innerHTML = `out of <strong>${totalFound}</strong> found <span style="color: var(--accent-amber); font-size: 0.85em;">⚠ Limited</span>`;
    } else {
        metricTotalFoundEl.innerText = `out of ${totalFound} found`;
    }
    
    document.getElementById('metricEnriched').innerText = meta.jobs_enriched || 0;
    document.getElementById('metricEnrichFailed').innerText = `${meta.jobs_enrichment_failed || 0} failed`;
    
    const atsVendor = meta.ats || meta.source_type || 'Generic';
    document.getElementById('metricATS').innerText = atsVendor.toUpperCase();
    document.getElementById('metricStrategy').innerText = `Strategy: ${meta.extraction_strategy || 'Default'}`;
    document.getElementById('metricTime').innerText = `${elapsedTime}s`;
    
    // Populate filter dropdowns
    populateFilterDropdowns(jobs);
    
    // Reset filters and sort state
    filteredJobs = [];
    currentSortColumn = null;
    currentSortDirection = 'asc';
    
    // Render Jobs Table
    renderTableRows(jobs);
    
    // Render JSON Code Block
    document.getElementById('jsonCodeBlock').innerText = JSON.stringify(data, null, 2);
    
    // Render Metadata Log
    const metaContainer = document.getElementById('metaContent');
    metaContainer.innerHTML = `
        <div style="font-family: var(--font-code); font-size: 13px; color: var(--text-muted);">
            <p><strong>Input URL:</strong> ${escapeHtml(meta.input_url || '')}</p>
            <p><strong>Resolved URL:</strong> ${escapeHtml(meta.resolved_url || '')}</p>
            <p><strong>Source Type:</strong> ${escapeHtml(meta.source_type || '')}</p>
            <p><strong>ATS Vendor:</strong> ${escapeHtml(meta.ats || 'None')}</p>
            <p><strong>Extraction Strategy Pipeline:</strong> ${escapeHtml(meta.extraction_strategy || '')}</p>
            <p><strong>Visited URLs:</strong> ${(meta.visited_urls || []).join(' → ')}</p>
            ${meta.warnings && meta.warnings.length ? `<p style="color: var(--accent-amber);"><strong>Warnings:</strong> ${meta.warnings.join(' | ')}</p>` : ''}
            ${meta.errors && meta.errors.length ? `<p style="color: var(--accent-rose);"><strong>Errors:</strong> ${meta.errors.join(' | ')}</p>` : ''}
        </div>
    `;
    
    document.getElementById('resultsSection').style.display = 'block';
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');
    
    const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
    if (activeBtn) activeBtn.classList.add('active');
    
    document.getElementById(tabId).style.display = 'block';
}

function downloadCSV() {
    if (!currentData || !currentData.jobs || currentData.jobs.length === 0) {
        showToast('No job data available to export');
        return;
    }
    
    // Match server-side CSV exporter column structure
    const headers = [
        'id', 'external_job_id', 'requisition_id', 'title',
        'location_raw', 'location_city', 'location_state', 'location_country',
        'department', 'employment_type', 'workplace_type', 'experience_level',
        'description', 'responsibilities', 'requirements', 'preferred_qualifications',
        'benefits', 'skills', 'job_url', 'application_url', 'posted_at',
        'source', 'ats'
    ];
    
    const rows = currentData.jobs.map(job => {
        // Extract location fields
        let locationRaw = '', locationCity = '', locationState = '', locationCountry = '';
        if (job.location) {
            if (typeof job.location === 'object') {
                locationRaw = job.location.raw || '';
                locationCity = job.location.city || '';
                locationState = job.location.state || '';
                locationCountry = job.location.country || '';
            } else {
                locationRaw = String(job.location);
            }
        }
        
        // Join list fields with semicolons
        const responsibilities = (job.responsibilities || []).join('; ');
        const requirements = (job.requirements || []).join('; ');
        const preferredQuals = (job.preferred_qualifications || []).join('; ');
        const benefits = (job.benefits || []).join('; ');
        const skills = (job.skills || []).join('; ');
        
        return [
            escapeCsv(job.id || ''),
            escapeCsv(job.external_job_id || ''),
            escapeCsv(job.requisition_id || ''),
            escapeCsv(job.title || ''),
            escapeCsv(locationRaw),
            escapeCsv(locationCity),
            escapeCsv(locationState),
            escapeCsv(locationCountry),
            escapeCsv(job.department || ''),
            escapeCsv(job.employment_type || ''),
            escapeCsv(job.workplace_type || ''),
            escapeCsv(job.experience_level || ''),
            escapeCsv(job.description || ''),
            escapeCsv(responsibilities),
            escapeCsv(requirements),
            escapeCsv(preferredQuals),
            escapeCsv(benefits),
            escapeCsv(skills),
            escapeCsv(job.job_url || ''),
            escapeCsv(job.application_url || ''),
            escapeCsv(job.posted_at || ''),
            escapeCsv(job.source || (currentData.metadata ? currentData.metadata.source : '') || ''),
            escapeCsv(job.ats || (currentData.metadata ? currentData.metadata.ats : '') || '')
        ].join(',');
    });
    
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    
    // Generate filename from source
    const source = (currentData.metadata && currentData.metadata.source) || 'jobs';
    link.setAttribute('download', `${source}_jobs_export_${Date.now()}.csv`);
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('CSV downloaded successfully!');
}

function escapeCsv(str) {
    if (str === null || str === undefined) return '""';
    const cleanStr = String(str).replace(/"/g, '""');
    return `"${cleanStr}"`;
}

function copyJSON() {
    if (!currentData) return;
    navigator.clipboard.writeText(JSON.stringify(currentData, null, 2));
    showToast('JSON copied to clipboard!');
}

function openModal(index) {
    if (!currentData || !currentData.jobs || !currentData.jobs[index]) return;
    const job = currentData.jobs[index];
    
    document.getElementById('modalTitle').innerText = job.title || 'Job Details';
    
    let locStr = 'N/A';
    if (job.location) {
        locStr = typeof job.location === 'object' ? (job.location.raw || 'N/A') : String(job.location);
    }
    document.getElementById('modalMeta').innerText = `${locStr} | ${job.department || 'Department Unspecified'}`;
    
    const modalBody = document.getElementById('modalBody');
    modalBody.innerHTML = `
        <div class="modal-section">
            <h4><i class="fa-solid fa-align-left"></i> Job Description</h4>
            <p>${escapeHtml(job.description || 'No description available.')}</p>
        </div>
        
        ${job.responsibilities && job.responsibilities.length ? `
        <div class="modal-section">
            <h4><i class="fa-solid fa-list-check"></i> Key Responsibilities</h4>
            <ul style="padding-left: 20px;">
                ${job.responsibilities.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
            </ul>
        </div>` : ''}
        
        ${job.requirements && job.requirements.length ? `
        <div class="modal-section">
            <h4><i class="fa-solid fa-graduation-cap"></i> Requirements & Qualifications</h4>
            <ul style="padding-left: 20px;">
                ${job.requirements.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
            </ul>
        </div>` : ''}
        
        ${job.skills && job.skills.length ? `
        <div class="modal-section">
            <h4><i class="fa-solid fa-code"></i> Skills</h4>
            <div class="skill-pills">${job.skills.map(s => `<span class="skill-pill">${escapeHtml(s)}</span>`).join('')}</div>
        </div>` : ''}
    `;
    
    document.getElementById('modalApplyBtn').href = job.job_url || '#';
    document.getElementById('jobDetailModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('jobDetailModal').style.display = 'none';
}

function closeModalOnBackdrop(e) {
    if (e.target.id === 'jobDetailModal') closeModal();
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 3000);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Table filtering and sorting
let currentSortColumn = null;
let currentSortDirection = 'asc';
let filteredJobs = [];

function populateFilterDropdowns(jobs) {
    // Populate ATS filter
    const atsSet = new Set();
    const locationSet = new Set();
    
    jobs.forEach(job => {
        if (job.ats) atsSet.add(job.ats);
        
        let location = '';
        if (job.location) {
            location = typeof job.location === 'object' ? (job.location.raw || '') : String(job.location);
        }
        if (location) locationSet.add(location);
    });
    
    // Update ATS dropdown
    const atsFilter = document.getElementById('filterATS');
    atsFilter.innerHTML = '<option value="">All ATS</option>' + 
        Array.from(atsSet).sort().map(ats => `<option value="${ats}">${ats.toUpperCase()}</option>`).join('');
    
    // Update Location dropdown (limit to top 20 most common)
    const locationFilter = document.getElementById('filterLocation');
    const topLocations = Array.from(locationSet).sort().slice(0, 20);
    locationFilter.innerHTML = '<option value="">All Locations</option>' + 
        topLocations.map(loc => `<option value="${loc}">${loc}</option>`).join('');
}

function filterTable() {
    if (!currentData || !currentData.jobs) return;
    
    const searchTerm = document.getElementById('tableSearchInput').value.toLowerCase();
    const atsFilter = document.getElementById('filterATS').value;
    const locationFilter = document.getElementById('filterLocation').value;
    
    filteredJobs = currentData.jobs.filter(job => {
        // Search filter (title, location, skills, description)
        if (searchTerm) {
            const title = (job.title || '').toLowerCase();
            const location = (typeof job.location === 'object' ? (job.location.raw || '') : String(job.location || '')).toLowerCase();
            const skills = (job.skills || []).join(' ').toLowerCase();
            const description = (job.description || '').toLowerCase();
            const dept = (job.department || '').toLowerCase();
            
            if (!title.includes(searchTerm) && 
                !location.includes(searchTerm) && 
                !skills.includes(searchTerm) && 
                !description.includes(searchTerm) &&
                !dept.includes(searchTerm)) {
                return false;
            }
        }
        
        // ATS filter
        if (atsFilter && job.ats !== atsFilter) {
            return false;
        }
        
        // Location filter
        if (locationFilter) {
            const jobLocation = typeof job.location === 'object' ? (job.location.raw || '') : String(job.location || '');
            if (jobLocation !== locationFilter) {
                return false;
            }
        }
        
        return true;
    });
    
    // Re-render table with filtered jobs
    renderTableRows(filteredJobs);
    
    // Show filter count
    if (filteredJobs.length !== currentData.jobs.length) {
        showToast(`Showing ${filteredJobs.length} of ${currentData.jobs.length} jobs`);
    }
}

function clearFilters() {
    document.getElementById('tableSearchInput').value = '';
    document.getElementById('filterATS').value = '';
    document.getElementById('filterLocation').value = '';
    filterTable();
    showToast('Filters cleared');
}

function sortTable(column) {
    if (!currentData || !currentData.jobs) return;
    
    // Toggle sort direction if same column
    if (currentSortColumn === column) {
        currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortColumn = column;
        currentSortDirection = 'asc';
    }
    
    // Get jobs to sort (filtered or all)
    const jobsToSort = filteredJobs.length > 0 ? [...filteredJobs] : [...currentData.jobs];
    
    jobsToSort.sort((a, b) => {
        let aVal, bVal;
        
        switch(column) {
            case 'id':
                aVal = a.id || a.requisition_id || a.external_job_id || '';
                bVal = b.id || b.requisition_id || b.external_job_id || '';
                break;
            case 'title':
                aVal = (a.title || '').toLowerCase();
                bVal = (b.title || '').toLowerCase();
                break;
            case 'location':
                aVal = (typeof a.location === 'object' ? (a.location.raw || '') : String(a.location || '')).toLowerCase();
                bVal = (typeof b.location === 'object' ? (b.location.raw || '') : String(b.location || '')).toLowerCase();
                break;
            case 'ats':
                aVal = (a.ats || '').toLowerCase();
                bVal = (b.ats || '').toLowerCase();
                break;
            case 'posted_at':
                aVal = a.posted_at || '';
                bVal = b.posted_at || '';
                break;
            default:
                return 0;
        }
        
        if (aVal < bVal) return currentSortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return currentSortDirection === 'asc' ? 1 : -1;
        return 0;
    });
    
    renderTableRows(jobsToSort);
    showToast(`Sorted by ${column} (${currentSortDirection})`);
}

function renderTableRows(jobs) {
    const tbody = document.getElementById('jobsTableBody');
    tbody.innerHTML = '';
    
    if (jobs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 40px; color: var(--text-muted);">
            <i class="fa-solid fa-folder-open" style="font-size: 32px; margin-bottom: 12px; display: block;"></i>
            No jobs match your filters.
        </td></tr>`;
        return;
    }
    
    const meta = currentData.metadata || {};
    
    jobs.forEach((job, index) => {
        const tr = document.createElement('tr');
        
        const jobId = job.id || job.requisition_id || job.external_job_id || `JOB-${currentData.jobs.indexOf(job) + 1}`;
        const title = job.title || 'Untitled Role';
        const jobUrl = job.job_url || '#';
        
        // Format Location
        let locStr = 'N/A';
        if (job.location) {
            if (typeof job.location === 'object') {
                locStr = job.location.raw || [job.location.city, job.location.state, job.location.country].filter(Boolean).join(', ') || 'N/A';
            } else {
                locStr = String(job.location);
            }
        }
        
        // Format ATS Badge
        const atsClass = (job.ats || meta.ats || 'generic').toLowerCase();
        
        // Format Responsibilities (Top 2 bullets)
        let respHtml = '<span class="text-dim">N/A</span>';
        if (job.responsibilities && job.responsibilities.length > 0) {
            const items = job.responsibilities.slice(0, 2).map(r => `<li>${escapeHtml(r.substring(0, 90))}${r.length > 90 ? '...' : ''}</li>`).join('');
            respHtml = `<ul class="resp-list">${items}</ul>`;
        } else if (job.description) {
            respHtml = `<span class="text-muted">${escapeHtml(job.description.substring(0, 100))}...</span>`;
        }
        
        // Format Skills
        let skillsHtml = '<span class="text-dim">None</span>';
        if (job.skills && job.skills.length > 0) {
            skillsHtml = `<div class="skill-pills">${job.skills.map(s => `<span class="skill-pill">${escapeHtml(s)}</span>`).join('')}</div>`;
        }
        
        const postedAt = job.posted_at || job.employment_type || 'N/A';
        const originalIndex = currentData.jobs.indexOf(job);
        
        tr.innerHTML = `
            <td><span class="badge-id">${escapeHtml(jobId)}</span></td>
            <td>
                <a href="${escapeHtml(jobUrl)}" target="_blank" class="job-title-link">${escapeHtml(title)}</a>
                <span class="text-dim" style="font-size: 11px;">${escapeHtml(job.department || '')}</span>
            </td>
            <td><span class="badge-loc"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(locStr)}</span></td>
            <td><span class="badge-ats ${atsClass}">${escapeHtml(job.ats || meta.ats || 'Generic')}</span></td>
            <td>${respHtml}</td>
            <td>${skillsHtml}</td>
            <td style="white-space: nowrap;"><i class="fa-regular fa-calendar"></i> ${escapeHtml(postedAt)}</td>
            <td>
                <button type="button" class="btn-icon" onclick="openModal(${originalIndex})" title="View Full Details">
                    <i class="fa-solid fa-eye"></i>
                </button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}


// ============================================
// INITIALIZATION
// ============================================

// Load customers on page load
document.addEventListener('DOMContentLoaded', () => {
    loadCustomers();
});

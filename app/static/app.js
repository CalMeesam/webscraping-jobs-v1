/**
 * Adaptive Career Job Extraction Engine Frontend Client
 */

let currentData = null;
let customersData = [];
let editingCustomerId = null; // Track which customer is being edited
let newJobKeysSet = new Set(); // Track new job identity keys for highlighting

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
                    <div class="customer-actions">
                        <button type="button" class="btn-history-customer" onclick="openCustomerHistoryModal('${customer.customer_id}')" title="View extraction run history">
                            <i class="fa-solid fa-clock-rotate-left"></i>
                        </button>
                        <button type="button" class="btn-edit-customer" onclick="openEditCustomerModal('${customer.customer_id}')" title="Edit customer">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                    </div>
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
// ADD & EDIT CUSTOMER MODAL
// ============================================

function openAddCustomerModal() {
    editingCustomerId = null;
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
    editingCustomerId = null;
    
    document.querySelector('#addCustomerModal .modal-header h2').innerHTML = 
        '<i class="fa-solid fa-building-circle-arrow-right"></i> Add New Customer';
    document.querySelector('#addCustomerModal .modal-meta').textContent = 
        'Register a new customer career portal';
    document.querySelector('#addCustomerModal button[type="submit"]').innerHTML = 
        '<i class="fa-solid fa-check"></i> Add Customer';
    
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
    rows.forEach((row) => {
        const removeBtn = row.querySelector('.btn-icon-remove');
        removeBtn.disabled = rows.length === 1;
    });
}

async function handleAddCustomer(event) {
    event.preventDefault();
    
    const customerName = document.getElementById('customerName').value.trim();
    const director = document.getElementById('customerDirector').value.trim();
    
    const bizdevInputs = document.querySelectorAll('.bizdev-input');
    const bizdev = Array.from(bizdevInputs).map(input => input.value.trim()).filter(v => v);
    
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
            headers: { 'Content-Type': 'application/json' },
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
        
        await loadCustomers();
        closeAddCustomerModal();
        
    } catch (err) {
        showError('addCustomerError', err.message);
    }
}

function openEditCustomerModal(customerId) {
    const customer = customersData.find(c => c.customer_id === customerId);
    if (!customer) {
        showToast('Customer not found', 'error');
        return;
    }
    
    editingCustomerId = customerId;
    
    document.querySelector('#addCustomerModal .modal-header h2').innerHTML = 
        '<i class="fa-solid fa-pen-to-square"></i> Edit Customer';
    document.querySelector('#addCustomerModal .modal-meta').textContent = 
        'Update customer information';
    
    document.getElementById('customerName').value = customer.customer_name;
    document.getElementById('customerDirector').value = customer.director;
    
    const bizdevContainer = document.getElementById('bizdevContainer');
    bizdevContainer.innerHTML = customer.bizdev.map((contact) => `
        <div class="bizdev-input-row">
            <input type="text" class="bizdev-input" placeholder="Enter name" value="${contact}" required>
            <button type="button" class="btn-icon-remove" onclick="removeBizDevInput(this)" ${customer.bizdev.length === 1 ? 'disabled' : ''}>
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `).join('');
    
    const careerLinksContainer = document.getElementById('careerLinksContainer');
    careerLinksContainer.innerHTML = customer.career_links.map((link) => `
        <div class="career-link-row">
            <input type="text" class="link-label-input" placeholder="Label (e.g. Main Portal)" value="${link.label}" required>
            <input type="url" class="link-url-input" placeholder="https://example.com/careers" value="${link.url}" required>
            <button type="button" class="btn-icon-remove" onclick="removeCareerLinkInput(this)" ${customer.career_links.length === 1 ? 'disabled' : ''}>
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
    `).join('');
    
    document.querySelector('#addCustomerModal button[type="submit"]').innerHTML = 
        '<i class="fa-solid fa-check"></i> Update Customer';
    
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
    
    const bizdevInputs = document.querySelectorAll('.bizdev-input');
    const bizdev = Array.from(bizdevInputs).map(input => input.value.trim()).filter(v => v);
    
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
            headers: { 'Content-Type': 'application/json' },
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
        
        await loadCustomers();
        closeAddCustomerModal();
        
    } catch (err) {
        showError('addCustomerError', err.message);
    }
}

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
// PRESETS & EXTRACTION
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
    
    setLoadingState(true);
    const startTime = performance.now();
    
    try {
        const response = await fetch('/extract-jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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
    
    // Process Diff Summary Ribbon
    const diff = meta.diff_summary;
    const diffBanner = document.getElementById('diffBanner');
    newJobKeysSet = new Set();
    
    if (diff && diff.has_previous_run) {
        diffBanner.style.display = 'flex';
        const formattedDate = diff.previous_run_at ? new Date(diff.previous_run_at).toLocaleString() : '';
        const bannerMessage = formattedDate 
            ? `${diff.new_jobs_count} new jobs, ${diff.removed_jobs_count} removed since last check on ${formattedDate}`
            : (diff.message || '');
        document.getElementById('diffBannerText').innerText = bannerMessage;
        
        const badgeNew = document.getElementById('diffBadgeNew');
        badgeNew.style.display = 'inline-flex';
        badgeNew.innerHTML = `<i class="fa-solid fa-plus-circle"></i> ${diff.new_jobs_count} New`;
        
        const badgeRemoved = document.getElementById('diffBadgeRemoved');
        badgeRemoved.style.display = 'inline-flex';
        badgeRemoved.innerHTML = `<i class="fa-solid fa-minus-circle"></i> ${diff.removed_jobs_count} Removed`;
        
        if (diff.new_job_keys && diff.new_job_keys.length) {
            newJobKeysSet = new Set(diff.new_job_keys);
        }
    } else if (diff && !diff.has_previous_run) {
        diffBanner.style.display = 'flex';
        document.getElementById('diffBannerText').innerText = "First extraction recorded for this customer (Baseline run, no prior comparison available).";
        
        const badgeNew = document.getElementById('diffBadgeNew');
        badgeNew.style.display = 'inline-flex';
        badgeNew.innerHTML = `<i class="fa-solid fa-flag"></i> Baseline Run`;
        
        const badgeRemoved = document.getElementById('diffBadgeRemoved');
        badgeRemoved.style.display = 'none';
    } else {
        diffBanner.style.display = 'none';
    }
    
    // Update Metrics Ribbon
    document.getElementById('metricReturned').innerText = jobs.length;
    
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
    
    populateFilterDropdowns(jobs);
    
    filteredJobs = [];
    currentSortColumn = null;
    currentSortDirection = 'asc';
    
    renderTableRows(jobs);
    
    document.getElementById('jsonCodeBlock').innerText = JSON.stringify(data, null, 2);
    
    const metaContainer = document.getElementById('metaContent');
    metaContainer.innerHTML = `
        <div style="font-family: var(--font-code); font-size: 13px; color: var(--text-muted);">
            <p><strong>Input URL:</strong> ${escapeHtml(meta.input_url || '')}</p>
            <p><strong>Customer ID:</strong> ${escapeHtml(meta.customer_id || 'N/A')}</p>
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
    
    const headers = [
        'id', 'external_job_id', 'requisition_id', 'title',
        'location_raw', 'location_city', 'location_state', 'location_country',
        'department', 'employment_type', 'workplace_type', 'experience_level',
        'description', 'responsibilities', 'requirements', 'preferred_qualifications',
        'benefits', 'skills', 'job_url', 'application_url', 'posted_at',
        'source', 'ats'
    ];
    
    const rows = currentData.jobs.map(job => {
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

let currentSortColumn = null;
let currentSortDirection = 'asc';
let filteredJobs = [];

function populateFilterDropdowns(jobs) {
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
    
    const atsFilter = document.getElementById('filterATS');
    atsFilter.innerHTML = '<option value="">All ATS</option>' + 
        Array.from(atsSet).sort().map(ats => `<option value="${ats}">${ats.toUpperCase()}</option>`).join('');
    
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
        
        if (atsFilter && job.ats !== atsFilter) {
            return false;
        }
        
        if (locationFilter) {
            const jobLocation = typeof job.location === 'object' ? (job.location.raw || '') : String(job.location || '');
            if (jobLocation !== locationFilter) {
                return false;
            }
        }
        
        return true;
    });
    
    renderTableRows(filteredJobs);
    
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
    
    if (currentSortColumn === column) {
        currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortColumn = column;
        currentSortDirection = 'asc';
    }
    
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
    
    jobs.forEach((job) => {
        const tr = document.createElement('tr');
        
        const jobId = job.id || job.requisition_id || job.external_job_id || `JOB-${currentData.jobs.indexOf(job) + 1}`;
        const title = job.title || 'Untitled Role';
        const jobUrl = job.job_url || '#';
        
        // Helper to check if job is NEW based on identity key
        let isNewJob = false;
        if (newJobKeysSet.size > 0) {
            const possibleKeys = [
                `id:${job.id}`,
                `job_url:${(job.job_url || '').replace(/^https?:\/\//, '').toLowerCase()}`,
                `app_url:${(job.application_url || '').replace(/^https?:\/\//, '').toLowerCase()}`
            ];
            isNewJob = possibleKeys.some(k => newJobKeysSet.has(k));
        }
        
        let locStr = 'N/A';
        if (job.location) {
            if (typeof job.location === 'object') {
                locStr = job.location.raw || [job.location.city, job.location.state, job.location.country].filter(Boolean).join(', ') || 'N/A';
            } else {
                locStr = String(job.location);
            }
        }
        
        const atsClass = (job.ats || meta.ats || 'generic').toLowerCase();
        
        let respHtml = '<span class="text-dim">N/A</span>';
        if (job.responsibilities && job.responsibilities.length > 0) {
            const items = job.responsibilities.slice(0, 2).map(r => `<li>${escapeHtml(r.substring(0, 90))}${r.length > 90 ? '...' : ''}</li>`).join('');
            respHtml = `<ul class="resp-list">${items}</ul>`;
        } else if (job.description) {
            respHtml = `<span class="text-muted">${escapeHtml(job.description.substring(0, 100))}...</span>`;
        }
        
        let skillsHtml = '<span class="text-dim">None</span>';
        if (job.skills && job.skills.length > 0) {
            skillsHtml = `<div class="skill-pills">${job.skills.map(s => `<span class="skill-pill">${escapeHtml(s)}</span>`).join('')}</div>`;
        }
        
        const postedAt = job.posted_at || job.employment_type || 'N/A';
        const originalIndex = currentData.jobs.indexOf(job);
        
        const newBadgeHtml = isNewJob ? '<span class="badge-new-pill"><i class="fa-solid fa-sparkles"></i> NEW</span> ' : '';
        
        tr.innerHTML = `
            <td><span class="badge-id">${escapeHtml(jobId)}</span></td>
            <td>
                ${newBadgeHtml}<a href="${escapeHtml(jobUrl)}" target="_blank" class="job-title-link">${escapeHtml(title)}</a>
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
        
        if (isNewJob) {
            tr.classList.add('row-new-job');
        }
        
        tbody.appendChild(tr);
    });
}

// Load customers on page load
document.addEventListener('DOMContentLoaded', () => {
    loadCustomers();
});

// ==========================================
// 1. CSV EXPORT FOR MAIN EXTRACTION VIEW
// ==========================================
function downloadCSV() {
    if (!currentData || !currentData.jobs || currentData.jobs.length === 0) {
        showToast('No job data available to export');
        return;
    }

    // Ensure all extracted jobs (not just filtered subset) are exported
    const allJobs = currentData.jobs;
    const columns = [
        "id", "external_job_id", "requisition_id", "title", "location_raw",
        "location_city", "location_state", "location_country", "department",
        "employment_type", "workplace_type", "experience_level", "description",
        "responsibilities", "requirements", "preferred_qualifications", "benefits",
        "skills", "job_url", "application_url", "posted_at", "source", "ats"
    ];

    const csvRows = [];
    csvRows.push(columns.join(','));

    allJobs.forEach(job => {
        let locRaw = '', locCity = '', locState = '', locCountry = '';
        if (job.location) {
            if (typeof job.location === 'object') {
                locRaw = job.location.raw || '';
                locCity = job.location.city || '';
                locState = job.location.state || '';
                locCountry = job.location.country || '';
            } else {
                locRaw = String(job.location);
            }
        }

        const row = [
            escapeCsvCell(job.id || ''),
            escapeCsvCell(job.external_job_id || ''),
            escapeCsvCell(job.requisition_id || ''),
            escapeCsvCell(job.title || ''),
            escapeCsvCell(locRaw),
            escapeCsvCell(locCity),
            escapeCsvCell(locState),
            escapeCsvCell(locCountry),
            escapeCsvCell(job.department || ''),
            escapeCsvCell(job.employment_type || ''),
            escapeCsvCell(job.workplace_type || ''),
            escapeCsvCell(job.experience_level || ''),
            escapeCsvCell(job.description || ''),
            escapeCsvCell((job.responsibilities || []).join('; ')),
            escapeCsvCell((job.requirements || []).join('; ')),
            escapeCsvCell((job.preferred_qualifications || []).join('; ')),
            escapeCsvCell((job.benefits || []).join('; ')),
            escapeCsvCell((job.skills || []).join('; ')),
            escapeCsvCell(job.job_url || ''),
            escapeCsvCell(job.application_url || ''),
            escapeCsvCell(job.posted_at || ''),
            escapeCsvCell(job.source || ''),
            escapeCsvCell(job.ats || '')
        ];
        csvRows.push(row.join(','));
    });

    const csvBlob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const blobUrl = URL.createObjectURL(csvBlob);
    const link = document.createElement('a');
    link.href = blobUrl;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    link.setAttribute('download', `extracted_jobs_${timestamp}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(blobUrl);

    showToast(`Exported all ${allJobs.length} extracted jobs to CSV`);
}

function escapeCsvCell(cell) {
    if (cell === null || cell === undefined) return '""';
    const str = String(cell).replace(/"/g, '""');
    return `"${str}"`;
}

// ==========================================
// 2. CLIENT RUN HISTORY & RUN COMPARISON
// ==========================================
let currentHistoryData = null;
let currentCustomerId = null;
let selectedRunIds = new Set();
let currentComparisonData = null;
let currentActiveComparisonFilter = 'all';

async function openCustomerHistoryModal(customerId) {
    currentCustomerId = customerId;
    selectedRunIds.clear();
    updateCompareSelectedBtn();

    const modal = document.getElementById('historyModal');
    const titleEl = document.getElementById('historyModalTitle');
    const metaEl = document.getElementById('historyModalMeta');
    const summaryEl = document.getElementById('historySummary');
    const listEl = document.getElementById('historyList');

    // Switch to timeline view
    document.getElementById('historyTimelineView').style.display = 'block';
    document.getElementById('historyComparisonView').style.display = 'none';

    const customer = (customersData || []).find(c => c.customer_id === customerId);
    const customerName = customer ? customer.customer_name : customerId;

    titleEl.innerHTML = `<i class="fa-solid fa-timeline"></i> Extraction Run History`;
    metaEl.innerText = `${customerName} (ID: ${customerId})`;

    summaryEl.innerHTML = `<div style="text-align: center; padding: 12px; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Loading historical runs...</div>`;
    listEl.innerHTML = '';

    modal.style.display = 'flex';
    modal.classList.add('active');

    try {
        const response = await fetch(`/customers/${encodeURIComponent(customerId)}/history?limit=30`);
        if (!response.ok) {
            throw new Error(`Failed to fetch history (HTTP ${response.status})`);
        }

        const data = await response.json();
        currentHistoryData = data;
        renderHistoryList(data, customerName);
    } catch (err) {
        summaryEl.innerHTML = `<div class="error-box" style="padding: 12px; background: rgba(244,63,94,0.15); border: 1px solid var(--accent-rose); border-radius: 8px; color: #fda4af;">
            <i class="fa-solid fa-triangle-exclamation"></i> Error loading history: ${escapeHtml(err.message)}
        </div>`;
    }
}

function renderHistoryList(data, customerName) {
    const summaryEl = document.getElementById('historySummary');
    const listEl = document.getElementById('historyList');
    const runs = data.runs || [];

    if (runs.length === 0) {
        summaryEl.innerHTML = `<div style="padding: 20px; text-align: center; color: var(--text-muted);">
            <i class="fa-solid fa-inbox" style="font-size: 32px; margin-bottom: 8px; display: block; opacity: 0.5;"></i>
            No previous extraction runs recorded for <strong>${escapeHtml(customerName)}</strong> yet.
        </div>`;
        listEl.innerHTML = '';
        return;
    }

    const diff = data.diff_summary || {};
    let diffSummaryHtml = '';
    if (diff.has_previous_run) {
        const dateStr = diff.previous_run_at ? new Date(diff.previous_run_at).toLocaleString() : '';
        diffSummaryHtml = `<div style="padding: 10px 14px; background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; margin-bottom: 12px; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <span><i class="fa-solid fa-chart-line"></i> Latest Diff: <strong>${diff.new_jobs_count} new</strong>, <strong>${diff.removed_jobs_count} removed</strong> against run on ${dateStr}</span>
            <button type="button" class="btn-primary" onclick="compareRuns(${diff.previous_run_id}, ${diff.latest_run_id}, '${escapeHtml(customerName)}')" style="padding: 4px 10px; font-size: 0.8rem;">
                <i class="fa-solid fa-code-compare"></i> View Latest Comparison
            </button>
        </div>`;
    }

    summaryEl.innerHTML = `
        ${diffSummaryHtml}
        <div style="font-size: 0.85rem; color: var(--text-muted);">
            Showing <strong>${runs.length}</strong> recorded extraction run${runs.length > 1 ? 's' : ''} for <strong>${escapeHtml(customerName)}</strong>:
        </div>
    `;

    listEl.innerHTML = '';
    runs.forEach((run, index) => {
        const runCard = document.createElement('div');
        runCard.className = 'history-run-card';
        runCard.id = `run-card-${run.id}`;

        const dateFormatted = run.run_at ? new Date(run.run_at).toLocaleString() : 'Unknown Date';
        const statusClass = (run.status || 'success').toLowerCase();
        const found = run.jobs_found_count !== null && run.jobs_found_count !== undefined ? run.jobs_found_count : (run.jobs_count || 0);
        const returned = run.jobs_returned_count !== null && run.jobs_returned_count !== undefined ? run.jobs_returned_count : (run.jobs_count || 0);
        const isLatest = index === 0;

        let compareButtonsHtml = '';
        if (index + 1 < runs.length) {
            const prevRun = runs[index + 1];
            compareButtonsHtml += `
                <button type="button" class="btn-secondary" onclick="compareRuns(${prevRun.id}, ${run.id}, '${escapeHtml(customerName)}')" title="Compare Run #${run.id} against Run #${prevRun.id}" style="padding: 6px 12px; font-size: 0.8rem;">
                    <i class="fa-solid fa-code-compare"></i> Compare with Run #${prevRun.id}
                </button>
            `;
        } else if (!isLatest && runs.length > 0) {
            const latestRun = runs[0];
            compareButtonsHtml += `
                <button type="button" class="btn-secondary" onclick="compareRuns(${run.id}, ${latestRun.id}, '${escapeHtml(customerName)}')" title="Compare with Latest (Run #${latestRun.id})" style="padding: 6px 12px; font-size: 0.8rem;">
                    <i class="fa-solid fa-code-compare"></i> Compare with Latest (#${latestRun.id})
                </button>
            `;
        }

        runCard.innerHTML = `
            <div class="run-card-left">
                <input type="checkbox" id="chk-run-${run.id}" onchange="toggleRunSelection(${run.id})" style="cursor: pointer; width: 16px; height: 16px; accent-color: var(--accent-cyan);">
                <div class="run-card-meta">
                    <div class="run-title">
                        <span>Run #${run.id}</span>
                        ${isLatest ? '<span class="badge-id" style="font-size: 10px; background: rgba(16, 185, 129, 0.2); color: #34d399;">LATEST</span>' : ''}
                        <span class="run-status-pill ${statusClass}">${escapeHtml(run.status || 'SUCCESS')}</span>
                    </div>
                    <div class="run-sub">
                        <span><i class="fa-regular fa-clock"></i> ${escapeHtml(dateFormatted)}</span>
                        <span><i class="fa-solid fa-briefcase"></i> <strong>${returned}</strong> returned (${found} found)</span>
                        <span style="color: var(--text-dim);"><i class="fa-solid fa-bolt"></i> ${escapeHtml(run.strategy_used || 'ATS')}</span>
                    </div>
                </div>
            </div>
            <div class="run-card-actions">
                ${compareButtonsHtml}
            </div>
        `;

        listEl.appendChild(runCard);
    });
}

function toggleRunSelection(runId) {
    if (selectedRunIds.has(runId)) {
        selectedRunIds.delete(runId);
        document.getElementById(`run-card-${runId}`)?.classList.remove('selected');
    } else {
        if (selectedRunIds.size >= 2) {
            const firstSelected = Array.from(selectedRunIds)[0];
            selectedRunIds.delete(firstSelected);
            const chk = document.getElementById(`chk-run-${firstSelected}`);
            if (chk) chk.checked = false;
            document.getElementById(`run-card-${firstSelected}`)?.classList.remove('selected');
        }
        selectedRunIds.add(runId);
        document.getElementById(`run-card-${runId}`)?.classList.add('selected');
    }
    updateCompareSelectedBtn();
}

function updateCompareSelectedBtn() {
    const btn = document.getElementById('btnCompareSelected');
    if (!btn) return;
    const count = selectedRunIds.size;
    btn.innerHTML = `<i class="fa-solid fa-code-compare"></i> Compare Selected (${count}/2)`;
    btn.disabled = count !== 2;
}

function compareSelectedRuns() {
    if (selectedRunIds.size !== 2) return;
    const ids = Array.from(selectedRunIds).sort((a, b) => a - b);
    const baseId = ids[0];
    const targetId = ids[1];
    const customer = (customersData || []).find(c => c.customer_id === currentCustomerId);
    const customerName = customer ? customer.customer_name : currentCustomerId;
    compareRuns(baseId, targetId, customerName);
}

async function compareRuns(baseRunId, targetRunId, customerName) {
    document.getElementById('historyTimelineView').style.display = 'none';
    document.getElementById('historyComparisonView').style.display = 'block';

    const container = document.getElementById('comparisonTablesContainer');
    const titleEl = document.getElementById('comparisonTitle');
    const metaEl = document.getElementById('comparisonMeta');

    titleEl.innerHTML = `<i class="fa-solid fa-code-compare" style="color: var(--accent-cyan);"></i> Comparison: Run #${baseRunId} vs Run #${targetRunId}`;
    metaEl.innerText = `Analyzing differences between baseline run #${baseRunId} and subsequent run #${targetRunId} (${customerName || ''})`;

    container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><br><br>Computing field-level diffs and snapshot comparisons...</div>`;

    try {
        const response = await fetch(`/runs/${targetRunId}/compare/${baseRunId}`);
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || `Server returned HTTP ${response.status}`);
        }

        const comparison = await response.json();
        currentComparisonData = comparison;
        renderComparisonView(comparison);
    } catch (err) {
        container.innerHTML = `<div class="error-box" style="padding: 16px; background: rgba(244,63,94,0.15); border: 1px solid var(--accent-rose); border-radius: 8px; color: #fda4af;">
            <i class="fa-solid fa-triangle-exclamation"></i> Comparison Failed: ${escapeHtml(err.message)}
        </div>`;
    }
}

function renderComparisonView(comp) {
    const summary = comp.summary || {};
    const addedCount = summary.added_count || 0;
    const removedCount = summary.removed_count || 0;
    const changedCount = summary.changed_count || 0;
    const unchangedCount = summary.unchanged_count || 0;

    document.getElementById('compCountAdded').innerText = addedCount;
    document.getElementById('compCountRemoved').innerText = removedCount;
    document.getElementById('compCountChanged').innerText = changedCount;
    document.getElementById('compCountUnchanged').innerText = unchangedCount;

    document.getElementById('tabCountAdded').innerText = addedCount;
    document.getElementById('tabCountRemoved').innerText = removedCount;
    document.getElementById('tabCountChanged').innerText = changedCount;
    document.getElementById('tabCountUnchanged').innerText = unchangedCount;

    const baseDate = comp.base_run?.run_at ? new Date(comp.base_run.run_at).toLocaleString() : `Run #${comp.base_run?.id}`;
    const targetDate = comp.target_run?.run_at ? new Date(comp.target_run.run_at).toLocaleString() : `Run #${comp.target_run?.id}`;
    document.getElementById('comparisonMeta').innerHTML = `
        <strong>Base:</strong> Run #${comp.base_run?.id} (${baseDate}) &nbsp;➔&nbsp; 
        <strong>Target:</strong> Run #${comp.target_run?.id} (${targetDate})
    `;

    filterComparisonTab('all');
}

function filterComparisonTab(tabKey) {
    currentActiveComparisonFilter = tabKey;

    ['tabCompAll', 'tabCompAdded', 'tabCompRemoved', 'tabCompChanged', 'tabCompUnchanged'].forEach(tabId => {
        document.getElementById(tabId)?.classList.remove('active');
    });

    const activeBtnMap = {
        'all': 'tabCompAll',
        'added': 'tabCompAdded',
        'removed': 'tabCompRemoved',
        'changed': 'tabCompChanged',
        'unchanged': 'tabCompUnchanged'
    };
    if (activeBtnMap[tabKey]) {
        document.getElementById(activeBtnMap[tabKey])?.classList.add('active');
    }

    renderComparisonTables(currentComparisonData, tabKey);
}

function renderComparisonTables(comp, filter) {
    if (!comp) return;
    const container = document.getElementById('comparisonTablesContainer');
    container.innerHTML = '';

    const addedJobs = comp.added_jobs || [];
    const removedJobs = comp.removed_jobs || [];
    const changedJobs = comp.changed_jobs || [];
    const unchangedJobs = comp.unchanged_jobs || [];

    const showAll = filter === 'all';
    const showAdded = showAll || filter === 'added';
    const showRemoved = showAll || filter === 'removed';
    const showChanged = showAll || filter === 'changed';
    const showUnchanged = showAll || filter === 'unchanged';

    let totalRenderedSections = 0;

    // 1. CHANGED JOBS SECTION (with Field-Level Old vs New Table)
    if (showChanged && changedJobs.length > 0) {
        totalRenderedSections++;
        const section = document.createElement('div');
        section.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h4 style="color: #fbbf24; display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                    <i class="fa-solid fa-pen-to-square"></i> Changed Jobs (${changedJobs.length})
                </h4>
                <table class="comp-table">
                    <thead>
                        <tr>
                            <th style="width: 25%;">Role / Title</th>
                            <th style="width: 20%;">Location</th>
                            <th style="width: 55%;">Field Modifications (Old Value ➔ New Value)</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${changedJobs.map(c => {
                            const diffRows = c.field_changes.map(ch => `
                                <tr>
                                    <td class="diff-field-name">${escapeHtml(ch.label || ch.field)}</td>
                                    <td><span class="diff-old-val">${escapeHtml(ch.old_value || 'None')}</span></td>
                                    <td style="color: var(--text-muted); width: 20px; text-align: center;">➔</td>
                                    <td><span class="diff-new-val">${escapeHtml(ch.new_value || 'None')}</span></td>
                                </tr>
                            `).join('');

                            return `
                                <tr>
                                    <td>
                                        <a href="${escapeHtml(c.job_url || '#')}" target="_blank" class="job-title-link">
                                            ${escapeHtml(c.title || 'Untitled')}
                                        </a>
                                        <div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">Key: ${escapeHtml(c.job_identity_key)}</div>
                                    </td>
                                    <td><span class="badge-loc"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(c.location || 'N/A')}</span></td>
                                    <td>
                                        <table class="diff-field-table">
                                            <thead>
                                                <tr>
                                                    <th>Field</th>
                                                    <th>Previous Value</th>
                                                    <th></th>
                                                    <th>New Value</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                ${diffRows}
                                            </tbody>
                                        </table>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
        container.appendChild(section);
    }

    // 2. ADDED JOBS SECTION
    if (showAdded && addedJobs.length > 0) {
        totalRenderedSections++;
        const section = document.createElement('div');
        section.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h4 style="color: #34d399; display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                    <i class="fa-solid fa-circle-plus"></i> Added Jobs in Newer Run (${addedJobs.length})
                </h4>
                <table class="comp-table">
                    <thead>
                        <tr>
                            <th style="width: 35%;">Role / Title</th>
                            <th style="width: 25%;">Location</th>
                            <th style="width: 20%;">Department / ATS</th>
                            <th style="width: 20%;">Links</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${addedJobs.map(job => `
                            <tr>
                                <td>
                                    <span class="badge-new-pill"><i class="fa-solid fa-plus"></i> NEW</span>
                                    <a href="${escapeHtml(job.job_url || '#')}" target="_blank" class="job-title-link">${escapeHtml(job.title || 'Untitled')}</a>
                                </td>
                                <td><span class="badge-loc"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(job.location || 'N/A')}</span></td>
                                <td>
                                    <span style="font-size: 0.85em; color: var(--text-muted);">${escapeHtml(job.department || 'N/A')}</span>
                                    <span class="badge-ats" style="margin-left: 6px; font-size: 10px;">${escapeHtml(job.ats || 'ATS')}</span>
                                </td>
                                <td>
                                    <a href="${escapeHtml(job.job_url || '#')}" target="_blank" class="btn-icon" style="display: inline-flex; text-decoration: none; padding: 4px 8px; font-size: 11px;">
                                        <i class="fa-solid fa-arrow-up-right-from-square"></i> Open
                                    </a>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        container.appendChild(section);
    }

    // 3. REMOVED JOBS SECTION
    if (showRemoved && removedJobs.length > 0) {
        totalRenderedSections++;
        const section = document.createElement('div');
        section.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h4 style="color: #fb7185; display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                    <i class="fa-solid fa-circle-minus"></i> Removed Jobs (No longer in Newer Run) (${removedJobs.length})
                </h4>
                <table class="comp-table">
                    <thead>
                        <tr>
                            <th style="width: 40%;">Role / Title</th>
                            <th style="width: 30%;">Last Known Location</th>
                            <th style="width: 30%;">Department / Key</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${removedJobs.map(job => `
                            <tr style="opacity: 0.85;">
                                <td>
                                    <span style="padding: 2px 6px; background: rgba(244,63,94,0.15); color: #fda4af; border-radius: 4px; font-size: 10px; font-weight: 600; margin-right: 6px;">REMOVED</span>
                                    <span style="text-decoration: line-through; color: var(--text-muted); font-weight: 500;">${escapeHtml(job.title || 'Untitled')}</span>
                                </td>
                                <td><span class="badge-loc"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(job.location || 'N/A')}</span></td>
                                <td>
                                    <span style="font-size: 0.85em; color: var(--text-dim);">${escapeHtml(job.department || 'N/A')}</span>
                                    <div style="font-size: 10px; color: var(--text-dim);">Key: ${escapeHtml(job.job_identity_key)}</div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        container.appendChild(section);
    }

    // 4. UNCHANGED JOBS SECTION
    if (showUnchanged && unchangedJobs.length > 0) {
        totalRenderedSections++;
        const section = document.createElement('div');
        section.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h4 style="color: #38bdf8; display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                    <i class="fa-solid fa-check"></i> Unchanged Jobs (${unchangedJobs.length})
                </h4>
                <table class="comp-table">
                    <thead>
                        <tr>
                            <th style="width: 50%;">Role / Title</th>
                            <th style="width: 35%;">Location</th>
                            <th style="width: 15%;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${unchangedJobs.map(job => `
                            <tr>
                                <td><a href="${escapeHtml(job.job_url || '#')}" target="_blank" class="job-title-link">${escapeHtml(job.title || 'Untitled')}</a></td>
                                <td><span class="badge-loc"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(job.location || 'N/A')}</span></td>
                                <td><span style="color: #38bdf8; font-size: 12px;"><i class="fa-solid fa-check-double"></i> Identical</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        container.appendChild(section);
    }

    if (totalRenderedSections === 0) {
        container.innerHTML = `
            <div style="padding: 40px; text-align: center; color: var(--text-muted);">
                <i class="fa-solid fa-circle-check" style="font-size: 32px; margin-bottom: 12px; display: block; color: var(--accent-emerald);"></i>
                No differences found matching the selected filter (<strong>${escapeHtml(filter)}</strong>).
            </div>
        `;
    }
}

function triggerComparisonCSVDownload() {
    if (!currentComparisonData || !currentComparisonData.base_run || !currentComparisonData.target_run) {
        showToast('No comparison data ready to export');
        return;
    }
    const baseId = currentComparisonData.base_run.id;
    const targetId = currentComparisonData.target_run.id;

    window.location.href = `/runs/${targetId}/compare/${baseId}/csv`;
    showToast(`Downloading comparison CSV for Run #${baseId} vs Run #${targetId}...`);
}

function backToHistoryList() {
    document.getElementById('historyTimelineView').style.display = 'block';
    document.getElementById('historyComparisonView').style.display = 'none';
}

function closeHistoryModal() {
    const modal = document.getElementById('historyModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}

function closeHistoryModalOnBackdrop(event) {
    if (event.target.id === 'historyModal') {
        closeHistoryModal();
    }
}


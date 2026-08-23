/**
 * Adaptive Career Job Extraction Engine Frontend Client
 */

let currentData = null;

const PRESETS = {
    dell: "https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers/jobs?mode=location",
    broadcom: "https://broadcom.wd1.myworkdayjobs.com/External_Career",
    figma: "https://boards.greenhouse.io/figma",
    cisco: "https://careers.cisco.com/global/en/search-results",
    exl: "https://fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/jobs?location=India",
    hpe: "https://careers.hpe.com/us/en/search-results"
};

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
    document.getElementById('metricTotalFound').innerText = `out of ${meta.total_jobs_found || jobs.length} found`;
    document.getElementById('metricEnriched').innerText = meta.jobs_enriched || 0;
    document.getElementById('metricEnrichFailed').innerText = `${meta.jobs_enrichment_failed || 0} failed`;
    
    const atsVendor = meta.ats || meta.source_type || 'Generic';
    document.getElementById('metricATS').innerText = atsVendor.toUpperCase();
    document.getElementById('metricStrategy').innerText = `Strategy: ${meta.extraction_strategy || 'Default'}`;
    document.getElementById('metricTime').innerText = `${elapsedTime}s`;
    
    // Render Jobs Table Body
    const tbody = document.getElementById('jobsTableBody');
    tbody.innerHTML = '';
    
    if (jobs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 40px; color: var(--text-muted);">
            <i class="fa-solid fa-folder-open" style="font-size: 32px; margin-bottom: 12px; display: block;"></i>
            No job listings found for the given URL.
        </td></tr>`;
    } else {
        jobs.forEach((job, index) => {
            const tr = document.createElement('tr');
            
            const jobId = job.id || job.requisition_id || job.external_job_id || `JOB-${index + 1}`;
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
                    <button type="button" class="btn-icon" onclick="openModal(${index})" title="View Full Details">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }
    
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
    
    const headers = ['Job ID', 'Title', 'Location', 'ATS', 'Employment Type', 'Posted At', 'Responsibilities', 'Requirements', 'Skills', 'Job URL'];
    
    const rows = currentData.jobs.map(job => {
        const jobId = job.id || job.requisition_id || '';
        const title = job.title || '';
        let location = '';
        if (job.location) {
            location = typeof job.location === 'object' ? (job.location.raw || '') : String(job.location);
        }
        const ats = job.ats || (currentData.metadata ? currentData.metadata.ats : '') || '';
        const empType = job.employment_type || '';
        const postedAt = job.posted_at || '';
        const resp = (job.responsibilities || []).join('; ');
        const reqs = (job.requirements || []).join('; ');
        const skills = (job.skills || []).join('; ');
        const jobUrl = job.job_url || '';
        
        return [
            escapeCsv(jobId),
            escapeCsv(title),
            escapeCsv(location),
            escapeCsv(ats),
            escapeCsv(empType),
            escapeCsv(postedAt),
            escapeCsv(resp),
            escapeCsv(reqs),
            escapeCsv(skills),
            escapeCsv(jobUrl)
        ].join(',');
    });
    
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `job_extraction_${Date.now()}.csv`);
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

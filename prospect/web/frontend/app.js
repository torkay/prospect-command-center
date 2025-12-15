/**
 * Prospect Command Center - Frontend UI
 * Vanilla JS, no dependencies
 */

const API = '/api/v1';
let currentJobId = null;
let currentResults = [];
let ws = null;

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initStatus();
    initForm();
    initKeyboard();
    loadJobs();
});

async function initStatus() {
    try {
        const res = await fetch(`${API}/health`);
        const data = await res.json();

        document.getElementById('status-serpapi').className =
            data.serpapi ? 'text-green-400' : 'text-red-400';
        document.getElementById('status-serpapi').title =
            data.serpapi ? 'SerpAPI: Connected' : 'SerpAPI: Not configured';

        document.getElementById('status-sheets').className =
            data.sheets ? 'text-green-400' : 'text-gray-500';
        document.getElementById('status-sheets').title =
            data.sheets ? 'Sheets: Configured' : 'Sheets: Not configured';

        document.getElementById('version').textContent = `v${data.version}`;
    } catch (e) {
        console.error('Health check failed:', e);
    }
}

function initForm() {
    const form = document.getElementById('search-form');
    form.addEventListener('submit', handleSearch);

    // Export buttons
    document.getElementById('export-csv').addEventListener('click', () => exportResults('csv'));
    document.getElementById('export-json').addEventListener('click', () => exportResults('json'));
    document.getElementById('export-sheets').addEventListener('click', exportToSheets);

    // Table sorting
    document.querySelectorAll('[data-sort]').forEach(th => {
        th.addEventListener('click', () => sortResults(th.dataset.sort));
    });
}

function initKeyboard() {
    document.addEventListener('keydown', (e) => {
        // / to focus search
        if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
            e.preventDefault();
            document.querySelector('input[name="business_type"]').focus();
        }

        // Esc to clear
        if (e.key === 'Escape') {
            document.querySelector('input[name="business_type"]').blur();
        }

        // e to export
        if (e.key === 'e' && document.activeElement.tagName !== 'INPUT' && currentResults.length) {
            exportResults('csv');
        }
    });
}

// ============================================================================
// Search
// ============================================================================

async function handleSearch(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    const request = {
        business_type: formData.get('business_type'),
        location: formData.get('location'),
        limit: parseInt(formData.get('limit')) || 20,
        parallel: parseInt(formData.get('parallel')) || 3,
        skip_enrichment: formData.get('skip_enrichment') === 'on',
        filters: {
            min_fit: parseInt(formData.get('min_fit')) || 0,
            min_opportunity: parseInt(formData.get('min_opportunity')) || 0,
            min_priority: parseInt(formData.get('min_priority')) || 0,
            require_phone: formData.get('require_phone') === 'on',
            require_email: formData.get('require_email') === 'on',
        }
    };

    // UI feedback
    setLoading(true);
    showProgress();
    hideResults();

    try {
        const res = await fetch(`${API}/search`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(request)
        });

        const data = await res.json();
        currentJobId = data.id;

        // Connect WebSocket for updates
        connectWebSocket(data.id);

        // Add to jobs list
        loadJobs();

    } catch (e) {
        console.error('Search failed:', e);
        setLoading(false);
        hideProgress();
    }
}

function connectWebSocket(jobId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/jobs/${jobId}`);

    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);

        if (data.type === 'progress') {
            updateProgress(data.progress, data.total, data.message);
        } else if (data.type === 'complete') {
            hideProgress();
            setLoading(false);
            loadResults(jobId);
            loadJobs();
        } else if (data.type === 'error') {
            hideProgress();
            setLoading(false);
            alert(`Error: ${data.message}`);
        }
    };

    ws.onerror = () => {
        // Fallback to polling
        pollJobStatus(jobId);
    };
}

async function pollJobStatus(jobId) {
    const poll = async () => {
        try {
            const res = await fetch(`${API}/jobs/${jobId}`);
            const data = await res.json();

            updateProgress(data.progress, data.progress_total, data.message);

            if (data.status === 'complete') {
                hideProgress();
                setLoading(false);
                loadResults(jobId);
                loadJobs();
            } else if (data.status === 'error') {
                hideProgress();
                setLoading(false);
                alert(`Error: ${data.error}`);
            } else {
                setTimeout(poll, 500);
            }
        } catch (e) {
            console.error('Poll failed:', e);
        }
    };

    poll();
}

// ============================================================================
// Results
// ============================================================================

async function loadResults(jobId) {
    try {
        const res = await fetch(`${API}/jobs/${jobId}`);
        const data = await res.json();

        currentResults = data.results || [];
        currentJobId = jobId;

        // Update raw data
        document.getElementById('raw-data').textContent =
            JSON.stringify(data, null, 2);

        // Show results
        showResults(currentResults, data.stats);

    } catch (e) {
        console.error('Load results failed:', e);
    }
}

function showResults(results, stats) {
    document.getElementById('empty-state').classList.add('hidden');
    document.getElementById('results-header').classList.remove('hidden');

    document.getElementById('results-count').textContent = results.length;

    if (stats) {
        document.getElementById('results-stats').textContent =
            `avg fit: ${stats.avg_fit_score.toFixed(0)} | avg opp: ${stats.avg_opportunity_score.toFixed(0)}`;
    }

    renderTable(results);
}

function hideResults() {
    document.getElementById('results-header').classList.add('hidden');
    document.getElementById('results-body').innerHTML = '';
    document.getElementById('empty-state').classList.remove('hidden');
}

function renderTable(results) {
    const tbody = document.getElementById('results-body');

    tbody.innerHTML = results.map(r => `
        <tr class="border-b border-gray-700 hover:bg-gray-750">
            <td class="py-2">
                <div class="font-medium">${escapeHtml(r.name)}</div>
                <div class="text-xs text-gray-500">
                    ${r.domain ? `<a href="https://${r.domain}" target="_blank" class="text-blue-400 hover:underline">${r.domain}</a>` : ''}
                </div>
            </td>
            <td class="py-2">
                <span class="px-2 py-0.5 rounded text-xs font-bold ${scoreClass(r.fit_score)}">${r.fit_score}</span>
            </td>
            <td class="py-2">
                <span class="px-2 py-0.5 rounded text-xs font-bold ${scoreClass(r.opportunity_score)}">${r.opportunity_score}</span>
            </td>
            <td class="py-2">
                <span class="px-2 py-0.5 rounded text-xs font-bold ${scoreClass(r.priority_score)}">${Math.round(r.priority_score)}</span>
            </td>
            <td class="py-2 text-xs">
                ${r.phone ? `<div>${escapeHtml(r.phone)}</div>` : ''}
                ${r.emails && r.emails.length ? `<div class="text-gray-500">${escapeHtml(r.emails[0])}</div>` : ''}
            </td>
            <td class="py-2 text-xs text-gray-400 max-w-xs truncate" title="${escapeHtml(r.opportunity_notes || '')}">
                ${escapeHtml(r.opportunity_notes || '')}
            </td>
        </tr>
    `).join('');
}

function scoreClass(score) {
    if (score >= 60) return 'bg-green-900 text-green-300';
    if (score >= 40) return 'bg-yellow-900 text-yellow-300';
    return 'bg-red-900 text-red-300';
}

function sortResults(field) {
    currentResults.sort((a, b) => {
        const aVal = a[field] || 0;
        const bVal = b[field] || 0;
        return bVal - aVal;
    });
    renderTable(currentResults);
}

// ============================================================================
// Jobs List
// ============================================================================

async function loadJobs() {
    try {
        const res = await fetch(`${API}/jobs?limit=10`);
        const jobs = await res.json();

        const container = document.getElementById('jobs-list');

        if (jobs.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-xs">No jobs yet</p>';
            return;
        }

        container.innerHTML = jobs.map(j => `
            <div class="flex justify-between items-center p-2 rounded hover:bg-gray-700 cursor-pointer ${j.id === currentJobId ? 'bg-gray-700' : ''}"
                 onclick="loadResults('${j.id}')">
                <div>
                    <div class="text-xs">${escapeHtml(j.business_type)}</div>
                    <div class="text-xs text-gray-500">${escapeHtml(j.location)}</div>
                </div>
                <div class="text-xs ${statusClass(j.status)}">${j.status}</div>
            </div>
        `).join('');

    } catch (e) {
        console.error('Load jobs failed:', e);
    }
}

function statusClass(status) {
    switch (status) {
        case 'complete': return 'text-green-400';
        case 'error': return 'text-red-400';
        case 'running':
        case 'searching':
        case 'enriching': return 'text-yellow-400';
        default: return 'text-gray-400';
    }
}

// ============================================================================
// Export
// ============================================================================

function exportResults(format) {
    if (!currentJobId || !currentResults.length) return;

    window.open(`${API}/jobs/${currentJobId}/results?format=${format}`, '_blank');
}

async function exportToSheets() {
    if (!currentJobId || !currentResults.length) return;

    try {
        const res = await fetch(`${API}/jobs/${currentJobId}/export/sheets`, {
            method: 'POST'
        });

        const data = await res.json();

        if (data.url) {
            window.open(data.url, '_blank');
        } else if (data.detail) {
            alert(`Export failed: ${data.detail}`);
        } else {
            alert('Sheets export failed');
        }
    } catch (e) {
        alert(`Export failed: ${e.message}`);
    }
}

// ============================================================================
// UI Helpers
// ============================================================================

function setLoading(loading) {
    const btn = document.getElementById('submit-btn');
    const text = document.getElementById('submit-text');
    const spinner = document.getElementById('submit-loading');

    btn.disabled = loading;
    text.classList.toggle('hidden', loading);
    spinner.classList.toggle('hidden', !loading);
}

function showProgress() {
    document.getElementById('progress-container').classList.remove('hidden');
}

function hideProgress() {
    document.getElementById('progress-container').classList.add('hidden');
}

function updateProgress(current, total, message) {
    const pct = total > 0 ? (current / total) * 100 : 0;
    document.getElementById('progress-bar').style.width = `${pct}%`;
    document.getElementById('progress-count').textContent = `${current}/${total}`;
    document.getElementById('progress-message').textContent = message || 'Processing...';
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[c]);
}

const API_BASE_URL = ''; // The dashboard and API share the Flask origin.
let activeCSVData = null;
let pieChartInstance = null;
let barChartInstance = null;
let healthPending = false;
const CATEGORY_MAP = {
    legit: 'Likely legitimate announcement', uncertain: 'Needs verification',
    fake_covid_health: 'Fake COVID / Health Scheme',
    fake_job_offer: 'Fake Job / Recruitment Offer',
    fake_kyc_aadhaar: 'Fake KYC / Aadhaar Urgency',
    fake_lottery_prize: 'Fake Lottery / Lucky Draw',
    fake_money_transfer: 'Fake Money Transfer / Bonus',
    fake_subsidy_ration: 'Fake Subsidy / Ration Benefit',
    fake_other: 'Other suspicious message'
};
const byId = id => document.getElementById(id);

async function requestJSON(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options, signal: AbortSignal.timeout(30000)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The service is unavailable. Please try again.');
    return data;
}

function verdict(label) {
    if (label === 1) return { text: 'Likely scam', badge: 'badge-scam', color: '#b53b36', style: 'verdict-scam' };
    if (label === 0) return { text: 'Likely legitimate', badge: 'badge-legit', color: '#08735a', style: 'verdict-legit' };
    return { text: 'Needs verification', badge: 'badge-warning', color: '#926013', style: 'verdict-warning' };
}

function makeBadge(label) {
    const badge = document.createElement('span');
    const view = verdict(label);
    badge.className = `verdict-badge ${view.badge}`;
    badge.textContent = view.text;
    return badge;
}

function setupTabSwitching() {
    document.querySelectorAll('.nav-btn').forEach(button => {
        button.addEventListener('click', () => {
            const target = button.dataset.tab;
            document.querySelectorAll('.nav-btn').forEach(item => {
                const active = item === button;
                item.classList.toggle('active', active);
                item.setAttribute('aria-pressed', String(active));
            });
            document.querySelectorAll('.tab-content').forEach(item => item.classList.toggle('active', item.id === target));
            byId('page-heading').textContent = {
                'checker-tab': 'Message Checker',
                'batch-tab': 'Batch CSV Classifier',
                'analytics-tab': 'Threat Intelligence',
                'pib-tab': 'Scam Awareness'
            }[target];
            if (target === 'analytics-tab') loadAnalyticsData();
        });
    });
}

function setupWorkspaceExtras() {
    document.querySelectorAll('[data-open-tab]').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelector(`.nav-btn[data-tab="${button.dataset.openTab}"]`).click();
            byId('page-heading').scrollIntoView({ block: 'start' });
        });
    });
    const examples = {
        prize: 'CONGRATULATIONS Suresh! Aapne KBC/Sarkari Lucky Draw mein ₹5,00,000 jeeta hai. Claim karne ke liye gov-scheme-claim.xyz par registration fee bhejein.',
        hindi: 'सरकारी विभाग में आपकी नौकरी पक्की है। बिना परीक्षा नियुक्ति पत्र लेने के लिए ₹2000 हमारे यूपीआई पर भेजें।'
    };
    document.querySelectorAll('[data-example]').forEach(button => {
        button.addEventListener('click', () => {
            const input = byId('message-input');
            input.value = examples[button.dataset.example];
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.focus();
        });
    });
}

async function checkAPIHealth() {
    if (healthPending) return;
    healthPending = true;
    try {
        const data = await requestJSON('/health');
        if (!data.model_loaded || !data.vectorizer_loaded) throw new Error('Model unavailable');
        byId('status-dot').className = 'status-dot connected';
        byId('status-text').textContent = 'Ready to analyze';
    } catch {
        byId('status-dot').className = 'status-dot disconnected';
        byId('status-text').textContent = 'Service unavailable';
    } finally {
        healthPending = false;
    }
}

function renderPrediction(data) {
    const view = verdict(data.label);
    byId('result-container').classList.remove('loading-skeleton');
    byId('result-empty-state').classList.add('hidden');
    byId('result-details').classList.remove('hidden');
    const score = data.scam_probability;
    byId('gauge-fill-circle').style.strokeDashoffset = score === null ? 283 : 283 * (1 - score);
    byId('gauge-fill-circle').style.stroke = view.color;
    byId('gauge-val').textContent = score === null ? '?' : `${Math.round(score * 100)}%`;
    byId('risk-verdict').className = `risk-verdict ${view.style}`;
    byId('risk-verdict').textContent = view.text;
    byId('result-classification').textContent = CATEGORY_MAP[data.category] || data.category;
    byId('result-confidence').textContent = score === null ? 'Inconclusive' : `${(data.confidence * 100).toFixed(1)}%`;
    byId('result-note').textContent = data.uncertainty_reason || 'This is a model estimate, not confirmation from an official authority.';
    const tags = byId('trigger-tags');
    tags.replaceChildren();
    const triggers = data.triggers_found.length ? data.triggers_found : ['No obvious cues found; this does not establish authenticity.'];
    triggers.forEach(trigger => {
        const tag = document.createElement('span');
        tag.className = 'trigger-tag';
        tag.textContent = trigger;
        tags.appendChild(tag);
    });
}

function setupRealtimeChecker() {
    const input = byId('message-input');
    const analyze = byId('analyze-btn');
    let revision = 0;
    function resetResult() {
        revision++;
        byId('char-count').textContent = input.value.length;
        byId('result-empty-state').classList.remove('hidden');
        byId('result-details').classList.add('hidden');
        byId('checker-error').textContent = '';
    }
    input.addEventListener('input', resetResult);
    byId('clear-btn').addEventListener('click', () => {
        input.value = '';
        resetResult();
        input.focus();
    });
    analyze.addEventListener('click', async () => {
        const message = input.value.trim();
        if (!message) {
            byId('checker-error').textContent = 'Enter a message to analyze.';
            input.focus();
            return;
        }
        const currentRevision = revision;
        analyze.disabled = true;
        analyze.textContent = 'Analyzing...';
        byId('checker-error').textContent = '';
        try {
            const data = await requestJSON('/predict', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            if (currentRevision === revision) renderPrediction(data);
        } catch (error) {
            if (currentRevision === revision) byId('checker-error').textContent = `Analysis failed: ${error.message}`;
        } finally {
            analyze.disabled = false;
            analyze.textContent = 'Analyze Message';
        }
    });
}

function escapeCSVCell(value) {
    let text = String(value ?? '');
    // Quoting alone does not prevent spreadsheet applications from evaluating formulas.
    if (/^[\s\u0000-\u001f]*[=+\-@]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
    return `"${text.replace(/"/g, '""')}"`;
}

function buildCSV(rows) {
    const columns = ['message', 'label', 'category', 'confidence', 'status', 'uncertainty_reason'];
    return '\ufeff' + columns.join(',') + '\r\n' + rows.map(row =>
        columns.map(column => escapeCSVCell(row[column])).join(',')
    ).join('\r\n') + '\r\n';
}

function renderBatch(data) {
    activeCSVData = data.results;
    const scam = data.results.filter(row => row.label === 1).length;
    const legit = data.results.filter(row => row.label === 0).length;
    byId('batch-total').textContent = data.total_processed;
    byId('batch-scam').textContent = scam;
    byId('batch-legit').textContent = legit;
    byId('batch-uncertain').textContent = data.total_processed - scam - legit;
    byId('batch-ratio').textContent = `${Math.round(scam / data.total_processed * 100)}%`;
    const body = byId('batch-table-body');
    body.replaceChildren();
    data.results.slice(0, 15).forEach(row => {
        const tr = document.createElement('tr');
        const message = document.createElement('td');
        message.setAttribute('data-label', 'Message');
        message.className = 'msg-cell';
        message.textContent = message.title = row.message;
        const label = document.createElement('td');
        label.setAttribute('data-label', 'Verdict');
        label.appendChild(makeBadge(row.label));
        const category = document.createElement('td');
        category.setAttribute('data-label', 'Category');
        category.textContent = CATEGORY_MAP[row.category] || row.category;
        category.title = row.uncertainty_reason || '';
        const confidence = document.createElement('td');
        confidence.setAttribute('data-label', 'Confidence');
        confidence.textContent = row.label === null ? 'Inconclusive' : `${(row.confidence * 100).toFixed(1)}%`;
        tr.append(message, label, category, confidence);
        body.appendChild(tr);
    });
    byId('batch-results-summary').classList.remove('hidden');
}

function setupBatchUploader() {
    const dropzone = byId('csv-dropzone');
    const fileInput = byId('csv-file-input');
    let uploading = false;
    dropzone.addEventListener('click', event => {
        if (!uploading && event.target !== fileInput) fileInput.click();
    });
    dropzone.addEventListener('keydown', event => {
        if (!uploading && ['Enter', ' '].includes(event.key)) {
            event.preventDefault();
            fileInput.click();
        }
    });
    dropzone.addEventListener('dragover', event => {
        event.preventDefault();
        if (!uploading) dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', event => {
        event.preventDefault();
        dropzone.classList.remove('dragover');
        if (event.dataTransfer.files.length) upload(event.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) upload(fileInput.files[0]);
    });
    async function upload(file) {
        if (uploading) return;
        byId('batch-error').textContent = '';
        if (!file.name.toLowerCase().endsWith('.csv') || file.size > 2 * 1024 * 1024) {
            byId('batch-error').textContent = 'Choose a CSV file no larger than 2 MB.';
            fileInput.value = '';
            return;
        }
        uploading = true;
        activeCSVData = null;
        fileInput.disabled = true;
        dropzone.setAttribute('aria-disabled', 'true');
        byId('batch-results-summary').classList.add('hidden');
        dropzone.querySelector('h3').textContent = 'Classifying messages...';
        const form = new FormData();
        form.append('file', file);
        try {
            renderBatch(await requestJSON('/predict_batch', { method: 'POST', body: form }));
        } catch (error) {
            byId('batch-error').textContent = `Batch upload failed: ${error.message}`;
        } finally {
            uploading = false;
            fileInput.disabled = false;
            fileInput.value = '';
            dropzone.setAttribute('aria-disabled', 'false');
            dropzone.querySelector('h3').textContent = 'Drag & drop your CSV file here';
        }
    }
    byId('download-csv-btn').addEventListener('click', () => {
        if (!activeCSVData) return;
        const url = URL.createObjectURL(new Blob([buildCSV(activeCSVData)], { type: 'text/csv;charset=utf-8;' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = 'classified_messages.csv';
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
}

async function loadAnalyticsData() {
    byId('analytics-error').textContent = '';
    try {
        const data = await requestJSON('/analytics');
        byId('analytics-storage-note').textContent = data.storage_mode === 'temporary'
            ? 'Preview statistics cover up to the latest 1,000 checks on this server and may reset. Message text is not saved.'
            : 'Only classification metadata is retained; message text stays out of analytics.';
        for (const [id, value] of Object.entries({
            'ana-total-checks': data.total_checks, 'ana-scam-count': data.scam_count,
            'ana-legit-count': data.legit_count, 'ana-uncertain-count': data.uncertain_count,
            'ana-scam-ratio': `${(data.scam_ratio * 100).toFixed(1)}%`
        })) byId(id).textContent = value;
        renderRecentLogs(data.recent_checks);
        byId('charts-status').textContent = !data.total_checks ? 'No checks recorded yet.' :
            typeof Chart === 'undefined' ? 'Charts are unavailable. Counts and recent results are shown above and below.' : '';
        if (typeof Chart !== 'undefined') renderCharts(data);
    } catch (error) {
        byId('analytics-error').textContent = `Unable to refresh analytics: ${error.message}`;
    }
}

function renderCharts(data) {
    if (pieChartInstance) pieChartInstance.destroy();
    if (barChartInstance) barChartInstance.destroy();
    const options = { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#66746e', font: { family: 'DM Sans' }, boxWidth: 10, padding: 16 } } } };
    pieChartInstance = new Chart(byId('verdict-pie-chart').getContext('2d'), {
        type: 'doughnut', options,
        data: { labels: ['Likely legitimate', 'Likely scam', 'Needs verification'],
            datasets: [{ data: [data.legit_count, data.scam_count, data.uncertain_count],
                backgroundColor: ['#6b9b72', '#cf7b65', '#d4b76c'], borderWidth: 0, hoverOffset: 4 }] }
    });
    const categories = Object.keys(CATEGORY_MAP).filter(key => key.startsWith('fake_'));
    barChartInstance = new Chart(byId('category-bar-chart').getContext('2d'), {
        type: 'bar', options: { ...options, plugins: { legend: { display: false } },
            scales: { x: { ticks: { color: '#66746e', font: { size: 10 } }, grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0, color: '#66746e' }, grid: { color: '#edf1e8' } } } },
        data: { labels: categories.map(key => CATEGORY_MAP[key].replace('Fake ', '')),
            datasets: [{ data: categories.map(key => data.category_counts[key] || 0), backgroundColor: '#789c76', borderRadius: 4 }] }
    });
}

function renderRecentLogs(checks) {
    const container = byId('recent-logs-feed');
    container.replaceChildren();
    if (!checks.length) {
        container.textContent = 'No requests recorded yet.';
        return;
    }
    checks.forEach(check => {
        const item = document.createElement('div');
        item.className = 'log-feed-item';
        const left = document.createElement('div');
        left.className = 'log-left';
        const category = document.createElement('div');
        category.className = 'log-text';
        category.textContent = CATEGORY_MAP[check.category] || check.category;
        const time = document.createElement('div');
        time.className = 'log-meta';
        time.textContent = new Date(check.timestamp).toLocaleString();
        left.append(category, time);
        item.append(left, makeBadge(check.label));
        container.appendChild(item);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupTabSwitching();
    setupRealtimeChecker();
    setupBatchUploader();
    setupWorkspaceExtras();
    byId('refresh-analytics-btn').addEventListener('click', loadAnalyticsData);
    checkAPIHealth();
    setInterval(checkAPIHealth, 10000);
});

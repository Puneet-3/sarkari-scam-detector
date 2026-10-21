const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function harness() {
    class Element {
        constructor() {
            this.textContent = ''; this.value = ''; this.children = []; this.events = {};
            this.style = {}; this.attributes = {}; this.files = [];
            this.classes = new Set();
            this.classList = {
                add: name => this.classes.add(name), remove: name => this.classes.delete(name),
                toggle: (name, enabled) => enabled ? this.classes.add(name) : this.classes.delete(name)
            };
        }
        set innerHTML(value) { throw new Error('Unsafe HTML assignment'); }
        setAttribute(name, value) { this.attributes[name] = value; }
        appendChild(child) { this.children.push(child); }
        append(...children) { this.children.push(...children); }
        replaceChildren(...children) { this.children = children; }
        addEventListener(name, callback) { this.events[name] = callback; }
        focus() {}
    }
    const nodes = new Map();
    const context = vm.createContext({
        document: { getElementById(id) {
            if (!nodes.has(id)) nodes.set(id, new Element());
            return nodes.get(id);
        }, createElement: () => new Element(), addEventListener() {} },
        AbortSignal, setTimeout, setInterval() {}, console, Blob, URL,
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../../public/static/js/app.js'), 'utf8'), context);
    return { context, node: id => context.document.getElementById(id) };
}

const uncertain = {
    label: null, category: 'uncertain', confidence: 0.24, scam_probability: null,
    uncertainty_reason: 'Verify independently.', triggers_found: []
};

test('hostile trigger text is rendered literally without HTML insertion', () => {
    const { context, node } = harness();
    const payload = 'https://evil.example/<svg/onload=window.reviewMarker=1>x';
    context.renderPrediction({ ...uncertain, triggers_found: [payload] });
    assert.equal(node('trigger-tags').children[0].textContent, payload);
    assert.equal(node('risk-verdict').textContent, 'Needs verification');
    assert.equal(node('gauge-val').textContent, '?');
});

test('classified legitimate results remain estimates rather than verified claims', () => {
    const { context, node } = harness();
    context.renderPrediction({ ...uncertain, label: 0, category: 'legit', confidence: 0.95,
        scam_probability: 0.05, uncertainty_reason: null });
    assert.equal(node('risk-verdict').textContent, 'Likely legitimate');
    assert.equal(node('gauge-val').textContent, '5%');
    assert.match(node('result-note').textContent, /not confirmation/);
});

test('CSV export neutralizes formulas, including formulas hidden after whitespace', () => {
    const { context } = harness();
    for (const message of ['=1+1', '+1+1', '-1+1', '@SUM(A1)', '  =1+1', '\t=1+1', '\n=1+1']) {
        assert.ok(context.escapeCSVCell(message).startsWith('"\''), message);
    }
    assert.equal(context.escapeCSVCell('He said "hello", today'), '"He said ""hello"", today"');
    assert.equal(context.escapeCSVCell(null), '""');
    const csv = context.buildCSV([{ message: 'हिंदी', label: null, category: 'uncertain', confidence: 0.2 }]);
    assert.ok(csv.startsWith('\ufeffmessage,'));
    assert.ok(csv.includes('हिंदी'));
    assert.ok(!csv.includes('undefined'));
});

test('batch counters and badges keep uncertainty separate from legitimate messages', () => {
    const { context, node } = harness();
    context.renderBatch({ total_processed: 3, results: [
        { ...uncertain, message: 'hello' },
        { ...uncertain, label: 0, category: 'legit', message: 'legit' },
        { ...uncertain, label: 1, category: 'fake_job_offer', message: 'scam' }
    ] });
    assert.equal(node('batch-legit').textContent, 1);
    assert.equal(node('batch-scam').textContent, 1);
    assert.equal(node('batch-uncertain').textContent, 1);
    const firstRow = node('batch-table-body').children[0];
    assert.equal(firstRow.children[1].children[0].textContent, 'Needs verification');
    assert.equal(firstRow.children[3].textContent, 'Inconclusive');
});

test('clearing an input during a request prevents its stale result from appearing', async () => {
    const { context, node } = harness();
    let resolve;
    context.fetch = () => new Promise(done => { resolve = done; });
    context.setupRealtimeChecker();
    node('message-input').value = 'message under analysis';
    const pending = node('analyze-btn').events.click();
    node('clear-btn').events.click();
    resolve({ ok: true, json: async () => uncertain });
    await pending;
    assert.equal(node('message-input').value, '');
    assert.ok(node('result-details').classes.has('hidden'));
    assert.equal(node('analyze-btn').disabled, false);
});

test('analytics still displays results when the chart CDN is unavailable', async () => {
    const { context, node } = harness();
    context.fetch = async () => ({ ok: true, json: async () => ({
        total_checks: 1, scam_count: 0, legit_count: 0, uncertain_count: 1, scam_ratio: 0,
        category_counts: {}, recent_checks: [{ ...uncertain, timestamp: '2026-10-21T00:00:00Z' }]
    }) });
    await context.loadAnalyticsData();
    assert.equal(node('ana-uncertain-count').textContent, 1);
    assert.equal(node('recent-logs-feed').children.length, 1);
    assert.match(node('charts-status').textContent, /Charts are unavailable/);
});

test('cloud analytics explains temporary retention', async () => {
    const { context, node } = harness();
    context.fetch = async () => ({ ok: true, json: async () => ({
        total_checks: 0, scam_count: 0, legit_count: 0, uncertain_count: 0, scam_ratio: 0,
        category_counts: {}, recent_checks: [], storage_mode: 'temporary', max_entries: 1000
    }) });
    await context.loadAnalyticsData();
    assert.match(node('analytics-storage-note').textContent, /1,000/);
    assert.match(node('analytics-storage-note').textContent, /may reset/);
});

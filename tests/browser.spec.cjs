const { test, expect } = require('@playwright/test');
const fs = require('node:fs/promises');
const path = require('node:path');

const HINDI_SCAM = 'सरकारी विभाग में आपकी नौकरी पक्की है। बिना परीक्षा नियुक्ति पत्र लेने के लिए ₹2000 हमारे यूपीआई पर भेजें।';
const HINDI_LEGIT = 'पीएम किसान की किस्त का भुगतान पात्र किसानों के पंजीकृत बैंक खाते में किया जाता है। स्थिति स्वयं pmkisan.gov.in पर देखें।';
const ENGLISH_SCAM = 'CONGRATULATIONS Suresh! Aapne KBC/Sarkari Lucky Draw mein ₹5,00,000 jeeta hai. Claim karne ke liye gov-scheme-claim.xyz par registration fee bhejein.';
const csv = rows => 'message\n' + rows.map(row => '"' + row.replace(/"/g, '""') + '"').join('\n');

async function capture(page, testInfo, name) {
    const folder = path.join(__dirname, '..', 'reports', 'visual');
    await fs.mkdir(folder, { recursive: true });
    await page.screenshot({ path: path.join(folder, `${testInfo.project.name}-${name}.png`), fullPage: true, animations: 'disabled' });
}

async function analyze(page, message) {
    await page.getByLabel('Message to analyze', { exact: true }).fill(message);
    await page.getByRole('button', { name: 'Analyze Message', exact: true }).click();
    await expect(page.locator('#result-details')).toBeVisible();
}

test.beforeEach(async ({ page }) => {
    page.testErrors = [];
    page.on('pageerror', error => page.testErrors.push(error.message));
    await page.goto('/');
    await expect(page.locator('#status-text')).toHaveText('Ready to analyze');
});

test.afterEach(async ({ page }) => {
    expect(page.testErrors).toEqual([]);
});

test('Hindi scam and legitimate messages render correct readable results', async ({ page }, testInfo) => {
    await analyze(page, HINDI_SCAM);
    await expect(page.locator('#risk-verdict')).toHaveText('Likely scam');
    await expect(page.locator('#result-classification')).toHaveText('Fake Job / Recruitment Offer');
    await expect(page.locator('#message-input')).toHaveValue(HINDI_SCAM);
    await capture(page, testInfo, 'hindi-scam');
    await analyze(page, HINDI_LEGIT);
    await expect(page.locator('#risk-verdict')).toHaveText('Likely legitimate');
    await expect(page.locator('#result-note')).toContainText('not confirmation');
});

test('unknown input is inconclusive and clear resets the result', async ({ page }, testInfo) => {
    await analyze(page, 'hello');
    await expect(page.locator('#risk-verdict')).toHaveText('Needs verification');
    await expect(page.locator('#gauge-val')).toHaveText('?');
    await capture(page, testInfo, 'uncertain');
    await page.getByRole('button', { name: 'Clear Text' }).click();
    await expect(page.locator('#result-details')).toBeHidden();
    await expect(page.locator('#message-input')).toHaveValue('');
});

test('mixed-language CSV upload, uncertainty and safe downloadable formulas', async ({ page }, testInfo) => {
    await page.getByRole('button', { name: 'Batch CSV Classifier' }).click();
    await page.locator('#csv-file-input').setInputFiles({
        name: 'mixed.csv', mimeType: 'text/csv', buffer: Buffer.from(csv([HINDI_SCAM, HINDI_LEGIT, 'hello', '=1+1']))
    });
    await expect(page.locator('#batch-total')).toHaveText('4');
    await expect(page.locator('#batch-scam')).toHaveText('1');
    await expect(page.locator('#batch-legit')).toHaveText('1');
    await expect(page.locator('#batch-uncertain')).toHaveText('2');
    const downloaded = page.waitForEvent('download');
    await page.getByRole('button', { name: /Download Classified CSV/ }).click();
    const download = await downloaded;
    const text = await fs.readFile(await download.path(), 'utf8');
    expect(text).toContain('ह');
    expect(text).toContain('"\'=1+1"');
    expect(text).toContain('"uncertain"');
    await capture(page, testInfo, 'batch');
});

test('invalid uploads show a useful error without stale results', async ({ page }) => {
    await page.getByRole('button', { name: 'Batch CSV Classifier' }).click();
    await page.locator('#csv-file-input').setInputFiles({
        name: 'bad.csv', mimeType: 'text/csv', buffer: Buffer.from('id\n12\n')
    });
    await expect(page.locator('#batch-error')).toContainText('needs a');
    await expect(page.locator('#batch-results-summary')).toBeHidden();
});

test('hostile HTML in a trigger remains literal text', async ({ page }) => {
    const payload = '<svg onload="document.body.dataset.attacked=1">';
    await page.route('**/predict', route => route.fulfill({ json: {
        label: null, category: 'uncertain', confidence: 0.2, scam_probability: null,
        uncertainty_reason: 'Verify independently.', triggers_found: [payload]
    } }));
    await analyze(page, 'A message with an untrusted link');
    await expect(page.locator('#trigger-tags')).toHaveText(payload);
    await expect(page.locator('#trigger-tags svg')).toHaveCount(0);
    expect(await page.locator('body').getAttribute('data-attacked')).toBeNull();
});

test('clearing during a delayed request prevents a stale result', async ({ page }) => {
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    await page.route('**/predict', async route => { await gate; await route.continue(); });
    await page.locator('#message-input').fill(ENGLISH_SCAM);
    await page.getByRole('button', { name: 'Analyze Message', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Analyzing...' })).toBeVisible();
    await page.getByRole('button', { name: 'Clear Text' }).click();
    release();
    await expect(page.getByRole('button', { name: 'Analyze Message', exact: true })).toBeEnabled();
    await expect(page.locator('#result-details')).toBeHidden();
});

test('analytics, awareness and all tabs fit the viewport', async ({ page }, testInfo) => {
    await analyze(page, ENGLISH_SCAM);
    for (const name of ['Batch CSV Classifier', 'Threat Intelligence', 'Scam Awareness', 'Message Checker']) {
        await page.getByRole('button', { name, exact: false }).click();
        const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, content: document.documentElement.scrollWidth }));
        expect(dimensions.content).toBeLessThanOrEqual(dimensions.width + 1);
        if (name === 'Threat Intelligence') {
            await expect(page.locator('#recent-logs-feed .log-feed-item').first()).toBeVisible();
            const response = await page.request.get('/analytics');
            const body = await response.json();
            expect(body.recent_checks.every(row => !('message' in row))).toBeTruthy();
            await capture(page, testInfo, 'analytics');
        }
        if (name === 'Scam Awareness') {
            await expect(page.locator('#pib-tab')).toContainText('ILLUSTRATIVE EXAMPLES');
            await capture(page, testInfo, 'awareness');
        }
    }
});

test('blocked chart CDN preserves analytics and shows fallback', async ({ page }) => {
    await page.route('https://cdn.jsdelivr.net/**', route => route.abort());
    await page.reload();
    await analyze(page, ENGLISH_SCAM);
    await page.getByRole('button', { name: /Threat Intelligence/ }).click();
    await expect(page.locator('#charts-status')).toContainText('Charts are unavailable');
    await expect(page.locator('#ana-total-checks')).not.toHaveText('');
});

// Browser smoke test for the published asset routes and interactive dashboard.
const { chromium, expect } = require('@playwright/test');
const { execSync } = require('node:child_process');
const fs = require('node:fs/promises');
const path = require('node:path');

async function main() {
    const origin = new URL(process.argv[2]).origin;
    if (!origin.endsWith('.vercel.app')) throw new Error('Expected a Vercel deployment URL.');
    const link = JSON.parse(await fs.readFile(path.join(__dirname, '../.vercel/project.json'), 'utf8'));
    if (!/^prj_[a-zA-Z0-9]+$/.test(link.projectId)) throw new Error('Invalid linked project ID.');
    if (!/^team_[a-zA-Z0-9]+$/.test(link.orgId)) throw new Error('Invalid linked team ID.');
    const project = JSON.parse(execSync(
        `vercel api /v9/projects/${link.projectId} --scope ${link.orgId}`,
        { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }
    ));
    const bypass = process.env.VERCEL_AUTOMATION_BYPASS_SECRET ||
        Object.keys(project.protectionBypass || {}).find(key => project.protectionBypass[key].scope === 'automation-bypass');
    if (!bypass) throw new Error('No existing automation bypass is available.');
    const folder = path.join(__dirname, '../reports/visual');
    await fs.mkdir(folder, { recursive: true });
    const browser = await chromium.launch();
    const results = [];
    try {
        for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
            const name = viewport.width === 390 ? 'mobile' : 'desktop';
            const context = await browser.newContext({ viewport, isMobile: name === 'mobile', hasTouch: name === 'mobile' });
            // Apply the secret only to this deployment, never to third-party CDNs.
            await context.route(`${origin}/**`, route => route.continue({
                headers: { ...route.request().headers(), 'x-vercel-protection-bypass': bypass }
            }));
            const page = await context.newPage();
            const errors = [];
            const assets = {};
            page.on('pageerror', error => errors.push(error.message));
            page.on('response', response => {
                const url = new URL(response.url());
                if (url.origin === origin && url.pathname.startsWith('/static/')) {
                    assets[url.pathname] = { status: response.status(), type: response.headers()['content-type'] };
                }
            });
            await page.goto(origin, { waitUntil: 'domcontentloaded', timeout: 90000 });
            await expect(page.locator('#status-text')).toHaveText('Ready to analyze', { timeout: 60000 });
            await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(246, 247, 244)');
            expect(assets['/static/css/styles.css'].status).toBe(200);
            expect(assets['/static/css/styles.css'].type).toContain('text/css');
            expect(assets['/static/js/app.js'].status).toBe(200);
            expect(assets['/static/js/app.js'].type).toMatch(/javascript/);
            await page.screenshot({ path: path.join(folder, `vercel-${name}-dashboard.png`), fullPage: true, animations: 'disabled' });
            await page.locator('[data-example="hindi"]').click();
            await expect(page.getByLabel('Message to analyze', { exact: true })).toHaveValue(/सरकारी विभाग/);
            await page.getByRole('button', { name: 'Analyze Message', exact: true }).click();
            await expect(page.locator('#risk-verdict')).toHaveText('Likely scam', { timeout: 60000 });
            for (const tab of ['Batch CSV Classifier', 'Threat Intelligence', 'Scam Awareness', 'Message Checker']) {
                await page.getByRole('button', { name: tab, exact: false }).click();
                expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBeTruthy();
            }
            await page.screenshot({ path: path.join(folder, `vercel-${name}-result.png`), fullPage: true, animations: 'disabled' });
            expect(errors).toEqual([]);
            results.push({ viewport: name, assets, styled: true, prediction: 'Likely scam', tabs: 4, errors });
            await context.close();
        }
    } finally {
        await browser.close();
    }
    const report = { origin, checkedAt: new Date().toISOString(), results };
    await fs.writeFile(path.join(__dirname, '../reports/vercel-browser-check.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });

const { defineConfig } = require('@playwright/test');
const path = require('node:path');
module.exports = defineConfig({
    testDir: './tests', testMatch: '**/browser.spec.cjs',
    workers: 1, timeout: 45000, expect: { timeout: 10000 },
    reporter: [['list'], ['html', { open: 'never' }]],
    use: { baseURL: 'http://127.0.0.1:5088', screenshot: 'only-on-failure', trace: 'retain-on-failure' },
    projects: [
        { name: 'desktop-chromium', use: { browserName: 'chromium', viewport: { width: 1440, height: 1000 } } },
        { name: 'mobile-chromium', use: { browserName: 'chromium', viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } }
    ],
    webServer: {
        command: `"${path.join(__dirname, 'backend', '.venv', 'Scripts', 'python.exe')}" "${path.join(__dirname, 'tests', 'browser_server.py')}"`,
        url: 'http://127.0.0.1:5088/health', reuseExistingServer: false, timeout: 30000
    }
});

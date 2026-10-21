# Vercel preview deployment

Confirmed Ready and browser-verified on 2026-10-22 (Asia/Calcutta).

- Preview: https://sarkari-scam-detector-el04es4nd-puneet-s-projects46.vercel.app
- Manage: https://vercel.com/puneet-s-projects46/sarkari-scam-detector/FAM7Stb4gJq2BuXob5HNxttExk3K
- Deployment: `dpl_FAM7Stb4gJq2BuXob5HNxttExk3K`
- Target: preview, protected by Vercel authentication.
- Project: `sarkari-scam-detector`; team: `puneet-s-projects46`.

The earlier preview loaded HTML but returned HTTP 404 for both `/static/css/styles.css` and `/static/js/app.js`. Build-time asset generation happened after static route discovery, and the function excluded those files. Local browser tests did not reproduce that packaging failure.

CSS and JavaScript now live as source files in `public/static/`, included in the upload and source control. Local Flask uses those same files. Attribution is in `public/data-sources.txt`. The build validates file presence, MIME types, the dashboard and model readiness. This follows [Vercel's Flask public asset guidance](https://vercel.com/docs/frameworks/backend/flask#serving-static-assets).

The upload manifest was inspected: public assets, runtime Python, trained artifacts, dashboard HTML and build script are included. Analytics, recovery backups, credential files, training data, environments and tests are excluded. Deployment used the authenticated CLI without a Git push or credential disclosure. The Linux build used Python 3.13 and completed in 33 seconds.

Verification:

- The earlier 27-test backend baseline passed. The UI redesign passed seven JavaScript tests and 16 desktop/mobile browser tests; the build rechecked model and asset readiness.
- Chromium opened the actual deployment at 1440x1000 and 390x844 using the existing Vercel automation bypass. Its header was restricted to the deployment origin; the secret was never saved in reports or screenshots.
- CSS and JavaScript returned HTTP 200 with correct content types; computed background matched the redesigned warm white theme.
- API status reached Ready to analyze; a Hindi message produced Likely scam; all four tabs fit both viewports without horizontal overflow; no browser JavaScript errors occurred.
- Deployed screenshots were visually inspected: `reports/visual/vercel-desktop-dashboard.png` and `reports/visual/vercel-mobile-dashboard.png`. Result screenshots and `reports/vercel-browser-check.json` retain additional evidence.

Cloud analytics remains temporary, retaining up to 1,000 metadata records per instance without submitted message text. Statistics may reset or differ across instances. HTTPS origin validation trusts the Vercel TLS proxy protocol. Previously documented research model limitations remain unchanged.

Repeat deployment and live browser check:

```powershell
vercel deploy --dry --json --environment preview --scope puneet-s-projects46
vercel deploy --environment preview --scope puneet-s-projects46 -y --no-wait
vercel inspect <deployment-url> --scope puneet-s-projects46
node scripts/check_deployment.cjs <deployment-url>
```

The live browser script requires an existing automation bypass and authenticated CLI access to the linked project. It never changes deployment protection settings.

## UI redesign

The current preview contains the warm white / deep green redesign described in reports/ui-redesign.md. The real deployment was checked again in desktop/mobile Chromium: public assets HTTP 200, new theme applied, Hindi example button and scam classification functional, all four tabs fit, and no page errors. Browser evidence was refreshed in reports/vercel-browser-check.json and reports/visual/vercel-*.png.

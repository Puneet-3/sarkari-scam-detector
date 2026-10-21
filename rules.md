# Development Rules and Standards (rules.md)

This document contains instructions, constraints, coding guidelines, and package rules to ensure consistency and prevent over-engineering.

---

## 1. Technical Constraints & Allowed Tech Stack

### 1.1. Backend (Python ML & REST API)
*   **Allowed Core ML Libraries:** `scikit-learn`, `pandas`, `numpy`, `nltk`, `joblib`.
*   **Allowed Web Framework:** `Flask`, `Flask-CORS` (for cross-origin request handling).
*   **Virtual Environments:** Always run python code inside a local virtual environment (`venv`). Prevent global pip package clutter.
*   **Avoid:**
    *   *No Deep Learning frameworks (PyTorch, TensorFlow) on early runs:* Complete the classical machine learning pipeline first (TF-IDF + Logistic Regression) as a robust baseline.
    *   *No complex database systems:* Keep session data in-memory or save statistics to a lightweight JSON file (`analytics.json`) to satisfy analytics feature requirements without adding PostgreSQL/MongoDB overhead.

### 1.2. Frontend (Web Dashboard)
*   **Allowed Languages:** Standard HTML5, Vanilla JavaScript (ES6+), and CSS3.
*   **Allowed CSS Frameworks:** **None.** Tailwind CSS is strictly prohibited unless specifically requested by the user. Rely on Vanilla CSS with custom properties (CSS variables) for modern theme management.
*   **Allowed JavaScript Frameworks:** **None.** No React, Vue, or Next.js for the core dashboard unless explicitly demanded. Vanilla JS is faster, has zero compile overhead, and matches the lightweight developer profile.
*   **Allowed Libraries:** **Chart.js** via CDN for rendering analytics charts.

---

## 2. Preprocessing & Normalization Rules

Hinglish (Hindi written in Latin script) is highly irregular. Apply the following strict regex and normalization patterns during text preprocessing:

1.  **Amount/Currency Normalization:**
    *   Patterns like `₹50,000`, `Rs. 10000`, `1,00,000 rs`, `50 hazar` must be replaced by a token: `[MONEY_VALUE]`.
2.  **URL/Link Masking:**
    *   Replace links matching `http://`, `https://`, `bit.ly/`, `tinyurl.com/`, `.xyz`, `.co`, `.info`, `.online` with a token: `[URL_LINK]`.
3.  **Urgency Word Tagging:**
    *   Flag urgency keywords: `turant`, `aaj hi`, `jaldi`, `abhi`, `last date`, `urgent`, `expire`. Append an urgency feature flag or map them to a structured token: `[URGENT_CUE]`.
4.  **Punctuation Preservation:**
    *   Do not strip `!`, `₹`, `%`, `?` as they carry emotional weight in scam messages (e.g., "Badhai ho!!!"). Replace common emojis or strip them if they introduce vocabulary bloat.
5.  **Case Folding:**
    *   Lower-case all text *after* extracting currency symbols and link types to ensure term consistency (e.g., `Congratulations` and `congratulations` become identical).

---

## 3. Ponytail Design Philosophy (Lazy but Perfect)

Always choose simplicity. Remember these key guidelines:
*   **YAGNI (You Aren't Gonna Need It):** Do not write a complex database pipeline if a local file (`analytics.json`) does the job.
*   **Standard Library First:** Use Python's built-in `re`, `json`, `csv`, and `pickle`/`joblib` modules before adding external packages.
*   **No Placeholders:** All UI components, graphics, and data outputs must be fully operational and meaningful.
*   **Clean Diffs:** Keep code edits localized and document the rationale behind significant modifications.

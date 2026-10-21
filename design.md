# Design System & UI Specification (design.md)

This document specifies the design tokens, visual assets, styling rules, and layout structures for the **Sarkari Scam Detector** web interface, adhering to modern UI/UX principles.

---

## 1. Visual Theme: "Cyber Security & Trust"
The interface should feel like a modern security dashboard — dark, clean, professional, and visually engaging. We use a **sleek dark mode** with high-contrast color coding to denote risk.

### 1.1. Color Palette (CSS Custom Properties)
```css
:root {
  /* Backgrounds & Canvas */
  --bg-primary: #0a0e17;       /* Very deep space-blue/gray */
  --bg-secondary: #121824;     /* Cards and containers */
  --bg-tertiary: #1b2336;      /* Active tabs, hover states */
  
  /* Borders & Dividers */
  --border-color: #243049;     /* Subtle separator lines */
  --glass-border: rgba(255, 255, 255, 0.05);

  /* Typography */
  --text-primary: #f3f4f6;     /* Off-white */
  --text-secondary: #9ca3af;   /* Soft gray */
  --text-muted: #6b7280;       /* Darker gray for footnotes */

  /* Status Accents (Tailored) */
  --color-legit: #10b981;      /* Emerald green (Safe) */
  --color-scam: #ef4444;       /* Ruby red (Danger/Scam) */
  --color-warning: #f59e0b;    /* Amber yellow (Urgent/Medium Confidence) */
  --color-brand: #3b82f6;      /* Cyber blue (Accent/Links/Buttons) */
  
  /* Gradients */
  --grad-legit: linear-gradient(135deg, #059669, #10b981);
  --grad-scam: linear-gradient(135deg, #dc2626, #ef4444);
  --grad-brand: linear-gradient(135deg, #1d4ed8, #3b82f6);
  --grad-card: linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0) 100%);
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}
```

---

## 2. Typography
*   **Primary Font:** `Inter` (sans-serif) or `Outfit` via Google Fonts.
*   **System Fallbacks:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`.
*   **Weights:** Light (300), Regular (400), Medium (500), Semi-Bold (600), Bold (700).

---

## 3. UI Components & Layout Grid

### 3.1. Main Layout
*   **Structure:** Responsive two-column dashboard.
    *   *Sidebar:* Minimal logo, menu/tabs (Checker, Batch, Analytics, Verified PIB Info).
    *   *Main Panel:* Header with status (API Connection indicator), followed by active workspace window.
*   **Layout Grid:** CSS Grid for layout organization, switching to single-column flex direction on mobile screens (max-width: 768px).

### 3.2. Glassmorphic Cards
*   Apply subtle blur, semitransparent borders, and a light gradient background:
    ```css
    .glass-card {
      background: var(--bg-secondary);
      background-image: var(--grad-card);
      border: 1px solid var(--glass-border);
      border-radius: 12px;
      backdrop-filter: blur(12px);
      box-shadow: var(--shadow-lg);
      padding: 24px;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .glass-card:hover {
      border-color: rgba(255, 255, 255, 0.1);
      transform: translateY(-2px);
    }
    ```

### 3.3. Real-time Risk Gauge
*   A circular SVG dial or linear progress bar showing confidence level.
*   **Color-shifting logic (JS-driven):**
    *   Confidence < 40%: Green (`--color-legit`).
    *   Confidence 40% - 70%: Amber (`--color-warning`).
    *   Confidence > 70%: Red (`--color-scam`).

### 3.4. Drag-and-Drop Dropzone
*   Dotted border layout. On dragover, borders pulse and turn to `--color-brand`.
*   Displays file name and upload progress bar, changing to green on completion.

---

## 4. Micro-interactions & Animations
1.  **Pulse Indicators:** The API status dot has a soft breathing pulse animation (scale & opacity) to represent active server connection.
2.  **Smooth Tabs:** Content transitions use a quick fade-in-up animation:
    ```css
    @keyframes fadeInUp {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    .tab-content.active {
      display: block;
      animation: fadeInUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    ```
3.  **Active Buttons:** Linear gradient transitions on hover/focus with a slight scale down (`scale(0.98)`) on active mouse clicks to give tactile feedback.

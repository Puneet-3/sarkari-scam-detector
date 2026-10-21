# Architecture Document (arch.md)

This document outlines the architecture, data flow, and file/folder organization of the **Sarkari Scam Detector** system.

---

## 1. System Architecture Diagram

```mermaid
graph TD
    subgraph Frontend [Web Dashboard - Vanilla HTML/JS/CSS]
        UI[Single Page App UI]
        RealTimeTab[Real-time Message Checker]
        BatchTab[Batch CSV Classifier]
        DashboardTab[Analytics & Metrics Dashboard]
    end

    subgraph Backend [Flask API Server - Python]
        API[Flask App: app.py]
        PredictRoute[/predict endpoint]
        BatchRoute[/predict_batch endpoint]
        StatsRoute[/analytics endpoint]
    end

    subgraph Core_ML_Engine [NLP Pipeline & Model]
        Cleaner[Code-Mixed Text Cleaner & Normalizer]
        Vectorizer[TF-IDF Vectorizer]
        Model[Logistic Regression Classifier]
        ModelSaver[Model Artifacts: model.pkl, vectorizer.pkl]
    end

    %% Data flow connections
    UI -->|JSON Request| API
    API -->|Routing| PredictRoute
    API -->|Routing| BatchRoute
    API -->|Routing| StatsRoute
    
    PredictRoute -->|Text Input| Cleaner
    Cleaner -->|Cleaned Text| Vectorizer
    Vectorizer -->|Sparse Feature Vector| Model
    Model -->|Inference & Probabilities| PredictRoute
    
    PredictRoute -->|JSON Response| UI
    BatchRoute -->|CSV Response| UI
    StatsRoute -->|Stats JSON| UI

    %% Loading weights
    ModelSaver -->|Load Weights| Model
    ModelSaver -->|Load Vocabulary| Vectorizer
```

---

## 2. Technical Components

### 2.1. Frontend Layer
*   **Structure:** Single-page dashboard structured using Semantic HTML5.
*   **Logic:** Native JavaScript (ES6+) utilizing `Fetch API` for asynchronous communication with the Flask backend.
*   **Styling:** Custom Vanilla CSS3 implementing a cohesive design system (sleek dark mode, custom glassmorphism, responsive CSS Grid and Flexbox). No heavy external CSS libraries (e.g., Tailwind) or component libraries.
*   **Charts:** Lightweight chart rendering using **Chart.js** via CDN or native SVGs for performance and micro-animations.

### 2.2. Backend REST API Layer
*   **Framework:** **Flask** with **Flask-CORS** enabled to allow cross-origin requests from the frontend app.
*   **Endpoints:**
    *   `POST /predict`: Input: `{"message": "string"}`. Output: `{"label": 0/1, "confidence": float, "category": "string", "triggers_found": []}`.
    *   `POST /predict_batch`: Input: Multipart form-data with CSV file. Output: JSON list of records or a direct classified CSV download.
    *   `GET /analytics`: Output: Summary statistics of queries processed (total counts, scam category ratio, average confidence).

### 2.3. NLP & ML Pipeline (Core Engine)
*   **Hinglish Preprocessor:** A dedicated Python class (`HinglishPreprocessor`) containing rules for:
    *   *URL Removal / Labeling:* Stripping links but flagging their presence.
    *   *Amount Normalization:* Standardizing ₹, Rs, rupees, and numeric ranges (e.g., Rs. 50,000 / 50000) to a uniform `[MONEY_VALUE]` token.
    *   *Urgency Tagging:* Flagging key urgency words (`turant`, `aaj hi`, `verify karein`).
    *   *Punctuation Cleaning:* Retaining critical signals like `!` and `?` while stripping redundant characters.
*   **Vectorization:** TF-IDF Vectorizer with customized tokenization and n-gram ranges (e.g., `ngram_range=(1, 2)`) to capture multi-word Hinglish cues.
*   **Classifier:** Logistic Regression trained with `class_weight='balanced'` to offset the mild dataset imbalance.

---

## 3. Directory & Folder Structure

We will structure the project under `C:\Users\punee\OneDrive\Desktop\Project\scam detector` to keep code modular, reusable, and easy to maintain.

```
scam detector/
│
├── dataset_final.csv             # Raw combined dataset (1800 rows)
├── train.csv                     # Stratified training subset
├── test.csv                      # Stratified test subset
├── Sarkari_Scam_Detector_Project_Report.docx # Historical project report
│
├── prd.md                        # Product Requirements
├── arch.md                       # Architecture & Structure
├── rules.md                      # Development Rules & Standards
├── phases.md                     # Implementation Plan
├── design.md                     # Design & CSS Specification
├── memory.md                     # Project Memory
│
├── backend/                      # Python Flask Backend
│   ├── app.py                    # Flask API Main Entrypoint
│   ├── train_model.py            # Model training & serialization script
│   ├── preprocess.py             # Hinglish Preprocessor class
│   ├── requirements.txt          # Python dependencies
│   └── artifacts/                # Serialized model and vectorizer
│       ├── model.pkl             # Trained Logistic Regression model
│       └── vectorizer.pkl        # Fitted TF-IDF Vectorizer
│
└── frontend/                     # Web Application Frontend
    ├── index.html                # Main Page Dashboard Structure
    ├── css/
    │   └── styles.css            # Custom Premium CSS (Aesthetics)
    └── js/
        └── app.js                # Core JS Logic & API Integration
```

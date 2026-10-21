# Implementation Phases (phases.md)

This document breaks down the development of the **Sarkari Scam Detector** into 5 distinct execution phases, detailing goals, tasks, and validation steps.

---

## Phase 1: Environment Setup & Hinglish Preprocessing Pipeline
*   **Goal:** Establish a localized Python environment, import existing datasets, and build the custom Hinglish preprocessor.
*   **Tasks:**
    1.  Create a virtual environment (`venv`) inside the `backend` folder.
    2.  Create `requirements.txt` with `flask`, `flask-cors`, `pandas`, `scikit-learn`, `nltk`, `joblib`.
    3.  Create `preprocess.py` and implement the `HinglishPreprocessor` class containing:
        *   Regex-based URL normalization to `[URL_LINK]`.
        *   Regex-based currency/amount normalization to `[MONEY_VALUE]`.
        *   Urgency token mapping.
        *   Basic punctuation isolation.
    4.  Verify preprocessing logic by running a test script with sample messages.

---

## Phase 2: Model Training & Tuning (Baseline)
*   **Goal:** Build, train, evaluate, and save a TF-IDF + Logistic Regression classification model.
*   **Tasks:**
    1.  Create `train_model.py`.
    2.  Load `train.csv` and `test.csv` (or split `dataset_final.csv` if needed).
    3.  Apply `HinglishPreprocessor` to clean the training and test texts.
    4.  Fit a `TfidfVectorizer` (with custom tokenization and `ngram_range=(1,2)`).
    5.  Train a `LogisticRegression` classifier using `class_weight='balanced'`.
    6.  Perform hyperparameter tuning (regularization strength `C`) using `GridSearchCV`.
    7.  Evaluate model performance (print accuracy, precision, recall, F1-score, and confusion matrix).
    8.  Serialize and save the trained model and fitted vectorizer to `backend/artifacts/` using `joblib` or `pickle`.

---

## Phase 3: Flask Backend API Development
*   **Goal:** Build a lightweight, reliable REST API server to expose model predictions.
*   **Tasks:**
    1.  Create `app.py` in the `backend/` directory.
    2.  Load the model and vectorizer artifacts on server startup.
    3.  Implement `POST /predict`:
        *   Accept JSON payload `{"message": "..."}`.
        *   Preprocess message.
        *   Extract prediction label and confidence probability.
        *   Identify matching keywords/triggers to send as metadata.
        *   Log prediction transaction to a local `analytics.json` file.
    4.  Implement `POST /predict_batch`:
        *   Accept CSV file, parse rows, classify each message, and return JSON list or classified CSV.
    5.  Implement `GET /analytics`:
        *   Read from `analytics.json` and return aggregate metrics (total checks, scam ratio, category counts).
    6.  Enable CORS and test endpoints using `curl` or a python test script.

---

## Phase 4: Frontend UI Development (Premium Web Dashboard)
*   **Goal:** Create a visually stunning, responsive single-page web dashboard integrated with the Flask backend.
*   **Tasks:**
    1.  Create `frontend/index.html` structure with semantic tags: Header, Sidebar/Navigation, Main Grid, Active Pane, Footer.
    2.  Create `frontend/css/styles.css` with a sleek dark-mode glassmorphism design:
        *   Vibrant accent colors: Emerald green for Legit (Safety), Deep Crimson/Ruby for Scam (Warning).
        *   Smooth transition effects and hover animations.
        *   Custom layout styling for text input, file dropzone, and metric cards.
    3.  Create `frontend/js/app.js` to handle interactive features:
        *   **Real-time Check:** Send pasted text to `POST /predict` and update the safety gauge and trigger explanation list dynamically.
        *   **Batch Check:** Implement a drag-and-drop CSV uploader sending file to `POST /predict_batch`, displaying results in a table with a download link.
        *   **Analytics Dashboard:** Load metrics from `GET /analytics` and render charts using Chart.js (e.g., bar chart of scam categories, pie chart of scam vs legit).

---

## Phase 5: Verification, Validation & Final Polish
*   **Goal:** Validate system functionality, test model generalization, and refine documentation.
*   **Tasks:**
    1.  Execute manual testing of the web app with unseen test cases (real messages from PIB Fact Check).
    2.  Document the final evaluation metrics (accuracy, recall, precision, F1) on the test dataset.
    3.  Polish repository layout and write a comprehensive README.

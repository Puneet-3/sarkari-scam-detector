# Project Requirement Document (PRD)

## Project Name: Sarkari Scam Detector (Hindi/Hinglish Fake Government Scheme Classifier)

---

## 1. Executive Summary & Problem Statement
In India, millions of citizens receive fraudulent messages via SMS and WhatsApp. These messages impersonate legitimate government initiatives (such as *PM Kisan Samman Nidhi*, *Ayushman Bharat*, *PM Awas Yojana*, etc.) to swindle money under the guise of processing fees, KYC verification, fake lottery wins, or COVID relief. 

Because these messages are typically written in **Hindi, Hinglish (Hindi written in Roman script), or code-mixed Hindi-English**, standard spam filters trained on English fail to detect them. 

The **Sarkari Scam Detector** is an NLP-powered classification system that identifies fake government scheme messages in Hinglish/Hindi. The project includes a machine learning model, a robust pre-processing pipeline for code-mixed text, a REST API backend, and a premium frontend web application for real-time scam verification and analytics.

---

## 2. Target Audience
1. **Rural & Semi-Urban Citizens:** The primary targets of these scams, who need a simple interface (or a backend bot like WhatsApp) to forward a message and verify its authenticity.
2. **Fact-Checking Agencies / Admins:** Professionals verifying reports of circulating scams who need a dashboard to analyze scam trends, download reports, and inspect classification confidence scores.
3. **Recruiters/Interviewers (Portfolio):** To showcase robust end-to-end Machine Learning, NLP, Software Engineering, and UI/UX design skills.

---

## 3. Product Features & Requirements

### 3.1. Core NLP & ML Classification Engine
*   **Binary Classification:** Predict if a message is `SCAM` (label=1) or `LEGIT` (label=0).
*   **Multi-Category Classification (Scam Types):** If classified as a scam, identify the sub-category:
    1.  *Fake Money Transfer / Scheme Benefit* (`fake_money_transfer`)
    2.  *Fake Job Offer / Sarkari Naukri* (`fake_job_offer`)
    3.  *Fake Subsidy / Ration Card Update* (`fake_subsidy_ration`)
    4.  *Fake KYC / Aadhaar / PAN Urgency* (`fake_kyc_aadhaar`)
    5.  *Fake Lottery / Prize Won* (`fake_lottery_prize`)
    6.  *Fake COVID / Health Scheme* (`fake_covid_health`)
*   **Confidence Score:** Output a probability score (0% to 100%) indicating prediction confidence.
*   **Explainable NLP Cues:** Highlight critical triggers in the text (e.g., urgency words like *turant*, *aaj hi*; suspicious links; fake official titles).

### 3.2. User Interface (Web Dashboard)
A premium, dark-mode responsive web interface containing:
*   **Real-time Message Checker:** Input box for users to paste a message and instantly check if it is a scam. Shows a visual safety gauge, confidence percentage, detected category, and key trigger words.
*   **Batch File Uploader:** Drag-and-drop CSV upload to classify multiple messages at once. Shows a summary of results (total processed, scam count, legit count) with a downloadable classified CSV.
*   **Interactive Analytics Dashboard:** Visualizations representing scam categories, most frequent scam words/triggers, and model performance metrics.
*   **PIB Fact-Check Portal Emulator:** Displays verified alerts and explains common scam tactics.

### 3.3. Backend API
*   **Flask REST API:** Lightweight server exposed at port `5000` (or dynamic port) with:
    *   `/predict` (POST): Accepts message text, returns label, confidence, category, and extracted features/keywords.
    *   `/predict_batch` (POST): Accepts a CSV file, processes messages in batch, returns list of predictions.
    *   `/analytics` (GET): Returns aggregate metrics from processed requests for the frontend dashboard.

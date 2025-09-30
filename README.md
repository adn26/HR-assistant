# 🧑‍💼HR AI Agent – Autonomous Recruitment System

An intelligent, modular AI agent that autonomously parses resumes, ranks candidates against a job description, schedules interviews on Google Calendar, and sends personalized confirmation emails.

## 📑Contents
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [End-to-End Flow (Agent Lifecycle)](#end-to-end-flow-agent-lifecycle)
- [Local Setup (Backend + Frontend)](#local-setup-backend--frontend)
- [Configuration (.env and OAuth)](#configuration-env-and-oauth)
- [API Reference](#api-reference)
- [Usage Guide](#usage-guide)
- [Troubleshooting & FAQs](#troubleshooting--faqs)
- [Security Notes](#security-notes)

---

## ⚙️Features
- Frontend (Next.js)
  - Job Description entry (context for parsing/ranking)
  - Batch PDF resume upload
  - Ranked candidate review with score, summary, strengths/gaps, recommendation badge
  - Selection and interview date picker
  - Professional iconography via Font Awesome
- Backend (FastAPI)
  - Resume parsing: PDF chunking, semantic retrieval, LLM info extraction
  - Candidate ranking: multi-criteria evaluation with LLM
  - Scheduling: Google Calendar event creation (or prefilled link fallback)
  - Email: personalized HTML confirmations via LLM or fallback template
  - Health endpoint, clear modular services

---

## 🛠️Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│  - JD Input     - Upload Resumes  - Review & Select          │
│  - Pick Date    - Trigger Scheduling                         │
└───────────────▲─────────────────────────────────────────────┘
                │ REST (JSON)
┌───────────────┴─────────────────────────────────────────────┐
│                         FastAPI                              │
│  main.py                                                     │
│   • POST /job_description/                                   │
│   • POST /upload_resumes/                                    │
│   • GET  /candidates/                                        │
│   • POST /select_candidates/                                 │
│                                                               │
│  resume_parser.py     candidate_ranker.py     scheduler.py    │
│   • PDF → chunks      • LLM eval JSON         • Google API    │
│   • embed+retrieve    • score/summarize       • create events │
│   • LLM extract       • sort by score                           │
│                                                               │
│  email_service.py                                           │
│   • LLM HTML body or fallback template                       │
│   • SMTP send (mock if not configured)                        │
└──────────────────────────────────────────────────────────────┘
```

Key modules:
- `resume_parser.py`: PyPDFLoader + text splitter + SentenceTransformers embeddings + cosine retrieval to extract relevant resume text, then Generative AI (Gemini) to produce a structured candidate JSON.
- `candidate_ranker.py`: Prompts the LLM with JD + candidate profile to generate a normalized evaluation (score, match%, strengths/gaps, recommendation).
- `scheduler.py`: Creates Calendar events through OAuth (desktop client) and returns event links. If credentials are absent, returns prefilled calendar create links as a safe fallback.
- `email_service.py`: Generates personalized HTML emails via LLM with a robust fallback template; sends via SMTP or mock if not configured.

---

## End-to-End Flow (Agent Lifecycle)
1) HR posts Job Description (JD)
2) HR uploads PDFs; backend parses each resume (LLM-guided extraction)
3) Backend ranks candidates against JD (LLM evaluation)
4) HR selects candidates and picks a date
5) Backend schedules interviews (Google Calendar) sequentially and returns links
6) Backend sends personalized confirmation emails

Resilience:
- If AI model fails, resume parsing and ranking fallback to safe defaults.
- If Google OAuth not ready, returns prefilled calendar links so HR can click-to-create.
- If SMTP not configured, email sending is mocked with clear status.

---

## Local Setup

Prerequisites
- Python 3.12
- Node.js 18+
- Google Cloud project with Calendar API enabled
- OAuth Client ID (Desktop app)

Backend
- Create and activate venv (example):
  - Windows PowerShell
    - `python -m venv venv`
    - `./venv/Scripts/Activate.ps1`
- Install dependencies (ensure the installed packages match imports):
  - FastAPI, uvicorn, python-dotenv, google-auth, google-auth-oauthlib, google-api-python-client, sentence-transformers, scikit-learn, langchain-community, pypdf (via PyPDFLoader chain), google-generativeai (`google.genai`).
- Environment file: `backend/.env`
  - `AI_API_KEY=YOUR_GEMINI_API_KEY`
  - `SMTP_SERVER=smtp.gmail.com`
  - `SMTP_PORT=587`
  - `SENDER_EMAIL=your_email@example.com` (optional during mock)
  - `SENDER_PASSWORD=your_app_password` (optional during mock)
  - `SENDER_NAME=Your HR Team`
  - Optional Google paths:
    - `GOOGLE_CREDENTIALS_PATH=D:\Adnan\hr_ai_agent\backend\credentials-desktop.json`
    - `GOOGLE_TOKEN_PATH=D:\Adnan\hr_ai_agent\backend\token.pickle`
- Start backend:
  - `cd backend`
  - `../venv/Scripts/uvicorn.exe main:app --host 0.0.0.0 --port 8000`

Frontend
- `cd frontend`
- `npm install`
- `npm run dev`
- Open `http://localhost:3000`

---

## Configuration (OAuth & Credentials)
- OAuth client type must be “Desktop app” for the built-in loopback flow.
- Place `credentials-desktop.json` anywhere and set `GOOGLE_CREDENTIALS_PATH` to its absolute path.
- First scheduling triggers OAuth; the app opens a browser. If browser cannot open, it falls back to console flow. After consent, a refreshable `token.pickle` is written at `GOOGLE_TOKEN_PATH` (or next to `scheduler.py` by default).
- If the consent screen is in “Testing”, add your Google account under Test Users. Delete `token.pickle` to re-consent.

Email (optional)
- For Gmail, use an App Password (requires 2FA). If not configured, app mock-sends.

---

## API Reference
- `POST /job_description/` { job_description: string } → 200 { message, jd }
- `POST /upload_resumes/` multipart files[] → 200 { candidates[] }
- `GET /candidates/` → 200 { candidates[] }
- `POST /select_candidates/` { candidate_indices[], interview_date: YYYY-MM-DD, interview_duration } → 200 { scheduled_interviews[], email_status[] }
- `GET /health/` → { status, candidates_count }

Candidate object (typical fields)
- id, name, email, phone, skills[], experience_years, summary, score, match_percentage, recommendation

---

## Usage Guide
1) Enter a descriptive JD and save.
2) Upload one or more PDF resumes and process.
3) Review ranked candidates; optionally quick-select top N.
4) Pick an interview date; schedule.
5) Click “View in Calendar” (if mock) or use the returned `calendar_link` to confirm real events.

Notes
- The UI uses sequential panels (no explicit step labels) for clarity.
- Hydration-safe date min is applied post-mount.

---

## Troubleshooting & FAQs
- AI_API_KEY not set → 400 “No valid resumes processed”
  - Fix: set in `backend/.env`, restart backend.
- Google 400 redirect_uri_mismatch
  - Use “Desktop app” OAuth client. Don’t manually add dynamic localhost ports.
- Google 403 access_denied (unverified)
  - Add your account to Test Users on the OAuth consent screen or publish the app.
- `credentials.json` not found
  - Set `GOOGLE_CREDENTIALS_PATH` absolute path (no quotes) or place `credentials.json` next to `scheduler.py`.
- Emails not sending (SMTP 535)
  - Use Gmail App Password or leave unset to mock-send during development.

---

## Security Notes
- Secrets (`backend/.env`, credentials JSON, token.pickle) are ignored by Git via root `.gitignore`.
- LLM outputs are sanitized for JSON extraction, with fallbacks.
- Avoid uploading PII to third-party services without consent; configure enterprise-grade providers as needed.

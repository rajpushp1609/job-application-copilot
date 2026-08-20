# 🚀 Job Application Copilot

An AI-powered Chrome extension and automation toolkit that streamlines job applications. It auto-fills forms, answers screening questions using AI, tracks applications, and works across LinkedIn, Greenhouse, Lever, Ashby, and other major job portals.

---

## ✨ Features

- **Chrome Extension** — Side panel UI with 1-click auto-fill for job application forms
- **AI-Powered Answers** — Uses Google Gemini to generate contextual answers to screening questions
- **Multi-Portal Support** — Works on LinkedIn Easy Apply, Greenhouse, Lever, Ashby HQ, and more
- **Question Bank** — Learns from your past answers and reuses them for similar questions
- **Application Tracker** — Dashboard to view and manage all your job applications
- **Agent Framework** — Modular Python agents for discovery, evaluation, and automated application
- **Resume Builder** — PDF resume generation from structured data

---

## 📁 Project Structure

```
├── extension/                # Chrome extension (Manifest V3)
│   ├── manifest.json         # Extension config
│   ├── background.js         # Service worker
│   ├── content.js            # Content script for form detection & filling
│   ├── sidepanel.html/js     # Side panel UI
│   └── styles.css            # Extension styles
│
├── agents/                   # Python agent framework
│   ├── config.py             # Configuration & profile loader
│   ├── copilot.py            # Copilot orchestration logic
│   ├── application.py        # Application submission agent
│   ├── answers.py            # AI answer generation
│   ├── discovery.py          # Job discovery agent
│   ├── evaluation.py         # Job-role match scoring
│   ├── gemini_engine.py      # Google Gemini API integration
│   ├── job_scraper.py        # Job listing scraper
│   ├── orchestrator.py       # Multi-agent orchestrator
│   ├── tracker.py            # Application status tracker
│   └── models.py             # Data models
│
├── dashboard/                # Web dashboard for tracking applications
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── server.py                 # Backend server for the automation pipeline
├── run.py                    # CLI entry point
├── build_resume_pdf.py       # Resume PDF generator
├── build_job_tracker.mjs     # Job tracker builder
├── requirements.txt          # Python dependencies
│
├── profile.example.json      # ← Template: your personal profile
├── .env.example              # ← Template: API keys & secrets
├── job_application_policy.example.md  # ← Template: job preferences
└── data/
    └── question_bank.example.json     # ← Template: screening Q&A bank
```

---

## 🛠️ Setup Guide

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for the tracker builder)
- **Google Chrome** (for the extension)
- **Google Gemini API Key** — Get one from [Google AI Studio](https://aistudio.google.com/apikey)

### 1. Clone the Repository

```bash
git clone https://github.com/rajpushp1609/job-application-copilot.git
cd job-application-copilot
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GMAIL_EMAIL=your.email@gmail.com        # Optional: for Google Forms auth
GMAIL_PASSWORD=your_app_password_here    # Optional: use Gmail App Password
```

### 3. Set Up Your Profile

```bash
cp profile.example.json profile.json
```

Edit `profile.json` with your details:

```json
{
  "name": "Your Name",
  "email": "your.email@example.com",
  "phone": "0000000000",
  "current_company": "Your Company",
  "linkedin": "https://www.linkedin.com/in/your-profile/",
  "location": "Your City, Country",
  "notice_period_days": 30,
  "total_experience_years": 3,
  "resume_path": "output/pdf/your_resume.pdf",
  "experience_stories": {
    "story_1": "A key achievement relevant to target roles..."
  }
}
```

### 4. Set Up Job Application Policy

```bash
cp job_application_policy.example.md job_application_policy.md
```

Edit the file to define:
- **Target roles** you want to apply for
- **Preferred locations** and work arrangements
- **Compensation details** (Current & Expected CTC)
- **Content rules** for tailoring answers

### 5. Set Up Question Bank

```bash
cp data/question_bank.example.json data/question_bank.json
```

Add your pre-written answers for common screening questions. The AI will use these as a reference and also learn new answers over time.

### 6. Install Python Dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 7. Place Your Resume

Put your resume PDF at the path specified in `profile.json` → `resume_path`. By default:

```
output/pdf/your_resume.pdf
```

---

## 🧩 Install the Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (top right toggle)
3. Click **"Load unpacked"**
4. Select the `extension/` folder from this project
5. The **Job Copilot** icon will appear in your toolbar
6. Click it to open the side panel on any job application page

---

## 🚀 Usage

### Chrome Extension (Copilot Mode)

1. Navigate to a job application page (LinkedIn, Greenhouse, Lever, etc.)
2. Open the Job Copilot side panel
3. Click **"Auto-Fill"** to populate form fields with your profile data
4. Review AI-generated answers for screening questions
5. Submit when satisfied

### Backend Server

```bash
python server.py
```

The server provides the automation pipeline for:
- Job discovery and scraping
- AI-powered form filling
- Application tracking

### Dashboard

Open `dashboard/index.html` in a browser to view and manage your tracked applications.

### CLI

```bash
python run.py
```

---

## 🔒 Privacy & Security

Your personal data stays **100% local**. The following files contain sensitive information and are **excluded from the repository** via `.gitignore`:

| File | Contains |
|------|----------|
| `.env` | API keys, email credentials |
| `profile.json` | Name, email, phone, LinkedIn, CTC |
| `job_application_policy.md` | Salary expectations, job preferences |
| `data/question_bank.json` | Your personal Q&A answers |
| `data/archived_jobs.json` | Application history |
| `tracker_live/` | Live application tracking data |
| `.agents/` | Agent rules with personal form-fill values |

> ⚠️ **Never commit these files to a public repo.** Use the provided `.example` templates to create your own local copies.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome-feature`)
3. Commit your changes (`git commit -m 'Add awesome feature'`)
4. Push to the branch (`git push origin feature/awesome-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

- [Google Gemini](https://ai.google.dev/) for AI-powered answer generation
- Built with ❤️ to make job hunting less painful

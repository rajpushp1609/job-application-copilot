# Workspace Agent Rules - Job Application Automation

## Project-Specific Execution Rules

1. **Screening & Bot Questions**:
   - For screening questions asking "Are you a Robot?" or "Are you a bot?", always select or answer **"No"** (acting on behalf of Pushp Raj).

2. **Form Field Resolutions**:
   - `Experience` / `Experience*` input field must be populated with `3.5` (Pushp's total experience in years).
   - `Current CTC` (in LPA = `25`, absolute annual integer = `2500000`).
   - `Expected CTC` (in LPA = `27`, absolute annual integer = `2700000`).
   - First Name = `Pushp`, Last Name = `Raj`.

3. **Google Forms & External Authentication**:
   - Support Gmail / Google Account login (`GMAIL_EMAIL`, `GMAIL_PASSWORD` in `.env`) when external application links navigate to Google Forms requiring authentication.

4. **Easy Apply Resume Policy**:
   - Do not re-upload a resume file during LinkedIn Easy Apply; use the pre-selected `Pushp_Raj_Resume_Revised.pdf` on the logged-in account.

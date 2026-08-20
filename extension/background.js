// Background Service Worker for Job Copilot Extension

const BACKEND_URL = "http://127.0.0.1:8000";

// Enable Side Panel on extension icon click
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch((error) => console.error(error));

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "GENERATE_AI_ANSWER") {
    fetch(`${BACKEND_URL}/api/generate-answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: request.question,
        company: request.company || "",
        role: request.role || ""
      })
    })
      .then(res => res.json())
      .then(data => sendResponse({ status: "SUCCESS", answer: data.answer, source: data.source }))
      .catch(err => sendResponse({ status: "ERROR", error: err.toString() }));
    return true; // Keep channel open for async response
  }

  if (request.action === "UPDATE_QUESTION_BANK") {
    fetch(`${BACKEND_URL}/api/question-bank/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: request.question,
        answer: request.answer
      })
    })
      .then(res => res.json())
      .then(data => sendResponse({ status: "SUCCESS", data: data }))
      .catch(err => sendResponse({ status: "ERROR", error: err.toString() }));
    return true;
  }

  if (request.action === "MARK_JOB_APPLIED") {
    fetch(`${BACKEND_URL}/api/jobs/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: request.url,
        company: request.company || "",
        role: request.role || ""
      })
    })
      .then(res => res.json())
      .then(data => sendResponse({ status: "SUCCESS", data: data }))
      .catch(err => sendResponse({ status: "ERROR", error: err.toString() }));
    return true;
  }
});

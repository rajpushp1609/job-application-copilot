// Sidepanel Interactive Logic for Job Copilot (Enhanced Tab Tracking & Dynamic Rescan)

let currentFields = [];
let currentUrl = "";
let currentCompany = "";
let currentRole = "";

document.addEventListener("DOMContentLoaded", () => {
  const btnFillForm = document.getElementById("btnFillForm");
  const btnScan = document.getElementById("btnScan");
  const btnMarkApplied = document.getElementById("btnMarkApplied");
  const btnGenerateAI = document.getElementById("btnGenerateAI");
  const btnSaveQBank = document.getElementById("btnSaveQBank");

  // Initial Scan on load
  scanActiveTab();

  // Listen for tab activation / switching in Chrome
  chrome.tabs.onActivated.addListener(() => {
    setTimeout(scanActiveTab, 300);
  });

  chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (tab.active && changeInfo.status === "complete") {
      setTimeout(scanActiveTab, 300);
    }
  });

  btnScan.addEventListener("click", scanActiveTab);

  btnFillForm.addEventListener("click", () => {
    chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      sendMessageWithInjection(activeTab, { action: "EXECUTE_FILL", fieldMap: currentFields }, (response) => {
        if (response && response.status === "SUCCESS") {
          showToast(`✨ Pre-filled ${response.filledCount} fields successfully!`);
        } else {
          showToast("⚠️ Could not fill fields on this page.");
        }
      });
    });
  });

  btnMarkApplied.addEventListener("click", () => {
    chrome.runtime.sendMessage({
      action: "MARK_JOB_APPLIED",
      url: currentUrl,
      company: currentCompany,
      role: currentRole
    }, (response) => {
      showToast("✅ Application confirmed & marked as Applied!");
    });
  });

  btnGenerateAI.addEventListener("click", () => {
    const questionText = document.getElementById("aiQuestionLabel").innerText;
    showToast("🤖 Requesting AI Answer (Gemini / DeepSeek)...");
    
    chrome.runtime.sendMessage({
      action: "GENERATE_AI_ANSWER",
      question: questionText,
      company: currentCompany,
      role: currentRole
    }, (response) => {
      if (response && response.status === "SUCCESS") {
        document.getElementById("aiAnswerText").value = response.answer;
        showToast("✨ AI Answer generated!");
      } else {
        showToast("❌ Failed to generate AI answer.");
      }
    });
  });

  btnSaveQBank.addEventListener("click", () => {
    const qText = document.getElementById("aiQuestionLabel").innerText;
    const aText = document.getElementById("aiAnswerText").value;
    if (!qText || !aText) return;

    chrome.runtime.sendMessage({
      action: "UPDATE_QUESTION_BANK",
      question: qText,
      answer: aText
    }, (response) => {
      showToast("💾 Saved to Question Bank!");
    });
  });
});

function isInternalUrl(url) {
  if (!url || typeof url !== "string") return true;
  const u = url.toLowerCase();
  return u.startsWith("chrome://") ||
         u.startsWith("chrome-extension://") ||
         u.startsWith("edge://") ||
         u.startsWith("about:") ||
         u.startsWith("devtools://") ||
         u.startsWith("view-source:");
}

function sendMessageWithInjection(activeTab, message, callback) {
  if (!activeTab || !activeTab.id) {
    showToast("⚠️ No active tab found.");
    return;
  }

  const url = activeTab.url || "";
  if (isInternalUrl(url)) {
    if (message.action === "SCAN_FORM") {
      document.getElementById("previewList").innerHTML = `
        <div class="empty-state">
          <p>Chrome system page detected.</p>
          <p style="margin-top: 4px; font-size: 10px; color: #94a3b8;">Switch to a job application tab to scan form fields.</p>
        </div>`;
      document.getElementById("fieldCount").innerText = "0 fields";
    } else {
      showToast("⚠️ Open a job application page (Greenhouse, Lever, LinkedIn, etc.) to fill fields.");
    }
    return;
  }

  chrome.tabs.sendMessage(activeTab.id, message, (response) => {
    if (!chrome.runtime.lastError && response) {
      callback(response);
      return;
    }

    // Auto-inject content script if not present
    chrome.scripting.executeScript({
      target: { tabId: activeTab.id },
      files: ["content.js"]
    }, () => {
      if (chrome.runtime.lastError) {
        showToast("⚠️ Refresh page & reload extension to attach scripts.");
        return;
      }
      setTimeout(() => {
        chrome.tabs.sendMessage(activeTab.id, message, (retryResp) => {
          if (chrome.runtime.lastError || !retryResp) {
            showToast("⚠️ Please refresh the web page to activate auto-fill.");
          } else {
            callback(retryResp);
          }
        });
      }, 150);
    });
  });
}

function scanActiveTab() {
  chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
    const activeTab = tabs[0];
    if (!activeTab || !activeTab.id) return;

    currentUrl = activeTab.url || "";
    document.getElementById("pageTitle").innerText = activeTab.title || "Job Application Form";
    document.getElementById("pageUrl").innerText = currentUrl;

    // Detect ATS platform from URL
    const atsBadge = document.getElementById("atsBadge");
    if (currentUrl.includes("greenhouse.io")) atsBadge.innerText = "Greenhouse ATS";
    else if (currentUrl.includes("lever.co")) atsBadge.innerText = "Lever ATS";
    else if (currentUrl.includes("ashbyhq.com")) atsBadge.innerText = "Ashby ATS";
    else if (currentUrl.includes("workday.com")) atsBadge.innerText = "Workday ATS";
    else if (currentUrl.includes("linkedin.com")) atsBadge.innerText = "LinkedIn Form";
    else atsBadge.innerText = "Web Form";

    sendMessageWithInjection(activeTab, { action: "SCAN_FORM" }, (response) => {
      if (!response || !response.fields) {
        document.getElementById("previewList").innerHTML = `
          <div class="empty-state">
            <p>No active form fields detected.</p>
            <p style="margin-top: 4px; font-size: 10px; color: #94a3b8;">If you just loaded the page, click "Rescan DOM".</p>
          </div>`;
        document.getElementById("fieldCount").innerText = "0 fields";
        return;
      }

      currentFields = response.fields || [];
      renderPreviewList(currentFields);
    });
  });
}

function renderPreviewList(fields) {
  const previewList = document.getElementById("previewList");
  const fieldCount = document.getElementById("fieldCount");

  fieldCount.innerText = `${fields.length} fields`;

  if (fields.length === 0) {
    previewList.innerHTML = `<div class="empty-state">No form fields detected.</div>`;
    return;
  }

  previewList.innerHTML = "";
  fields.forEach((field, index) => {
    const item = document.createElement("div");
    item.className = "field-item";

    item.innerHTML = `
      <div class="field-header">
        <span class="field-title">${escapeHtml(field.label)}</span>
        <span class="source-badge">${escapeHtml(field.source)}</span>
      </div>
      <input type="text" class="field-input" data-index="${index}" value="${escapeHtml(field.targetValue)}">
    `;

    // Highlight AI generator trigger if custom text area
    if (field.source === "AI Ready" || field.targetValue === "[AI Generation Ready]") {
      item.style.borderColor = "#8b5cf6";
      item.addEventListener("click", () => {
        document.getElementById("aiSection").style.display = "block";
        document.getElementById("aiQuestionLabel").innerText = field.label;
      });
    }

    previewList.appendChild(item);
  });

  // Attach input listener to update target values on edit
  document.querySelectorAll(".field-input").forEach(inputEl => {
    inputEl.addEventListener("input", (e) => {
      const idx = parseInt(e.target.getAttribute("data-index"));
      if (currentFields[idx]) {
        currentFields[idx].targetValue = e.target.value;
      }
    });
  });
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.innerText = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3000);
}

function escapeHtml(str) {
  return String(str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Job Application Command Center Dashboard App (Pushp Raj v4.0)

const API_BASE = "http://127.0.0.1:8000/api";

let allJobs = [];
let allQBank = {};
let activePillFilter = "all";

document.addEventListener("DOMContentLoaded", () => {
  initNav();
  fetchJobs();
  fetchQuestionBank();

  // Setup 5-second silent auto-polling
  setInterval(() => {
    fetchJobs(true);
  }, 5000);

  // Event Listeners for Jobs
  document.getElementById("btnRefreshJobs").addEventListener("click", triggerScraperRefresh);
  const btnArc = document.getElementById("btnArchiveJobs");
  if (btnArc) btnArc.addEventListener("click", triggerArchiveApplied);
  const btnRerun = document.getElementById("btnRerunHold");
  if (btnRerun) btnRerun.addEventListener("click", triggerRerunHold);
  const btnExpArc = document.getElementById("btnExportArchivedCSV");
  if (btnExpArc) btnExpArc.addEventListener("click", exportCSV);

  document.getElementById("searchBox").addEventListener("input", filterJobs);
  document.getElementById("filterCountry").addEventListener("change", filterJobs);
  document.getElementById("filterCity").addEventListener("change", filterJobs);
  document.getElementById("filterRole").addEventListener("change", filterJobs);
  document.getElementById("filterATS").addEventListener("change", filterJobs);
  document.getElementById("btnClearFilters").addEventListener("click", resetFilters);

  // Event Listener for QBank Search
  const qsearch = document.getElementById("searchQBank");
  if (qsearch) {
    qsearch.addEventListener("input", () => renderQBank(allQBank));
  }

  setupColorPills();
});

function initNav() {
  const navJobs = document.getElementById("navJobs");
  const navQBank = document.getElementById("navQBank");
  const navProfile = document.getElementById("navProfile");

  const viewJobs = document.getElementById("viewJobs");
  const viewQBank = document.getElementById("viewQBank");
  const viewProfile = document.getElementById("viewProfile");

  navJobs.addEventListener("click", (e) => {
    e.preventDefault();
    setActiveNav(navJobs, viewJobs, "Job Application Dashboard", "Targeting PM, APM, Growth PM & Analyst Roles in India, SEA & Remote");
  });

  navQBank.addEventListener("click", (e) => {
    e.preventDefault();
    setActiveNav(navQBank, viewQBank, "Question Bank Studio", "28 Curated Screening Answers synced with Chrome Extension");
    renderQBank(allQBank);
  });

  navProfile.addEventListener("click", (e) => {
    e.preventDefault();
    setActiveNav(navProfile, viewProfile, "Applicant Profile & Rules", "Hardcoded parameters for Pushp Raj (3.5 yrs, 25/27 LPA)");
  });

  const navArchived = document.getElementById("navArchived");
  const viewArchived = document.getElementById("viewArchived");
  if (navArchived && viewArchived) {
    navArchived.addEventListener("click", (e) => {
      e.preventDefault();
      setActiveNav(navArchived, viewArchived, "Applied Applications Archive Studio", "Complete historical archive of all submitted job applications with full filtering");
      fetchArchivedJobs();
    });
  }

  // Setup Archived Filter Listeners
  const sArc = document.getElementById("searchArchived");
  if (sArc) sArc.addEventListener("input", filterArchivedJobs);
  const fACountry = document.getElementById("filterArchivedCountry");
  if (fACountry) fACountry.addEventListener("change", filterArchivedJobs);
  const fACity = document.getElementById("filterArchivedCity");
  if (fACity) fACity.addEventListener("change", filterArchivedJobs);
  const fARole = document.getElementById("filterArchivedRole");
  if (fARole) fARole.addEventListener("change", filterArchivedJobs);
  const fAATS = document.getElementById("filterArchivedATS");
  if (fAATS) fAATS.addEventListener("change", filterArchivedJobs);
  const btnClrArc = document.getElementById("btnClearArchivedFilters");
  if (btnClrArc) btnClrArc.addEventListener("click", () => {
    if (sArc) sArc.value = "";
    if (fACountry) fACountry.value = "ALL";
    if (fACity) fACity.value = "ALL";
    if (fARole) fARole.value = "ALL";
    if (fAATS) fAATS.value = "ALL";
    filterArchivedJobs();
  });
  // Setup Hash Routing
  window.addEventListener("hashchange", handleHashRouting);
  handleHashRouting();
}

function setActiveNav(navEl, viewEl, heading, subheading) {
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".content-section").forEach(el => el.style.display = "none");

  navEl.classList.add("active");
  viewEl.style.display = "block";
  document.getElementById("pageHeading").innerText = heading;
  document.getElementById("pageSubheading").innerText = subheading;

  // Toggle Stats Bar visibility (only show on Jobs Feed)
  const metricsGrid = document.querySelector(".metrics-grid");
  if (metricsGrid) {
    metricsGrid.style.display = (viewEl.id === "viewJobs") ? "grid" : "none";
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function handleHashRouting() {
  const hash = window.location.hash;
  const navJobs = document.getElementById("navJobs");
  const viewJobs = document.getElementById("viewJobs");
  const navQBank = document.getElementById("navQBank");
  const viewQBank = document.getElementById("viewQBank");
  const navProfile = document.getElementById("navProfile");
  const viewProfile = document.getElementById("viewProfile");
  const navArchived = document.getElementById("navArchived");
  const viewArchived = document.getElementById("viewArchived");

  if (hash === "#archived" && navArchived && viewArchived) {
    setActiveNav(navArchived, viewArchived, "Applied Applications Archive Studio", "Complete historical archive of all submitted job applications with full filtering");
    fetchArchivedJobs();
  } else if (hash === "#qbank" && navQBank && viewQBank) {
    setActiveNav(navQBank, viewQBank, "Question Bank Studio", "24 Curated Screening Answers synced with Chrome Extension");
    renderQBank(allQBank);
  } else if (hash === "#profile" && navProfile && viewProfile) {
    setActiveNav(navProfile, viewProfile, "Applicant Profile & Rules", "Hardcoded parameters for Pushp Raj (3.5 yrs, 25/27 LPA)");
  } else if (navJobs && viewJobs) {
    setActiveNav(navJobs, viewJobs, "Job Application Dashboard", "Targeting PM, APM, Growth PM & Analyst Roles in India, SEA & Remote");
  }
}

function setupColorPills() {
  const pillBtns = document.querySelectorAll(".color-pill");
  pillBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      pillBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activePillFilter = btn.getAttribute("data-pill-type");
      filterJobs();
    });
  });
}

async function fetchJobs(silent = false) {
  const grid = document.getElementById("jobGrid");
  if (!silent && (!allJobs || allJobs.length === 0)) {
    grid.innerHTML = `<div class="loading-spinner">Fetching live jobs...</div>`;
  }

  try {
    const res = await fetch(`${API_BASE}/jobs`);
    allJobs = await res.json();

    // Parse clean City and Country metadata for each job
    allJobs.forEach(job => {
      const loc = extractCountryAndCity(job.location || "");
      job._city = loc.city;
      job._country = loc.country;
    });

    populateFilterOptions(allJobs);
    updateMetrics(allJobs);
    updatePillCounts(allJobs);
    filterJobs();

    const statusBadge = document.getElementById("apiStatusBadge");
    if (statusBadge) {
      statusBadge.innerHTML = "● Real-Time Live Sync (Connected)";
      statusBadge.style.color = "#34d399";
    }
  } catch (err) {
    console.error("Fetch jobs failed:", err);
    if (!silent) {
      grid.innerHTML = `<div class="loading-spinner" style="color: #ef4444;">Could not connect to API server at ${API_BASE}</div>`;
    }
    const statusBadge = document.getElementById("apiStatusBadge");
    if (statusBadge) {
      statusBadge.innerHTML = "● API Offline";
      statusBadge.style.color = "#ef4444";
    }
  }
}

function extractCountryAndCity(locationStr) {
  if (!locationStr) return { city: "Remote", country: "Remote" };
  const loc = locationStr.toLowerCase();

  let country = "India";
  if (loc.includes("singapore") || loc.includes("sg")) country = "Singapore";
  else if (loc.includes("bahrain") || loc.includes("manama")) country = "Bahrain";
  else if (loc.includes("remote") && !loc.includes("india")) country = "Remote / Global";
  else if (loc.includes("india")) country = "India";

  let city = "Bengaluru";
  if (loc.includes("bengaluru") || loc.includes("bangalore")) city = "Bengaluru";
  else if (loc.includes("gurugram") || loc.includes("gurgaon") || loc.includes("ncr") || loc.includes("delhi")) city = "Gurugram / NCR";
  else if (loc.includes("mumbai")) city = "Mumbai";
  else if (loc.includes("chennai")) city = "Chennai";
  else if (loc.includes("vadodara")) city = "Vadodara";
  else if (loc.includes("singapore")) city = "Singapore";
  else if (loc.includes("manama")) city = "Manama";
  else if (loc.includes("remote")) city = "Remote";

  return { city, country };
}

function populateFilterOptions(jobs) {
  const countrySelect = document.getElementById("filterCountry");
  const citySelect = document.getElementById("filterCity");
  const roleSelect = document.getElementById("filterRole");

  const currentCountry = countrySelect.value;
  const currentCity = citySelect.value;
  const currentRole = roleSelect.value;

  const countries = new Set();
  const cities = new Set();
  const roles = new Set();

  jobs.forEach(j => {
    if (j._country) countries.add(j._country);
    if (j._city) cities.add(j._city);
    if (j.role_family) roles.add(j.role_family);
  });

  // Country Dropdown
  countrySelect.innerHTML = `<option value="ALL">📍 Country: All</option>`;
  Array.from(countries).sort().forEach(c => {
    countrySelect.innerHTML += `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`;
  });
  countrySelect.value = currentCountry || "ALL";

  // City Dropdown
  citySelect.innerHTML = `<option value="ALL">🏙️ City: All</option>`;
  Array.from(cities).sort().forEach(c => {
    citySelect.innerHTML += `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`;
  });
  citySelect.value = currentCity || "ALL";

  // Role Family Dropdown
  roleSelect.innerHTML = `<option value="ALL">💼 Role: All</option>`;
  Array.from(roles).sort().forEach(r => {
    roleSelect.innerHTML += `<option value="${escapeHtml(r)}">${escapeHtml(r)}</option>`;
  });
  roleSelect.value = currentRole || "ALL";
}

async function syncAllCounts(activeJobs) {
  const jobs = activeJobs || allJobs || [];

  // 1. Active applied jobs in current feed
  const activeAppliedCount = jobs.filter(j => j.status === "Applied").length;

  // 2. Fetch server archived count
  let serverArchivedCount = 0;
  try {
    const res = await fetch(`${API_BASE}/jobs/archived`);
    const archivedList = await res.json();
    serverArchivedCount = (archivedList || []).length;
  } catch (err) {
    console.warn("Silent archived count fetch error:", err);
  }

  // 3. Total all-time applications = serverArchivedCount + activeAppliedCount
  const totalAllTimeApplied = serverArchivedCount + activeAppliedCount;

  // 4. Update Header Metrics Card: "Applications Submitted"
  const metricAppliedEl = document.getElementById("metricApplied");
  if (metricAppliedEl) {
    metricAppliedEl.innerText = totalAllTimeApplied;
  }

  // 5. Update Sidebar Tab Badge: "Applied Archive"
  const arcNavBadgeEl = document.getElementById("archivedNavCount");
  if (arcNavBadgeEl) {
    arcNavBadgeEl.innerText = totalAllTimeApplied;
  }

  // 6. Update Header Action Button: "📦 Archive Applied (activeAppliedCount)"
  const arcBtn = document.getElementById("btnArchiveJobs");
  if (arcBtn) {
    if (activeAppliedCount > 0) {
      arcBtn.innerHTML = `📦 Archive Applied (${activeAppliedCount})`;
      arcBtn.style.opacity = "1";
      arcBtn.style.cursor = "pointer";
      arcBtn.title = `Click to archive ${activeAppliedCount} applied jobs`;
    } else {
      arcBtn.innerHTML = `📦 Archive Applied (0)`;
      arcBtn.style.opacity = "0.6";
      arcBtn.style.cursor = "not-allowed";
      arcBtn.title = "No applied jobs available in active feed to archive";
    }
  }

  // 7. Update Total Qualified Jobs metric
  const metricTotalEl = document.getElementById("metricTotal");
  if (metricTotalEl) {
    metricTotalEl.innerText = jobs.length;
  }
}

function updateMetrics(jobs) {
  syncAllCounts(jobs);
}

function updatePillCounts(jobs) {
  document.getElementById("countPillAll").innerText = jobs.length;
  document.getElementById("countPillApplied").innerText = jobs.filter(j => j.status === "Applied").length;
  document.getElementById("countPillUnapplied").innerText = jobs.filter(j => j.status !== "Applied" && j.status !== "On Hold").length;
  const countHoldEl = document.getElementById("countPillHold");
  if (countHoldEl) countHoldEl.innerText = jobs.filter(j => j.status === "On Hold").length;
  document.getElementById("countPillIndia").innerText = jobs.filter(j => j._country === "India").length;
  document.getElementById("countPillSea").innerText = jobs.filter(j => j._country === "Singapore" || j._country === "Bahrain" || j._country === "SEA").length;
  document.getElementById("countPillRemote").innerText = jobs.filter(j => j._city === "Remote" || j._country === "Remote / Global").length;
}

function filterJobs() {
  const query = document.getElementById("searchBox").value.toLowerCase().trim();
  const country = document.getElementById("filterCountry").value;
  const city = document.getElementById("filterCity").value;
  const role = document.getElementById("filterRole").value;
  const ats = document.getElementById("filterATS").value;

  const filtered = allJobs.filter(job => {
    // Quick Pill Filters
    if (activePillFilter === "applied" && job.status !== "Applied") return false;
    if (activePillFilter === "unapplied" && (job.status === "Applied" || job.status === "On Hold")) return false;
    if (activePillFilter === "hold" && job.status !== "On Hold") return false;
    if (activePillFilter === "india" && job._country !== "India") return false;
    if (activePillFilter === "sea" && (job._country !== "Singapore" && job._country !== "Bahrain" && job._country !== "SEA")) return false;
    if (activePillFilter === "remote" && (job._city !== "Remote" && job._country !== "Remote / Global")) return false;

    // Search Query
    const matchesSearch = !query ||
      (job.company || "").toLowerCase().includes(query) ||
      (job.role_title || "").toLowerCase().includes(query) ||
      (job.location || "").toLowerCase().includes(query) ||
      (job._city || "").toLowerCase().includes(query) ||
      (job._country || "").toLowerCase().includes(query);

    const matchesCountry = country === "ALL" || job._country === country;
    const matchesCity = city === "ALL" || job._city === city;
    const matchesRole = role === "ALL" || job.role_family === role;
    const matchesATS = ats === "ALL" || detectATS(job.job_url).toLowerCase() === ats.toLowerCase();

    return matchesSearch && matchesCountry && matchesCity && matchesRole && matchesATS;
  });

  const hasActiveFilters = query !== "" || country !== "ALL" || city !== "ALL" || role !== "ALL" || ats !== "ALL" || activePillFilter !== "all";
  document.getElementById("btnClearFilters").style.display = hasActiveFilters ? "inline-block" : "none";

  document.getElementById("resultsCounter").innerText = `Showing ${filtered.length} of ${allJobs.length} qualified jobs`;
  renderJobs(filtered);
}

function resetFilters() {
  document.getElementById("searchBox").value = "";
  document.getElementById("filterCountry").value = "ALL";
  document.getElementById("filterCity").value = "ALL";
  document.getElementById("filterRole").value = "ALL";
  document.getElementById("filterATS").value = "ALL";

  activePillFilter = "all";
  document.querySelectorAll(".color-pill").forEach(b => b.classList.remove("active"));
  document.getElementById("pillAll").classList.add("active");

  filterJobs();
}

function calculateRealMatchScore(roleTitle, companyName) {
  const text = ((roleTitle || "") + " " + (companyName || "")).toLowerCase();
  let score = 78; // Base baseline match for curated PM list

  // Core Role Relevance
  if (text.includes("ai") && text.includes("product")) score += 14;
  else if (text.includes("growth") && text.includes("product")) score += 12;
  else if (text.includes("associate product") || text.includes("apm")) score += 11;
  else if (text.includes("product manager")) score += 10;
  else if (text.includes("analyst")) score += 8;
  else if (text.includes("founders office")) score += 7;
  else if (text.includes("product")) score += 5;

  // High-Tech / Startup Boost
  if (text.includes("ai") || text.includes("llm") || text.includes("tech")) score += 3;

  // Hash-based deterministic micro variance per job posting
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = (hash << 5) - hash + text.charCodeAt(i);
    hash |= 0;
  }
  const variance = Math.abs(hash % 5);

  return Math.min(98, Math.max(72, score + variance));
}

function renderJobs(jobs) {
  const container = document.getElementById("jobGrid");
  container.innerHTML = "";

  if (!jobs || jobs.length === 0) {
    container.innerHTML = `<div class="empty-state">No matching job listings found for selected colored filters.</div>`;
    return;
  }

  // Sort jobs cleanly: Applied jobs at top, then On Hold, then newest Qualified jobs
  const sortedJobs = [...jobs].sort((a, b) => {
    if (a.status === "Applied" && b.status !== "Applied") return -1;
    if (a.status !== "Applied" && b.status === "Applied") return 1;
    if (a.status === "On Hold" && b.status !== "On Hold") return -1;
    if (a.status !== "On Hold" && b.status === "On Hold") return 1;
    return new Date(b.discovered_at || 0) - new Date(a.discovered_at || 0);
  });

  sortedJobs.forEach(job => {
    const card = document.createElement("div");
    const isApplied = job.status === "Applied";
    const isHold = job.status === "On Hold";
    card.className = `job-card ${isApplied ? 'is-applied' : ''} ${isHold ? 'is-hold' : ''}`;

    const ats = detectATS(job.job_url);
    const atsClass = ats.toLowerCase().replace(/\s+/g, '');
    const realMatch = calculateRealMatchScore(job.role_title, job.company);

    let statusBadgeHTML = '<span class="status-badge qualified">⚡ Qualified</span>';
    if (isApplied) statusBadgeHTML = '<span class="status-badge applied">✅ Applied</span>';
    else if (isHold) statusBadgeHTML = '<span class="status-badge hold" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4);">⏸️ On Hold</span>';

    card.innerHTML = `
      <div>
        <span class="ats-tag ${atsClass}">${ats}</span>
        <div class="job-company">${escapeHtml(job.company)}</div>
        <div class="job-title">${escapeHtml(job.role_title)}</div>

        <div class="card-pills">
          <span class="badge-pill loc">📍 ${escapeHtml(job._city)}, ${escapeHtml(job._country)}</span>
          <span class="badge-pill exp">💼 3.5 yrs Exp</span>
          <span class="badge-pill match">🎯 ${realMatch}% Match</span>
          ${statusBadgeHTML}
        </div>
      </div>

      <div class="card-actions">
        <a href="${escapeHtml(job.job_url)}" target="_blank" class="btn-action-primary">
          ${isApplied ? '🔗 Open Posting' : (isHold ? '🔗 Check Link' : '🚀 Launch Posting')}
        </a>
        ${isHold ? `
          <button class="btn-action-applied btn-unhold" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; border-color: rgba(59, 130, 246, 0.35);">
            🔄 Un-hold
          </button>
        ` : ''}
        ${!isApplied && !isHold ? `
          <button class="btn-action-applied btn-mark-applied">
            ✅ Applied
          </button>
          <button class="btn-action-applied btn-mark-hold" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.35);">
            ⏸️ On Hold
          </button>
        ` : ''}
      </div>
    `;

    // Attach direct event listeners
    const btnApplied = card.querySelector(".btn-mark-applied");
    if (btnApplied) {
      btnApplied.addEventListener("click", async (e) => {
        e.preventDefault();
        e.stopPropagation();
        btnApplied.innerText = "⏳ Updating...";
        await quickMarkApplied(job.job_url, job.company, job.role_title);
      });
    }

    const btnHold = card.querySelector(".btn-mark-hold");
    if (btnHold) {
      btnHold.addEventListener("click", async (e) => {
        e.preventDefault();
        e.stopPropagation();
        btnHold.innerText = "⏳ Updating...";
        await quickMarkHold(job.job_url, job.company, job.role_title);
      });
    }

    const btnUnhold = card.querySelector(".btn-unhold");
    if (btnUnhold) {
      btnUnhold.addEventListener("click", async (e) => {
        e.preventDefault();
        e.stopPropagation();
        btnUnhold.innerText = "⏳ Updating...";
        await quickUnhold(job.job_url, job.company);
      });
    }

    container.appendChild(card);
  });
}

async function quickDumpJob(url, company, role) {
  try {
    const res = await fetch(`${API_BASE}/jobs/dump`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, company, role })
    });
    const data = await res.json();
    if (data.status === "success") {
      fetchJobs(false);
    }
  } catch (err) {
    console.error("Quick dump job error:", err);
  }
}

async function quickMarkApplied(url, company, role) {
  try {
    const res = await fetch(`${API_BASE}/jobs/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, company, role })
    });
    if (res.ok) fetchJobs(false);
  } catch (err) {
    console.error("Mark applied error:", err);
  }
}

async function quickMarkHold(url, company, role) {
  try {
    const res = await fetch(`${API_BASE}/jobs/hold`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, company, role })
    });
    if (res.ok) fetchJobs(false);
  } catch (err) {
    console.error("Mark hold error:", err);
  }
}

async function quickUnhold(url, company) {
  try {
    const res = await fetch(`${API_BASE}/jobs/unhold`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, company })
    });
    if (res.ok) fetchJobs(false);
  } catch (err) {
    console.error("Unhold error:", err);
  }
}

function detectATS(url) {
  if (!url) return "Portal";
  if (url.includes("greenhouse.io")) return "Greenhouse";
  if (url.includes("lever.co")) return "Lever";
  if (url.includes("ashbyhq.com")) return "Ashby";
  if (url.includes("workday.com")) return "Workday";
  if (url.includes("linkedin.com")) return "LinkedIn";
  return "Company Portal";
}

async function fetchQuestionBank() {
  try {
    const res = await fetch(`${API_BASE}/qbank`);
    allQBank = await res.json();
    renderQBank(allQBank);
  } catch (err) {
    console.error("Fetch QBank error:", err);
  }
}

function renderQBank(qbank) {
  const qbankGrid = document.getElementById("qbankGrid");
  if (!qbankGrid) return;
  qbankGrid.innerHTML = "";

  const entries = Object.entries(qbank || {});
  const searchVal = (document.getElementById("searchQBank")?.value || "").toLowerCase().trim();

  const filtered = entries.filter(([q, a]) => {
    return !searchVal || q.toLowerCase().includes(searchVal) || a.toLowerCase().includes(searchVal);
  });

  const counterEl = document.getElementById("qbankCounter");
  if (counterEl) counterEl.innerText = `${filtered.length} of ${entries.length} Questions in Bank`;
  const navCountEl = document.getElementById("qbankNavCount");
  if (navCountEl) navCountEl.innerText = entries.length;

  if (filtered.length === 0) {
    qbankGrid.innerHTML = `<div class="empty-state">No screening questions match "${searchVal}".</div>`;
    return;
  }

  filtered.forEach(([q, a], index) => {
    const card = document.createElement("div");
    card.className = "qbank-card";

    // Clean question text display
    const displayQ = q.replace(/\*$/, "").trim();

    card.innerHTML = `
      <div class="qbank-header">
        <span class="q-number-tag">Q${index + 1}</span>
        <div class="q-title">${escapeHtml(displayQ)}</div>
        <button class="btn-copy" onclick="copyToClipboard('${escapeJsString(a)}')">📋 Copy Answer</button>
      </div>
      <div class="q-answer-box">
        ${escapeHtml(a)}
      </div>
    `;

    qbankGrid.appendChild(card);
  });
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert("Copied answer to clipboard!");
  }).catch(err => {
    console.error("Copy error:", err);
  });
}

function escapeJsString(str) {
  return String(str || "").replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, " ");
}

async function triggerScraperRefresh() {
  const btn = document.getElementById("btnRefreshJobs");

  if (allJobs && allJobs.length >= 100) {
    alert("⚡ Feed Capacity Ceiling Reached (100 Active Jobs).\n\nPlease click '📦 Archive 15 Applied' to archive completed applications before refreshing new roles.");
    return;
  }

  const originalText = btn.innerHTML;
  btn.innerHTML = "⏳ Scraping 15 New Roles...";
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/jobs/refresh`, { method: "POST" });
    const data = await res.json();

    if (data.status === "blocked") {
      alert(`⚠️ ${data.message}`);
    } else if (data.status === "success") {
      alert(`✅ ${data.message}`);
      fetchJobs(false);
    }
  } catch (err) {
    console.error("Scraper refresh error:", err);
    alert("Could not connect to backend scraper engine.");
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

async function triggerArchiveApplied() {
  const btn = document.getElementById("btnArchiveJobs");
  const appliedCount = allJobs ? allJobs.filter(j => j.status === "Applied").length : 0;

  if (appliedCount === 0) {
    alert("⚠️ No applied jobs currently available in feed to archive.");
    return;
  }

  const originalText = btn ? btn.innerHTML : "";
  if (btn) {
    btn.innerHTML = "📦 Archiving 15 Jobs...";
    btn.disabled = true;
  }

  try {
    const res = await fetch(`${API_BASE}/jobs/archive`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ batch_size: 15 })
    });
    const data = await res.json();

    if (data.status === "success") {
      alert(`📦 ${data.message}\n\nRemaining Active Feed: ${data.remaining_active} jobs.\nTotal Archived: ${data.total_archived} jobs.`);
      fetchJobs(false);
    } else if (data.status === "warning") {
      alert(`⚠️ ${data.message}`);
    }
  } catch (err) {
    console.error("Archive jobs error:", err);
    alert("Could not connect to backend archive engine.");
  } finally {
    if (btn) {
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  }
}

async function triggerRerunHold() {
  const btn = document.getElementById("btnRerunHold");
  const holdCount = allJobs ? allJobs.filter(j => j.status === "On Hold").length : 0;

  if (holdCount === 0) {
    alert("⚠️ No jobs currently marked On Hold to re-run.");
    return;
  }

  const originalText = btn ? btn.innerHTML : "";
  if (btn) {
    btn.innerHTML = "⏳ Evaluating On Hold Jobs...";
    btn.disabled = true;
  }

  try {
    const res = await fetch(`${API_BASE}/jobs/hold/rerun`, { method: "POST" });
    const data = await res.json();

    if (data.status === "success") {
      alert(`🔍 ${data.message}`);
      fetchJobs(false);
    } else if (data.status === "warning") {
      alert(`⚠️ ${data.message}`);
    }
  } catch (err) {
    console.error("Re-run On Hold jobs error:", err);
    alert("Could not connect to backend evaluation engine.");
  } finally {
    if (btn) {
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  }
}

function clean_url_base(urlStr) {
  if (!urlStr) return "";
  try {
    const u = new URL(urlStr);
    return (u.origin + u.pathname).replace(/\/+$/, "").toLowerCase();
  } catch (e) {
    return String(urlStr).split("?")[0].replace(/\/+$/, "").toLowerCase();
  }
}

let allArchivedJobs = [];

async function fetchArchivedJobs() {
  try {
    const res = await fetch(`${API_BASE}/jobs/archived`);
    let serverArchived = await res.json();

    // Also include any active jobs marked as Applied
    const activeApplied = (allJobs || []).filter(j => j.status === "Applied");

    const combinedMap = new Map();
    [...serverArchived, ...activeApplied].forEach(j => {
      const key = clean_url_base(j.job_url) || ((j.company || "") + "_" + (j.role_title || "")).toLowerCase();
      if (!combinedMap.has(key)) {
        combinedMap.set(key, j);
      }
    });

    allArchivedJobs = Array.from(combinedMap.values());
    allArchivedJobs.forEach(job => {
      const loc = extractCountryAndCity(job.location || "");
      job._city = loc.city;
      job._country = loc.country;
    });

    const arcCountEl = document.getElementById("archivedNavCount");
    if (arcCountEl) arcCountEl.innerText = allArchivedJobs.length;

    populateArchivedFilterOptions(allArchivedJobs);
    filterArchivedJobs();
  } catch (err) {
    console.error("Fetch archived jobs error:", err);
  }
}

function populateArchivedFilterOptions(jobs) {
  const countrySelect = document.getElementById("filterArchivedCountry");
  const citySelect = document.getElementById("filterArchivedCity");
  const roleSelect = document.getElementById("filterArchivedRole");

  if (!countrySelect || !citySelect || !roleSelect) return;

  const currentCountry = countrySelect.value;
  const currentCity = citySelect.value;
  const currentRole = roleSelect.value;

  const countries = new Set();
  const cities = new Set();
  const roles = new Set();

  jobs.forEach(j => {
    if (j._country) countries.add(j._country);
    if (j._city) cities.add(j._city);
    if (j.role_family) roles.add(j.role_family);
  });

  countrySelect.innerHTML = `<option value="ALL">📍 Country: All</option>`;
  Array.from(countries).sort().forEach(c => {
    countrySelect.innerHTML += `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`;
  });
  countrySelect.value = currentCountry || "ALL";

  citySelect.innerHTML = `<option value="ALL">🏙️ City: All</option>`;
  Array.from(cities).sort().forEach(c => {
    citySelect.innerHTML += `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`;
  });
  citySelect.value = currentCity || "ALL";

  roleSelect.innerHTML = `<option value="ALL">💼 Role: All</option>`;
  Array.from(roles).sort().forEach(r => {
    roleSelect.innerHTML += `<option value="${escapeHtml(r)}">${escapeHtml(r)}</option>`;
  });
  roleSelect.value = currentRole || "ALL";
}

function filterArchivedJobs() {
  const query = (document.getElementById("searchArchived")?.value || "").toLowerCase().trim();
  const country = document.getElementById("filterArchivedCountry")?.value || "ALL";
  const city = document.getElementById("filterArchivedCity")?.value || "ALL";
  const role = document.getElementById("filterArchivedRole")?.value || "ALL";
  const ats = document.getElementById("filterArchivedATS")?.value || "ALL";

  const filtered = allArchivedJobs.filter(job => {
    const matchesSearch = !query ||
      (job.company || "").toLowerCase().includes(query) ||
      (job.role_title || "").toLowerCase().includes(query) ||
      (job.location || "").toLowerCase().includes(query) ||
      (job._city || "").toLowerCase().includes(query) ||
      (job._country || "").toLowerCase().includes(query);

    const matchesCountry = country === "ALL" || job._country === country;
    const matchesCity = city === "ALL" || job._city === city;
    const matchesRole = role === "ALL" || job.role_family === role;
    const matchesATS = ats === "ALL" || detectATS(job.job_url).toLowerCase() === ats.toLowerCase();

    return matchesSearch && matchesCountry && matchesCity && matchesRole && matchesATS;
  });

  const clearBtn = document.getElementById("btnClearArchivedFilters");
  if (clearBtn) {
    clearBtn.style.display = (query !== "" || country !== "ALL" || city !== "ALL" || role !== "ALL" || ats !== "ALL") ? "inline-block" : "none";
  }

  const counterEl = document.getElementById("archivedResultsCounter");
  if (counterEl) {
    counterEl.innerText = `Showing ${filtered.length} of ${allArchivedJobs.length} archived applications`;
  }

  renderArchivedJobs(filtered);
}

function renderArchivedJobs(jobs) {
  const grid = document.getElementById("archivedJobGrid");
  if (!grid) return;
  grid.innerHTML = "";

  if (!jobs || jobs.length === 0) {
    grid.innerHTML = `<div class="empty-state">No matching archived applications found.</div>`;
    return;
  }

  jobs.forEach(job => {
    const card = document.createElement("div");
    card.className = "job-card is-applied";

    const ats = detectATS(job.job_url);
    const atsClass = ats.toLowerCase().replace(/\s+/g, '');
    const realMatch = calculateRealMatchScore(job.role_title, job.company);

    card.innerHTML = `
      <div>
        <span class="ats-tag ${atsClass}">${ats}</span>
        <div class="job-company">${escapeHtml(job.company)}</div>
        <div class="job-title">${escapeHtml(job.role_title)}</div>

        <div class="card-pills">
          <span class="badge-pill loc">📍 ${escapeHtml(job._city)}, ${escapeHtml(job._country)}</span>
          <span class="badge-pill exp">💼 3.5 yrs Exp</span>
          <span class="badge-pill match">🎯 ${realMatch}% Match</span>
          <span class="status-badge applied">✅ Applied</span>
        </div>
      </div>

      <div class="card-actions">
        <a href="${escapeHtml(job.job_url)}" target="_blank" class="btn-action-primary">
          🔗 Open Job Posting
        </a>
      </div>
    `;

    grid.appendChild(card);
  });
}

function exportCSV() {
  window.open(`${API_BASE}/jobs`, '_blank');
}

function escapeHtml(str) {
  return String(str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

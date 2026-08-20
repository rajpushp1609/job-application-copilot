// Job Copilot Content Script for Pushp Raj
// Features: Auto Resume PDF Attachment, Shadow DOM scanning, Lever/Greenhouse ATS Radio & Link Matching, React/Vue value setters, and strict profile rules.

(function () {
  if (window.__jobCopilotLoaded) return;
  window.__jobCopilotLoaded = true;

  console.log("[Job Copilot] Universal Extension Engine Active on:", window.location.href);

  const PROFILE = {
    firstName: "Pushp",
    lastName: "Raj",
    fullName: "Pushp Raj",
    email: "rajpushp1609@gmail.com",
    phone: "7368089031",
    linkedin: "https://www.linkedin.com/in/pushp-raj-a09/",
    github: "https://github.com/pushpraj1609",
    portfolio: "https://github.com/pushpraj1609",
    naukri: "",
    other_url: "",
    location: "Bengaluru, India",
    currentCompany: "Wayground",
    experience: "3.5",
    currentCTC: "25 LPA",
    currentCTCInt: "2500000",
    expectedCTC: "27 LPA",
    expectedCTCInt: "2700000",
    noticePeriod: "0",
    noticeLabel: "Immediate",
    botCheck: "No",
    aiTools: "I use Claude Code, ChatGPT, Cursor, and Gemini daily for 0-to-1 vibe-coding feature prototypes, drafting PRDs, and testing AI workflows."
  };

  // Base64 string of Pushp_Raj_Resume_Revised.pdf
  const RESUME_BASE64 = "JVBERi0xLjQKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgKG9wZW5zb3VyY2UpCjEgMCBvYmoKPDwKL0YxIDIgMCBSIC9GMiAzIDAgUgo+PgplbmRvYmoKMiAwIG9iago8PAovQmFzZUZvbnQgL0hlbHZldGljYSAvRW5jb2RpbmcgL1dpbkFuc2lFbmNvZGluZyAvTmFtZSAvRjEgL1N1YnR5cGUgL1R5cGUxIC9UeXBlIC9Gb250Cj4+CmVuZG9iagozIDAgb2JqCjw8Ci9CYXNlRm9udCAvSGVsdmV0aWNhLUJvbGQgL0VuY29kaW5nIC9XaW5BbnNpRW5jb2RpbmcgL05hbWUgL0YyIC9TdWJ0eXBlIC9UeXBlMSAvVHlwZSAvRm9udAo+PgplbmRvYmoKNCAwIG9iago8PAovQ29udGVudHMgOCAwIFIgL01lZGlhQm94IFsgMCAwIDU5NS4yNzU2IDg0MS44ODk4IF0gL1BhcmVudCA3IDAgUiAvUmVzb3VyY2VzIDw8Ci9Gb250IDEgMCBSIC9Qcm9jU2V0IFsgL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSSBdCj4+IC9Sb3RhdGUgMCAvVHJhbnMgPDwKCj4+IAogIC9UeXBlIC9QYWdlCj4+CmVuZG9iago1IDAgb2JqCjw8Ci9QYWdlTW9kZSAvVXNlTm9uZSAvUGFnZXMgNyAwIFIgL1R5cGUgL0NhdGFsb2cKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL0F1dGhvciAoUHVzaHAgUmFqKSAvQ3JlYXRpb25EYXRlIChEOjIwMjYwNzE4MTE1MzEyKzA1JzAwJykgL0NyZWF0b3IgKFwodW5zcGVjaWZpZWRcKSkgL0tleXdvcmRzICgpIC9Nb2REYXRlIChEOjIwMjYwNzE4MTE1MzEyKzA1JzAwJykgL1Byb2R1Y2VyIChSZXBvcnRMYWIgUERGIExpYnJhcnkgLSBcKG9wZW5zb3VyY2VcKSkgCiAgL1N1YmplY3QgKFwodW5zcGVjaWZpZWRcKSkgL1RpdGxlIChQdXNocCBSYWogLSBSZXN1bWUpIC9UcmFwcGVkIC9GYWxzZQo+PgplbmRvYmoKNyAwIG9iago8PAovQ291bnQgMSAvS2lkcyBbIDQgMCBSIF0gL1R5cGUgL1BhZ2VzCj4+CmVuZG9iago8IDAgb2JqCjw8Ci9GaWx0ZXIgWyAvQVNDSUk4NURlY29kZSAvRmxhdGVEZWNvZGUgXSAvTGVuZ3RoIDM2MTAKPj4Kc3RyZWFtCkdiITtmZ04pJT4lWGxaKWkqZUQmQ2RcYWRpYmVGJGppXG9FU0Ffa3NiWUZGMT4jXC4oOVRfcjJbJWwsdXIjUltkOFRxMERTVFMyRkcjYjgwUERxYSslTHRiWUFEdS5rczJHR0ByPVQjJV0xb18kVUZGbEVaVlI+MDNaOjBZcjYwJVpwLVs8OCw8cW5GWyoxNWZqImMhdD4hQEI6MTlJS25nRUR1bmtNUilTZmVfRjM/TE5MQzAhS3NxRy9RSSUyVycjUW9PQFVsUGcwTVA/STdtTE5XLWFVVCZLRlg/JSRwND0zKCU0Y21SPDRxTjltJGwuVV5HJXNJPlRQTVhmbDJjXGtkWjc+ITBnVUVvLGNQQF1yYnJCKFc/aD8rWi48LDc0JDchYSVuXEllWz8tMTMuZiJqQyMxKmIhNmZZJSh0MyM4MGQoVmtLaCVoSmFuaFs3NGFbSElBKnJrOTdwR0t0XnBmQFsnTTtUMHJxJzpHNFo3NW1kdS1oZXBoVWVoNlY7aihMUjtDKylWLSZuck5TS3VtSTZvTGBkPVhLJ2YvJi4pOFhKY29FUXA5SlBwMVlxbk9JI1IxJFBLX2VNaDdmdDxtI1s0TWNxRCJqRmZgUWwiSWNQS1RgRk0nTUNtKy5bLkMrMi5lQ008Zi9aU1pROVI5JUBOJm1NQ1dSYkZZdW5iKV8+SixWSCZyKFpvLCdqWTBYTTtVOFNjNVsnaj9oUC0hUylgSW9vJlYpWmMuPC8jZTcnSiYlKE1DT1d0ZDs2JFw3Ni9XQyFcOTFsakUtai9EIztCQWkqamVkNGouW19CUislTVlpREopRW9CUXVHMnRSbGpAIV9haHBWTEZsST1OTHFUbkVScT0ybDBLOzEmRz5AdWM2Zz5NX2gjJkUnWDFPVTNObXVja0hPXmZVVCY0LWxkam8hWjg5XSc7RnI/c0tDZjY/XjJWO1xUU3FiXmJwclFzQz1ddVVNNUM7Jk8rZDBsMm1kbWxIOEZvOGlJci1vLlNJISxHSWlyKCQrbV1mRVw4bHArOCtZTE5ZXW1QQ2w0My8iVkU4XVpBJSwuJyQ5VmRyUkg/PlpPJyhQXmBxOztXbkEkWFMxUEgwMyY1TVFLVmhETnRFVVlHJEZuSFxmIWdMJ1RNOSQrPlcuWUNLXS83PDJ0VVxaa1NvM2pVSkUsUTpVKm5gTyI+cVhLX0FkInRHcVMoZStxVSd1aTAnc2RTQDRYQ1U1Mz1CSiRhXCM6O0xnPG5iUkwkb0w6ImBEYF9xWDE9WHIxPW04OTo4cFFjVDFJTF5rc1woP2Q4LkgzPyM5QlJLU0RPT1ksP0RFP2gvNSY6LlczVVspQ0dFPi8nIT4kazIsZk5SNGY8TE9XU3MjJ2xzWl0qTF0kYzJjalpOTlxlRiFbT2syQTVRXlU2W2AsW0twRlldRipCOWMjT0VeZi9zISFralgsVC8sKzxmI2JlQkJMWS8wNyc6ZTtQVTVlUUFRPG4sTGUiN2InLVI7MyFWbVNCV0IhOzFBdSdybDVhQUQwT0JVOjwzb1gsMUlPZUpLai5DQ0hxZXU2aS84SnRmdE9HS1QuP2NxV1g9IVAiMGMrbVMsVWs6SFJNYGBFJC0sby0jbzJOJE5rKGZaQzdeMlRGL3JuN0M/Q19XYWxPJSR0J2dINkA7Zyshb0YwVW9zdVNaUk5mOCMsdDRlb0k1PVlzJC02aWRscDE6PC9hSS4qP0JPVjxMRUZKSnBdJEMhNXBUQGQoWWE3L1cqamJcP2JZYFdXIUJjO19PWWY2ImJAT0skaVdyY2VGVUxdKWo7QSU6J1tqNiE8LT90IVVpOk9JOT82QGF1JEdKWWZbK3U0Om9SVU44N3RhRlUyO04nW1JMU0E3SHBuOEUmNEtQKG5UJW5uKzxJODQ0U0sjNiRIQ1I4aWpiV0lpRlZdSk9eNTpIMCkoXCw7LktUJFpFKXI+Y0pzN24jLi4tUTJBW0pAbUUhPmcvJlhVPkVkWCtDZGp1NG1zI2QyQC81VDVcdT4rMSFaa2hnQD5oMGpCUy0vSCpeN1pOYVBgWGcqOEFTMmM8dDE7aXJzUFcvcD8yO2ZgXjFhXG1ESm1tLUpjLHVpUVsqYzMxL2xnQGdJST5GZkJEMiRyXik7QWNmRzM4NTRSSixKSjRydHBwOjE3UmsiSk0jYTVqSj5AIzshb1RUaE5vV2IySWYqKjU6PVktO2lPcT5eTE85VT5NPFQtU2peN1VJVjVpcHFDNW8xbT86U21EQWNaaGBJNG0raiY+SnMub0VIL0NVbywtampYMGRmZXVsKW0zMyw6PCk1NUQ+VGc2IzBIXyc5cS5BQ1ZbMGsuXShaSXJSJVZFM2hTJm1aQCw3K19nb1I8Tk47OU5PM1JOJSokNltsLkBeLlkzNk1ELmg1VUtSQiMpTkhQMWdQKkVOOlg+S1ojYjptUWQ7TCNFZztsM1FUI01RMFpHPE5kUUpOLnJqbC05PyxGQUZKZks0dHBsLj0qYCU5KiIjLC0iJSMyaWBSYk9UR0pVcDVSXVJQWCclYUdAOTFYPkUvN3IlSSJRVzQpREBtNWFCXiphYkxpKkFjajBYYVV1WWgqaGxMJE9VVWAuIlxpYEQ6OTlxQ0N0VTFZIl0vRDI4UU8rVlw5Ny5IL2VCTy4uOjUvTVorVEE/LVQwQjBIbm1mTnE4LjlfLy0iMDlVKipBKlpmLGgxIWIxQycmZihOTlArP0ddOSYrcVhIXFVROnFSJlA6TG5HSGJXLCpaYkBxPGctLk5MLFs0ZChYXCo6RToiJ2ZNYGY6O2I8QWNNX2VpJi9xYUIlYj5icG9KTlBKcHB0KDY+aGkmRjwqIUBTZFxKWGpzbVFIby8/LHVIWSs3VkBORkVyPl4hb2lkJStnXyZhMzdKXGM8SUk+RSZTPTVdKGFfQ1ZbNjFpQVI1UmQtXDE4TC1pSE1VVl9xL19HKyZBMTs3SWgxbyoiaWxqK2hCYExCYE9yT0xbZW1OdGVyQ2hIKjA/OihcTTo0Y2B0ZzplPTNxSUxJVjszZGp0TCI5WlRdNj9zdSxgZ1peNHRVVEA+RlZxN0xKNSpUSi1vSVotIUY6WTJ0Ii80MTEsIjdbVmRLUnFtajFAVkJUcCQoZms4IUEwczZYaU8xYygiIWJUM0oraXJibTk+K1pbaVxIbSVGNlgyTFZxTnRpJTlXJDNKXW8jLGpVSFBYPkZiIWRAYVBQOE1nIm5TVjw2bVw+SG1IcDQkdCclVjswb090X2kxN2IuPm9LQHJXJkEuYEBpYUVLdUA5O2REYig4PkFNaDlTZFs9MStFWFJoLj5DTjM5JEtsRkI4P2chIkRRN3FGYjxObWplaDQnQVBHRU1fdCxpcSF1XFNLP1giKThbKTNXVnNrXSUlY29zNVdxJGIvMmNeR1NaMk9hO21KRmJQNGBOMylfQD04MTJ0QSxkWUooTGpCQEIvWiY5NShjJT0nOFE9O0U2bzQ9WzZsUHV1TGdSYUQ2ZHU6W05XLllXbTg3YT5iMSc8VSlecyRyNGtSWWAqYy88PSppUmpiWzByOjpSNGQ0SzRKYyIwNFAwYyknWD1hVmE8RE07Mj0nKmVESChORiEjOlQrP3BRIT4jaFBNVCtqRCVjJDgyPD1bPWVlL3BFbis5SlgpO0Nibk47Ny1ZXj4qYVw9cjBdbmAkZ0YqI3I5KSRxQThaaEtRM0tvaDclMEp0TV9vXmk6Qy89K0J0dGQ2LmBaSyJKW0ZdQVtpWzFvJWhHcjtCJFshWzFPLThRaD1BLWFQJiU5VTtVUCUhKDx0LzYjQDQqL2kpP3A6KjQtK1FjNy5yalFuQkUsQmFccS05QmxjLE9QdWhgJzYwKlpfTDw7UyZAVVw/NFpOKThtKCxBTVsvN2VHP18oWnNaRDgvP0VzNmdxaTFjV2tzXGpOdGw4Wl9vI3VFWkc/aTFqQjdgZzcmRmdUbWB1NSNnXVwyQCpIP1ZGRkleQVlcOHRlREpfZ201SF8uIURsSHNzYzY/Qi4nUj5gYyg3KDdPKWxGczRPY2JcMW9UR1BMc0csaC1eMyxuL1VSV1lfKTJJPiheSyooUjU3NCpvJFNwL1BvIWUyLCZaNT03ZCRyKmxlLFZOXC9qTlYxSEY7OippbDFpaFxJUTNIaltGVmRnMDpIW2UtTyxRJklVOC9lWlxbYzdMSig6cG5dXjI8SXN0PUZtTXI4am06TVVVKkIuYT4pQWJJLW8iQUk3blVRPCdubSJvOWRcODhbZDdCKj5qIT1TZzowWmdSI09UVEVeIjQ8cV1ZNGxLYzRhMz0kP1ZJXkNQY1NLMDs0Nz05OUNPK1klLlQyQDJWTUluVyYyWSgxbDhpbnBuSHVuOV9aJmlVUFIpclFfLWomLFMpPFY4NXFzb3BjQiomUighclI/QlByIVdVdEE+LityVERXKk0zMTldN0RcT0wyOm1YYiM6N2ZgPmtqU0E6WSFsYGZDQG0vT0VyOEhEalBFWHRfSFImKjNVRDxkODY2KmgyWTViJHNialY8VG5hQz4xRTEjaG9XM0k2P3Jwc0BWXS86Ry5yczddW0hLbTRlTzV0TnUyai1WL2EyUjVDUG4xNiZoSEkyWzFRaEJjSXIkRCMraU5DOjpJMGBWYnVJbmpeYEEvSEpfQW9dYEstNWgvTzZoRWhoL2w6bSVkLkxYKWNNUFw9XyFqLl1LKD5Oa1dGZSJlImxFNytKJnI0TVRtOSdvQVJELzdWOiwoJ1BFPU9JdTRcb2A0UGdjOk9cZlUuYGl1T2kzUz5tW1RUN3I+LWRpcjFhfj5lbmRzdHJlYW0KZW5kb2JqCnhyZWYKMCA5CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDA2MSAwMDAwMCBuIAowMDAwMDAwMTAyIDAwMDAwIG4gCjAwMDAwMDAyMDkgMDAwMDAgbiAKMDAwMDAwMDMyMSAwMDAwMCBuIAowMDAwMDAwNTI0IDAwMDAwIG4gCjAwMDAwMDA1OTIgMDAwMDAgbiAKMDAwMDAwMDg3MyAwMDAwMCBuIAowMDAwMDAwOTMyIDAwMDAwIG4gCnRyYWlsZXIKPDwKL0lEIApbPGU3ZGViYTNmMGZlZDJiZWRlYzcwZjQ4YmZlZTYzYjQwPjxlN2RlYmEzZjBmZWQyYmVkZWM3MGY0OGJmZWU2M2I0MD5dCiUgUmVwb3J0TGFiIGdlbmVyYXRlZCBQREYgZG9jdW1lbnQgLS0gZGlnZXN0IChvcGVuc291cmNlKQoKL0luZm8gNiAwIFIKL1Jvb3QgNSAwIFIKL1NpemUgOQo+PgpzdGFydHhyZWYKNDYzMwolJUVPRgo=";

  function attachResumeToFileInput(fileInput) {
    if (!fileInput) return false;
    try {
      const byteCharacters = atob(RESUME_BASE64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: "application/pdf" });
      const file = new File([blob], "Pushp_Raj_Resume_Revised.pdf", { type: "application/pdf" });

      const container = new DataTransfer();
      container.items.add(file);
      fileInput.files = container.files;

      fileInput.dispatchEvent(new Event("change", { bubbles: true }));
      fileInput.dispatchEvent(new Event("input", { bubbles: true }));
      fileInput.dispatchEvent(new Event("blur", { bubbles: true }));
      console.log("[Job Copilot] Successfully attached Pushp_Raj_Resume_Revised.pdf");
      return true;
    } catch (err) {
      console.warn("[Job Copilot] Resume auto-attach error:", err);
      return false;
    }
  }

  // Extract clean text label for any input/select/textarea
  function getElementLabel(el) {
    if (!el) return "";

    // 1. Native HTML5 label property
    if (el.labels && el.labels.length > 0 && el.labels[0].innerText) {
      const txt = el.labels[0].innerText.replace(/REQUIRED|\*/gi, "").trim();
      if (txt) return txt;
    }

    // 2. Google Forms & ARIA aria-labelledby inspection
    const ariaLabelledBy = el.getAttribute("aria-labelledby");
    if (ariaLabelledBy) {
      const ids = ariaLabelledBy.split(/\s+/);
      for (let id of ids) {
        const target = document.getElementById(id);
        if (target && target.innerText.trim()) {
          const tTxt = target.innerText.replace(/REQUIRED|\*/gi, "").trim();
          if (tTxt && tTxt.length > 1 && !tTxt.startsWith("Questionnaire for")) {
            return tTxt;
          }
        }
      }
    }

    // 3. Google Forms Explicit Question Container Inspection
    const gfContainer = el.closest('[role="listitem"], .geS58, .QrShBc, .o3D87, .freebirdFormviewerViewItemsItemItem, .form-group, fieldset');
    if (gfContainer) {
      const gfHeading = gfContainer.querySelector('[role="heading"], .M7eMe, .HoX3D, .freebirdFormviewerViewItemsItemItemTitle, legend, label');
      if (gfHeading && gfHeading !== el && gfHeading.innerText.trim()) {
        const gfTxt = gfHeading.innerText.replace(/REQUIRED|\*/gi, "").trim();
        if (gfTxt && gfTxt.length > 1 && !gfTxt.startsWith("Questionnaire for")) {
          return gfTxt;
        }
      }
    }

    // 4. Explicit label for id
    if (el.id) {
      try {
        const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (lbl && lbl.innerText.trim()) return lbl.innerText.replace(/REQUIRED|\*/gi, "").trim();
      } catch (e) {}
    }

    // 5. Instahyre & Custom Question Block Sibling Search (Look for preceding label or text div)
    let parentBlock = el.parentElement;
    for (let depth = 0; depth < 4; depth++) {
      if (!parentBlock) break;
      
      // Check previous element siblings
      let prev = parentBlock.previousElementSibling || el.previousElementSibling;
      while (prev) {
        const pTxt = prev.innerText ? prev.innerText.replace(/REQUIRED|\*/gi, "").trim() : "";
        if (pTxt && pTxt.length > 5 && pTxt.length < 500) {
          return pTxt;
        }
        prev = prev.previousElementSibling;
      }

      // Check headings inside container
      const heading = parentBlock.querySelector('label, p, h1, h2, h3, h4, div[class*="question"], div[class*="title"], div[class*="label"], div[class*="text"]');
      if (heading && heading !== el) {
        const hTxt = heading.innerText.replace(/REQUIRED|\*/gi, "").trim();
        if (hTxt && hTxt.length > 5 && hTxt.length < 500 && !hTxt.startsWith("Questionnaire for")) {
          return hTxt;
        }
      }

      parentBlock = parentBlock.parentElement;
    }

    // 6. Fallback to attributes: aria-label, placeholder, name, autocomplete, id
    const aria = el.getAttribute("aria-label");
    if (aria && aria.trim()) return aria.trim();

    const placeholder = el.getAttribute("placeholder");
    if (placeholder && placeholder.trim()) return placeholder.trim();

    const name = el.getAttribute("name");
    if (name && name.trim()) return name.trim();

    const id = el.id;
    if (id && id.trim()) return id.trim();

    return "Form Field";
  }

  // Helper to extract radio/checkbox option text specifically
  function getRadioOrCheckboxOptionText(el) {
    let text = "";
    if (el.value) text += " " + el.value;
    if (el.id) {
      try {
        const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (lbl) text += " " + lbl.innerText;
      } catch(e) {}
    }
    if (el.parentElement) {
      text += " " + el.parentElement.innerText;
    }
    if (el.nextElementSibling) {
      text += " " + el.nextElementSibling.innerText;
    }
    if (el.nextSibling && el.nextSibling.textContent) {
      text += " " + el.nextSibling.textContent;
    }
    return text.toLowerCase();
  }

  // Match target profile value based on label & attribute inspection
  function matchValueForElement(el, labelStr) {
    const text = (labelStr + " " + (el.name || "") + " " + (el.id || "") + " " + (el.placeholder || "") + " " + (el.getAttribute("autocomplete") || "")).toLowerCase();

    // 1. Bot check rule (CRITICAL HARD RULE)
    if (text.includes("robot") || text.includes("bot check") || text.includes("are you a bot") || text.includes("human check")) {
      return { value: "No", source: "Rule [Bot Check = No]" };
    }

    // 2. Resume File Upload
    if (el.type === "file" || text.includes("resume") || text.includes("cv") || text.includes("attach resume")) {
      return { value: "Pushp_Raj_Resume_Revised.pdf", source: "Resume Attached (PDF)" };
    }

    // 3. First Name / Last Name / Full Name
    if (text.includes("first name") || text.includes("fname") || text.includes("given name") || text.includes("given-name")) {
      return { value: PROFILE.firstName, source: "Profile [First Name]" };
    }
    if (text.includes("last name") || text.includes("lname") || text.includes("family name") || text.includes("family-name")) {
      return { value: PROFILE.lastName, source: "Profile [Last Name]" };
    }
    if (text.includes("name") && !text.includes("company") && !text.includes("school") && !text.includes("filename") && !text.includes("user")) {
      return { value: PROFILE.fullName, source: "Profile [Full Name]" };
    }

    // 4. Email
    if (text.includes("email") || el.type === "email" || (el.placeholder && el.placeholder.includes("example.com"))) {
      return { value: PROFILE.email, source: "Profile [Email]" };
    }

    // 5. Phone
    if (text.includes("phone") || text.includes("mobile") || text.includes("contact") || text.includes("tel") || el.type === "tel" || (el.placeholder && el.placeholder.includes("1-415"))) {
      return { value: PROFILE.phone, source: "Profile [Phone]" };
    }

    // 6. Current Company / Employer
    if (text.includes("current company") || text.includes("company") || text.includes("employer") || text.includes("organization")) {
      return { value: PROFILE.currentCompany, source: "Profile [Current Company = Wayground]" };
    }

    // 7. Distinct URL Matching Rules (Precise Link Separation)
    if (text.includes("github")) {
      return { value: PROFILE.github, source: "Profile [GitHub URL]" };
    }
    if (text.includes("naukri")) {
      return { value: PROFILE.naukri, source: "Profile [Naukri URL]" };
    }
    if (text.includes("portfolio") || text.includes("personal site") || text.includes("website") || text.includes("blog")) {
      return { value: PROFILE.portfolio, source: "Profile [Portfolio URL]" };
    }
    if (text.includes("other url") || text.includes("other link") || text.includes("additional url")) {
      return { value: PROFILE.other_url, source: "Profile [Other URL]" };
    }
    if (text.includes("linkedin")) {
      return { value: PROFILE.linkedin, source: "Profile [LinkedIn URL]" };
    }
    // Generic URL fallback (only if no specific link matched above)
    if (text.includes("url") || text.includes("link")) {
      return { value: "", source: "Unmatched URL" };
    }

    // 8. Location / Address / City / Relocate questions
    if (text.includes("based out of") || text.includes("relocate") || text.includes("bangalore") || text.includes("bengaluru") || text.includes("authorized")) {
      return { value: "Yes", source: "Profile [Relocate / Location = Yes]" };
    }
    if (text.includes("location") || text.includes("city") || text.includes("address")) {
      return { value: PROFILE.location, source: "Profile [Location]" };
    }

    // 9. Gender / Diversity
    if (text.includes("gender") || text.includes("sex") || text.includes("identity")) {
      return { value: "Male", source: "Profile [Gender = Male]" };
    }

    // 10. Total & Relevant Experience
    if (text.includes("experience") || text.includes("years") || text.includes("yoe")) {
      return { value: PROFILE.experience, source: "Profile [3.5 Yrs]" };
    }

    // 11. Current CTC & Expected CTC & Compensation
    if (text.includes("current compensation") || text.includes("current ctc") || text.includes("current salary") || text.includes("fixed ctc")) {
      return { value: PROFILE.currentCTCInt, source: "Profile [Current CTC]" };
    }
    if (text.includes("expected compensation") || text.includes("expected ctc") || text.includes("expected salary") || text.includes("target ctc")) {
      return { value: PROFILE.expectedCTCInt, source: "Profile [Expected CTC]" };
    }

    // 12. Notice Period (Must NOT match 'why do you want to join')
    if (text.includes("notice period") || text.includes("notice days") || text.includes("how soon can you start") || text.includes("availability to start")) {
      return { value: PROFILE.noticePeriod, source: "Profile [Notice Period]" };
    }

    // 13. Screening / Motivation / Why Join Questions (Triggers QBank / AI Answer)
    if (text.includes("why do you want to join") || text.includes("why join") || text.includes("why work") || text.includes("why are you interested") || text.includes("looking for")) {
      return { value: "[AI Generation Ready]", source: "AI Ready [Screening Question]" };
    }

    // 14. How did you hear about us / source
    if (text.includes("how did you hear") || text.includes("referral") || text.includes("source")) {
      return { value: "LinkedIn / Career Site", source: "Profile [Source]" };
    }

    // 14. AI Tools
    if (text.includes("ai tool") || text.includes("claude") || text.includes("chatgpt") || text.includes("cursor") || text.includes("workflow")) {
      return { value: PROFILE.aiTools, source: "Profile [AI Tools]" };
    }

    // 15. Custom Textareas / Screening Questions
    if (el.tagName === "TEXTAREA" || text.includes("why") || text.includes("describe") || text.includes("tell us") || text.includes("how")) {
      return { value: "[AI Generation Ready]", source: "AI Ready" };
    }

    return { value: "", source: "Unmatched" };
  }

  // Find all form elements (including inside Shadow DOM trees & Google Forms ARIA widgets)
  function getAllElements(root = document) {
    let list = Array.from(root.querySelectorAll("input, textarea, select, [role='radio'], [role='checkbox']"));
    
    // Pierce Shadow DOM roots
    const allNodes = root.querySelectorAll("*");
    allNodes.forEach(node => {
      if (node.shadowRoot) {
        list = list.concat(getAllElements(node.shadowRoot));
      }
    });

    return list;
  }

  // Scan all visible form fields
  function scanFormFields() {
    const fields = [];
    const elements = getAllElements();

    elements.forEach((el, index) => {
      if (el.type === "hidden" || el.type === "submit" || el.type === "button" || el.type === "image") return;

      const rawLabel = getElementLabel(el).replace(/[\n\r]+/g, " ").trim();
      const label = rawLabel.length > 0 ? rawLabel : `Field ${index + 1}`;
      const match = matchValueForElement(el, label);

      fields.push({
        index: index,
        id: el.id || `field_${index}`,
        label: label.substring(0, 60),
        targetValue: match.value,
        source: match.source,
        tagName: el.tagName,
        type: el.type || el.tagName.toLowerCase()
      });
    });

    return fields;
  }

  // Dedicated robust radio & checkbox checker
  function checkRadioButtonOrCheckbox(el, targetValue, fieldLabel) {
    if (!el || (el.type !== "radio" && el.type !== "checkbox")) return false;

    const optText = (getRadioOrCheckboxOptionText(el) + " " + (el.value || "")).toLowerCase();
    const labelLower = (fieldLabel || "").toLowerCase();
    const valLower = (targetValue || "").toLowerCase();

    let shouldCheck = false;

    // 1. Gender matching
    if (labelLower.includes("gender") || labelLower.includes("sex") || labelLower.includes("identity")) {
      if (valLower === "male" && optText.includes("male") && !optText.includes("female")) {
        shouldCheck = true;
      }
    }
    // 2. Experience matching (e.g. "Relevant Exp in Product", "Total Years of experience")
    else if (labelLower.includes("exp") || labelLower.includes("experience")) {
      if (optText.includes("yes") || optText.includes("3") || optText.includes("3.5") || optText.includes("more than")) {
        shouldCheck = true;
      }
    }
    // 3. Location / Relocate / Bangalore matching
    else if (labelLower.includes("based out") || labelLower.includes("relocate") || labelLower.includes("bangalore") || labelLower.includes("bengaluru") || labelLower.includes("authorized")) {
      if (optText.includes("yes")) {
        shouldCheck = true;
      }
    }
    // 4. Bot check
    else if (labelLower.includes("bot") || labelLower.includes("robot")) {
      if (optText.includes("no")) {
        shouldCheck = true;
      }
    }
    // 5. Generic Yes/No fallback
    else if (valLower === "yes" && optText.includes("yes")) {
      shouldCheck = true;
    } else if (valLower === "no" && optText.includes("no") && !optText.includes("notice")) {
      shouldCheck = true;
    } else if (valLower === "male" && optText.includes("male") && !optText.includes("female")) {
      shouldCheck = true;
    }

    if (shouldCheck) {
      el.checked = true;
      setNativeValue(el, el.value || "on");

      // Dispatch click events on element, parent, and label container
      try { el.click(); } catch(e) {}
      if (el.parentElement) {
        try { el.parentElement.click(); } catch(e) {}
      }
      const parentLabel = el.closest("label");
      if (parentLabel && parentLabel !== el.parentElement) {
        try { parentLabel.click(); } catch(e) {}
      }

      el.dispatchEvent(new Event("change", { bubbles: true }));
      el.dispatchEvent(new Event("input", { bubbles: true }));
      return true;
    }

    return false;
  }

  // React & Framework Value Injector
  function setNativeValue(element, value) {
    if (!element) return;
    const valueSetter = Object.getOwnPropertyDescriptor(element, 'value')?.set;
    const prototype = Object.getPrototypeOf(element);
    const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;

    if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {
      prototypeValueSetter.call(element, value);
    } else if (valueSetter) {
      valueSetter.call(element, value);
    } else {
      element.value = value;
    }

    if (element._valueTracker) {
      element._valueTracker.setValue("" + Math.random());
    }

    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    element.dispatchEvent(new Event('blur', { bubbles: true }));
  }

  // Execute fill on all matched elements
  function fillForm(fieldMap) {
    let filledCount = 0;
    const elements = getAllElements();

    // 1. Auto-attach resume to file upload inputs
    elements.forEach((el) => {
      if (el.type === "file" || (el.name && el.name.toLowerCase().includes("resume"))) {
        const attached = attachResumeToFileInput(el);
        if (attached) filledCount++;
      }
    });

    // 2. Fill text, radios, checkboxes, selects, textareas
    fieldMap.forEach((field) => {
      const el = elements[field.index];
      if (!el) return;

      try {
        // Handle AI Screening Questions / Textareas
        if (field.targetValue === "[AI Generation Ready]" || el.tagName === "TEXTAREA") {
          const qLabel = getElementLabel(el);
          let companyName = "";
          const pageTitle = document.title || "";
          if (pageTitle.includes("Questionnaire for ")) {
            companyName = pageTitle.split("Questionnaire for ")[1].split("-")[0].trim();
          } else if (pageTitle.includes("at ")) {
            companyName = pageTitle.split("at ")[1].trim();
          } else {
            companyName = pageTitle.replace("- Google Forms", "").trim();
          }

          chrome.runtime.sendMessage({
            action: "GENERATE_AI_ANSWER",
            question: qLabel,
            company: companyName,
            role: "Product Manager"
          }, (response) => {
            if (chrome.runtime.lastError) {
              console.warn("[Job Copilot] AI answer message error:", chrome.runtime.lastError);
              setNativeValue(el, "I am looking for opportunities where I can build products that bring meaningful impact, scale 0-to-1 features, and solve real user pain points.");
              return;
            }
            if (response && response.status === "SUCCESS" && response.answer) {
              setNativeValue(el, response.answer);
              console.log(`[Job Copilot] Injected AI Screening Answer (${response.source}) for: "${qLabel.substring(0, 30)}..."`);
            } else {
              console.warn("[Job Copilot] AI answer fallback triggered:", response ? response.error : "No response");
              setNativeValue(el, "I am looking for opportunities where I can build products that bring meaningful impact, scale 0-to-1 features, and solve real user pain points.");
            }
          });

          filledCount++;
          return;
        }

        if (!field.targetValue) return;

        if (el.type === "radio" || el.type === "checkbox") {
          const checked = checkRadioButtonOrCheckbox(el, field.targetValue, field.label);
          if (checked) filledCount++;
        } else if (el.tagName === "SELECT") {
          let matched = false;
          const targetValLower = field.targetValue.toLowerCase();

          for (let opt of el.options) {
            const optText = opt.text.toLowerCase();
            const optVal = opt.value.toLowerCase();
            if (optText.includes(targetValLower) || optVal.includes(targetValLower)) {
              el.value = opt.value;
              el.dispatchEvent(new Event('change', { bubbles: true }));
              matched = true;
              filledCount++;
              break;
            }
          }
          if (!matched && targetValLower === "yes") {
            for (let opt of el.options) {
              if (opt.text.toLowerCase().includes("yes") || opt.value.toLowerCase().includes("yes")) {
                el.value = opt.value;
                el.dispatchEvent(new Event('change', { bubbles: true }));
                matched = true;
                filledCount++;
                break;
              }
            }
          }
          if (!matched && el.options.length > 1 && el.selectedIndex <= 0) {
            el.selectedIndex = 1;
            el.dispatchEvent(new Event('change', { bubbles: true }));
            filledCount++;
          }
        } else if (el.type !== "file") {
          setNativeValue(el, field.targetValue);
          filledCount++;
        }
      } catch (err) {
        console.warn("[Job Copilot] Fill error for:", field.label, err);
      }
    });

    console.log(`[Job Copilot] Filled ${filledCount} fields.`);
    return filledCount;
  }

  // Injects non-intrusive floating button on page
  function injectFloatingWidget() {
    if (document.getElementById("job-copilot-floating-btn")) return;

    const fields = scanFormFields();
    if (fields.length === 0) return;

    const btn = document.createElement("button");
    btn.id = "job-copilot-floating-btn";
    btn.innerHTML = "⚡ Fill Application (Pushp Raj)";
    btn.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999999;
      background: linear-gradient(135deg, #8b5cf6, #3b82f6);
      color: #ffffff;
      border: none;
      padding: 12px 18px;
      border-radius: 30px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4);
      transition: all 0.2s ease;
    `;

    btn.addEventListener("mouseover", () => btn.style.transform = "scale(1.05)");
    btn.addEventListener("mouseout", () => btn.style.transform = "scale(1)");

    btn.addEventListener("click", () => {
      const current = scanFormFields();
      const count = fillForm(current);
      btn.innerHTML = `✨ Pre-filled ${count} fields!`;
      setTimeout(() => btn.innerHTML = "⚡ Fill Application (Pushp Raj)", 3000);
    });

    document.body.appendChild(btn);
  }

  // Run initial floating widget injection & setup observer for SPAs
  setTimeout(injectFloatingWidget, 1000);

  const observer = new MutationObserver(() => {
    injectFloatingWidget();
  });
  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Message listener from Extension Popup / Sidepanel
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "PING") {
      sendResponse({ status: "PONG" });
    } else if (request.action === "SCAN_FORM") {
      const fields = scanFormFields();
      sendResponse({ status: "SUCCESS", fields: fields, url: window.location.href, pageTitle: document.title });
    } else if (request.action === "EXECUTE_FILL") {
      const current = scanFormFields();
      const count = fillForm(request.fieldMap && request.fieldMap.length > 0 ? request.fieldMap : current);
      sendResponse({ status: "SUCCESS", filledCount: count });
    }
    return true;
  });

})();

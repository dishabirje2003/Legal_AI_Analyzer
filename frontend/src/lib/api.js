const API_BASE = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL : "";

async function parseError(res, fallback) {
  const raw = await res.text().catch(function () { return ""; });
  if (!raw) return fallback;
  try {
    const payload = JSON.parse(raw);
    const detail = payload ? payload.detail : null;
    if (typeof detail == "string") {
      if (detail.trim()) return detail;
    } else if (detail) {
      return JSON.stringify(detail);
    }
  } catch {}
  return raw ? raw : fallback;
}

async function fetchJson(path, options) {
  const res = await fetch(API_BASE + path, options);
  if (!res.ok) throw new Error(await parseError(res, "Request failed (" + res.status + ")"));
  return res.json();
}

export function uploadDocument(file, documentType, documentName, onProgress, userId) {
  const url = API_BASE + "/upload";
  const xhr = new XMLHttpRequest();
  return new Promise(function (resolve, reject) {
    xhr.upload.addEventListener("progress", function (e) {
      if (e.lengthComputable) {
        if (onProgress) onProgress(Math.min(100, Math.round((e.loaded / e.total) * 100)));
      }
    });
    xhr.addEventListener("load", function () {
      if ([200, 201, 202, 204].includes(xhr.status)) {
        const raw = xhr.responseText;
        try { resolve(raw ? JSON.parse(raw) : {}); } catch { resolve(raw); }
        return;
      }
      const raw = xhr.responseText ? xhr.responseText : "";
      try {
        const payload = raw ? JSON.parse(raw) : null;
        const detail = payload ? payload.detail : null;
        if (typeof detail == "string") {
          if (detail.trim()) {
            reject(new Error(detail));
            return;
          }
        }
      } catch {}
      reject(new Error(raw ? raw : "Upload failed (" + xhr.status + ")"));
    });
    xhr.addEventListener("error", function () { reject(new Error("Network error")); });
    xhr.addEventListener("abort", function () { reject(new Error("Upload aborted")); });
    xhr.open("POST", url);
    const body = new FormData();
    body.append("file", file);
    body.append("document_type", documentType);
    if (documentName) body.append("document_name", documentName);
    if (userId) body.append("user_id", userId);
    xhr.send(body);
  });
}

export function listDocuments(userId) {
  const q = userId ? "?user_id=" + encodeURIComponent(userId) : "";
  return fetchJson("/documents" + q);
}

export async function deleteDocument(documentId) {
  const res = await fetch(API_BASE + "/documents/" + encodeURIComponent(documentId), { method: "DELETE" });
  if (!res.ok) throw new Error(await parseError(res, "Delete failed (" + res.status + ")"));
}

export function getDocument(documentId) { return fetchJson("/documents/" + encodeURIComponent(documentId)); }
export function getDocumentText(documentId) { return fetchJson("/documents/" + encodeURIComponent(documentId) + "/text"); }
export function getDocumentAnalysis(documentId) { return fetchJson("/documents/" + encodeURIComponent(documentId) + "/analysis"); }
export function getQueueStatus() { return fetchJson("/admin/queue-status"); }
export function getDocumentClauses(documentId) { return fetchJson("/documents/" + encodeURIComponent(documentId) + "/clauses"); }
export function getDocumentRisks(documentId) { return fetchJson("/documents/" + encodeURIComponent(documentId) + "/risks"); }
export function getDocumentSections(documentId) { return fetchJson("/documents/" + encodeURIComponent(documentId) + "/sections"); }
export async function triggerCustomSummary(documentId, checklistMode, selectedSections) {
  const res = await fetch(API_BASE + "/documents/" + encodeURIComponent(documentId) + "/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ checklist_mode: checklistMode, selected_sections: selectedSections })
  });
  if (!res.ok) throw new Error(await parseError(res, "Request failed (" + res.status + ")"));
  return res.json();
}
export function getDashboardRiskSummary(userId) {
  const q = userId ? "?user_id=" + encodeURIComponent(userId) : "";
  return fetchJson("/dashboard/risk-summary" + q);
}
export function getSettingsProfile(userId, accessToken = "") {
  const q = userId ? "?user_id=" + encodeURIComponent(userId) : "";
  return fetchJson("/settings/profile" + q, {
    headers: { "Authorization": "Bearer " + accessToken },
  });
}
export function updateSettingsProfile(payload, accessToken = "") {
  return fetchJson("/settings/profile", {
    method: "PUT",
    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + accessToken },
    body: JSON.stringify(payload),
  });
}
export function deleteAllDocumentsForUser(userId, confirmation, accessToken = "") {
  return fetchJson("/settings/delete-all-documents", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + accessToken },
    body: JSON.stringify({ user_id: userId, confirmation }),
  });
}
export function deleteAccountForUser(userId, confirmation, accessToken = "") {
  return fetchJson("/settings/delete-account", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + accessToken },
    body: JSON.stringify({ user_id: userId, confirmation }),
  });
}
export async function askDocumentQuestion(documentId, question) {
  const res = await fetch(API_BASE + "/documents/" + encodeURIComponent(documentId) + "/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question })
  });
  if (!res.ok) throw new Error(await parseError(res, "Request failed (" + res.status + ")"));
  return res.json();
}
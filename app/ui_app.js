const state = {
  tenantId: "",
  apiKey: "",
  sessionId: "",
};

const tenantInput = document.getElementById("tenantId");
const apiKeyInput = document.getElementById("apiKey");
const sessionInput = document.getElementById("sessionId");
const saveBtn = document.getElementById("saveConfig");
const createBtn = document.getElementById("createTenant");
const notice = document.getElementById("tenantNotice");
const ingestNotice = document.getElementById("ingestNotice");
const ingestProgress = document.getElementById("ingestProgress");
const ingestProgressBar = document.getElementById("ingestProgressBar");
const ingestProgressText = document.getElementById("ingestProgressText");
const sessionBadge = document.getElementById("sessionBadge");
const latencyBadge = document.getElementById("latencyBadge");
const tokensBadge = document.getElementById("tokensBadge");
const docsBadge = document.getElementById("docsBadge");
const chatWindow = document.getElementById("chatWindow");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const clearBtn = document.getElementById("clearChat");
const chatAttachFileInput = document.getElementById("chatAttachFileInput");
const chatAttachFolderInput = document.getElementById("chatAttachFolderInput");
const chatAttachBtn = document.getElementById("chatAttachBtn");
const chatAttachNote = document.getElementById("chatAttachNote");
const attachMenu = document.getElementById("attachMenu");
const attachFilesBtn = document.getElementById("attachFiles");
const attachFolderBtn = document.getElementById("attachFolder");

let pendingAttachment = null;
let pendingAttachmentLabel = "Attach";

const stored = JSON.parse(localStorage.getItem("tourassist-chat") || "{}");
if (stored.tenantId) tenantInput.value = stored.tenantId;
if (stored.apiKey) apiKeyInput.value = stored.apiKey;
if (stored.sessionId) sessionInput.value = stored.sessionId;

function syncState() {
  state.tenantId = tenantInput.value.trim();
  state.apiKey = apiKeyInput.value.trim();
  state.sessionId = sessionInput.value.trim();
  localStorage.setItem("tourassist-chat", JSON.stringify(state));
  updateStatus();
}

function updateStatus() {
  if (state.tenantId && state.sessionId) {
    sessionBadge.textContent = `${state.tenantId}/${state.sessionId}`;
    notice.textContent = "Ready to chat.";
    notice.style.background = "rgba(51, 92, 98, 0.16)";
    notice.style.color = "#335c62";
  } else {
    sessionBadge.textContent = "Not connected";
    notice.textContent = "No tenant connected yet.";
    notice.style.background = "rgba(240, 106, 70, 0.12)";
    notice.style.color = "#d74a2c";
  }
}

function appendBubble(text, role = "assistant") {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  const para = document.createElement("p");
  para.textContent = text;
  bubble.appendChild(para);
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function setIngestNotice(message, tone = "neutral") {
  ingestNotice.textContent = message;
  if (tone === "ok") {
    ingestNotice.style.background = "rgba(51, 92, 98, 0.16)";
    ingestNotice.style.color = "#335c62";
    return;
  }
  if (tone === "error") {
    ingestNotice.style.background = "rgba(240, 106, 70, 0.12)";
    ingestNotice.style.color = "#d74a2c";
    return;
  }
  ingestNotice.style.background = "rgba(23, 19, 19, 0.08)";
  ingestNotice.style.color = "#5a4e4e";
}

function setIngestProgress(percent, active = true) {
  if (active) {
    ingestProgress.classList.add("active");
  } else {
    ingestProgress.classList.remove("active");
  }
  if (percent == null) {
    ingestProgressBar.style.width = "100%";
    ingestProgressText.textContent = "Uploading...";
    return;
  }
  const clamped = Math.max(0, Math.min(100, percent));
  ingestProgressBar.style.width = `${clamped}%`;
  ingestProgressText.textContent = `${clamped}%`;
}

function uploadWithProgress(url, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.setRequestHeader("X-API-Key", state.apiKey);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        if (onProgress) {
          onProgress(percent);
        } else {
          setIngestProgress(percent, true);
        }
      } else {
        if (onProgress) {
          onProgress(null);
        } else {
          setIngestProgress(null, true);
        }
      }
    };
    xhr.onload = () => {
      let payload = null;
      try {
        payload = JSON.parse(xhr.responseText || "{}");
      } catch {
        payload = {};
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        if (onProgress) {
          onProgress(100);
        } else {
          setIngestProgress(100, true);
        }
        resolve(payload);
        return;
      }
      const detail = payload.detail || `Upload failed (${xhr.status}).`;
      reject(new Error(detail));
    };
    xhr.onerror = () => reject(new Error("Network error during upload."));
    xhr.send(formData);
  });
}

function finalizeProgress() {
  setTimeout(() => setIngestProgress(0, false), 1200);
}

async function uploadSingleFile(file, buttonEl, label) {
  try {
    buttonEl.disabled = true;
    buttonEl.textContent = "Uploading...";
    setIngestProgress(0, true);
    const formData = new FormData();
    formData.append("tenant_id", state.tenantId);
    formData.append("file", file);
    const payload = await uploadWithProgress("/ingest", formData);
    setIngestNotice(
      `Indexed ${payload.chunks_indexed} chunks from ${file.name}.`,
      "ok"
    );
    return true;
  } catch (err) {
    setIngestNotice(err.message || "Ingest failed.", "error");
    return false;
  } finally {
    buttonEl.disabled = false;
    buttonEl.textContent = label;
    finalizeProgress();
  }
}

async function uploadFileBatch(files, buttonEl, label) {
  try {
    buttonEl.disabled = true;
    buttonEl.textContent = "Uploading...";
    const total = files.length;
    const results = [];
    let ingested = 0;
    let totalChunks = 0;
    setIngestProgress(0, true);

    for (let index = 0; index < total; index += 1) {
      const file = files[index];
      const formData = new FormData();
      formData.append("tenant_id", state.tenantId);
      formData.append("file", file);
      try {
        const payload = await uploadWithProgress("/ingest", formData, (percent) => {
          if (percent == null) {
            setIngestProgress(null, true);
            return;
          }
          const overall = Math.round(((index + percent / 100) / total) * 100);
          setIngestProgress(overall, true);
        });
        ingested += 1;
        totalChunks += payload.chunks_indexed ?? 0;
        results.push({ filename: file.name, error: null });
      } catch (err) {
        results.push({ filename: file.name, error: err.message || "Upload failed." });
      }
      const completed = Math.round(((index + 1) / total) * 100);
      setIngestProgress(completed, true);
    }

    const errors = results.filter((result) => result.error);
    const tone = ingested > 0 ? "ok" : "error";
    const message = `Indexed ${totalChunks} chunks from ${ingested} of ${total} files.` +
      (errors.length ? ` ${errors.length} file(s) failed.` : "");
    setIngestNotice(message, tone);
  } catch (err) {
    setIngestNotice(err.message || "Folder ingest failed.", "error");
  } finally {
    buttonEl.disabled = false;
    buttonEl.textContent = label;
    finalizeProgress();
  }
}

saveBtn.addEventListener("click", () => {
  syncState();
  appendBubble("Session saved. You can start chatting now.", "assistant");
});

createBtn.addEventListener("click", async () => {
  const tenantId = tenantInput.value.trim();
  if (!tenantId) {
    appendBubble("Enter a tenant ID before creating a new tenant.", "assistant");
    return;
  }

  try {
    createBtn.disabled = true;
    createBtn.textContent = "Creating...";
    const response = await fetch("/tenants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant_id: tenantId }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Unable to create tenant.");
    }
    apiKeyInput.value = payload.api_key;
    sessionInput.value = `session-${Date.now()}`;
    syncState();
    appendBubble(`Tenant "${payload.tenant_id}" created. API key saved.`, "assistant");
  } catch (err) {
    appendBubble(err.message || "Tenant creation failed.", "assistant");
  } finally {
    createBtn.disabled = false;
    createBtn.textContent = "Create Tenant";
  }
});

function closeAttachMenu() {
  attachMenu.classList.remove("active");
  attachMenu.setAttribute("aria-hidden", "true");
}

chatAttachBtn.addEventListener("click", () => {
  const isOpen = attachMenu.classList.contains("active");
  if (isOpen) {
    closeAttachMenu();
  } else {
    attachMenu.classList.add("active");
    attachMenu.setAttribute("aria-hidden", "false");
  }
});

attachFilesBtn.addEventListener("click", () => {
  closeAttachMenu();
  chatAttachFileInput.click();
});

attachFolderBtn.addEventListener("click", () => {
  closeAttachMenu();
  chatAttachFolderInput.click();
});

function handleAttachment(files, label) {
  const list = Array.from(files || []);
  if (list.length === 0) {
    pendingAttachment = null;
    pendingAttachmentLabel = "Attach";
    chatAttachNote.textContent = "No attachment selected.";
    return;
  }
  pendingAttachment = list;
  pendingAttachmentLabel = label;
  if (list.length === 1) {
    chatAttachNote.textContent = `Attachment ready: ${list[0].name}`;
    return;
  }
  chatAttachNote.textContent = `Attachment ready: ${list.length} files selected.`;
}

async function ingestSelectedFiles(files) {
  syncState();
  if (!state.tenantId || !state.apiKey) {
    setIngestNotice("Connect a tenant and API key before ingesting.", "error");
    return;
  }
  const list = Array.from(files || []);
  if (list.length === 0) {
    return;
  }
  if (list.length === 1) {
    await uploadSingleFile(list[0], chatAttachBtn, "Attach");
  } else {
    await uploadFileBatch(list, chatAttachBtn, "Attach");
  }
  pendingAttachment = null;
  chatAttachFileInput.value = "";
  chatAttachFolderInput.value = "";
  chatAttachNote.textContent = "No attachment selected.";
}

chatAttachFileInput.addEventListener("change", async () => {
  handleAttachment(chatAttachFileInput.files, "Attach");
  await ingestSelectedFiles(chatAttachFileInput.files);
});

chatAttachFolderInput.addEventListener("change", async () => {
  handleAttachment(chatAttachFolderInput.files, "Attach");
  await ingestSelectedFiles(chatAttachFolderInput.files);
});

document.addEventListener("click", (event) => {
  if (!attachMenu.classList.contains("active")) return;
  const target = event.target;
  if (target === chatAttachBtn || attachMenu.contains(target)) return;
  closeAttachMenu();
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;
  if (event.shiftKey) return;
  event.preventDefault();
  chatForm.requestSubmit();
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;
  syncState();
  if (!state.tenantId || !state.apiKey || !state.sessionId) {
    appendBubble("Connect a tenant, API key, and session before chatting.", "assistant");
    return;
  }

  if (pendingAttachment) {
    pendingAttachment = null;
  }

  appendBubble(message, "user");
  messageInput.value = "";

  const payload = {
    tenant_id: state.tenantId,
    session_id: state.sessionId,
    user_message: message,
  };

  try {
    const start = performance.now();
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": state.apiKey,
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    const elapsed = performance.now() - start;
    if (!response.ok) {
      throw new Error(data.detail || "Chat request failed.");
    }

    appendBubble(data.response || "No response returned.", "assistant");
    latencyBadge.textContent = `${data.latency_ms?.toFixed(0) ?? elapsed.toFixed(0)} ms`;
    tokensBadge.textContent = `${data.tokens_used ?? "--"}`;
    docsBadge.textContent = data.retrieved_doc_ids?.length
      ? data.retrieved_doc_ids.join(", ")
      : "--";
  } catch (err) {
    appendBubble(err.message || "Chat request failed.", "assistant");
  }
});

clearBtn.addEventListener("click", () => {
  chatWindow.innerHTML = "";
  appendBubble("Chat cleared. Ask another question whenever you're ready.", "assistant");
});

setIngestNotice("No file uploaded yet.");
syncState();

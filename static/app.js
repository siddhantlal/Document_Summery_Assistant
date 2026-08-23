"use strict";

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = ["pdf", "png", "jpg", "jpeg"];

const form = document.querySelector("#summary-form");
const input = document.querySelector("#document-input");
const dropZone = document.querySelector("#drop-zone");
const fileCard = document.querySelector("#file-card");
const fileName = document.querySelector("#file-name");
const fileSize = document.querySelector("#file-size");
const removeFileButton = document.querySelector("#remove-file");
const submitButton = document.querySelector("#submit-button");
const statusPanel = document.querySelector("#status-panel");
const statusTitle = document.querySelector("#status-title");
const statusDetail = document.querySelector("#status-detail");
const errorPanel = document.querySelector("#error-panel");
const errorMessage = document.querySelector("#error-message");
const results = document.querySelector("#results");
const summaryText = document.querySelector("#summary-text");
const keyPoints = document.querySelector("#key-points");
const resultMeta = document.querySelector("#result-meta");
const copyButton = document.querySelector("#copy-summary");
const startOverButton = document.querySelector("#start-over");

let selectedFile = null;
let phaseTimer = null;

function chooseFile() {
  input.click();
}

function setFile(file) {
  clearError();
  if (!file) {
    selectedFile = null;
    input.value = "";
    fileCard.hidden = true;
    dropZone.hidden = false;
    submitButton.disabled = true;
    return;
  }

  const extension = file.name.split(".").pop().toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    showError("Upload a PDF, PNG, or JPEG file.");
    return;
  }
  if (file.size === 0) {
    showError("The selected file is empty.");
    return;
  }
  if (file.size > MAX_FILE_SIZE) {
    showError("Files are limited to 10 MB.");
    return;
  }

  selectedFile = file;
  fileName.textContent = file.name;
  fileSize.textContent = formatFileSize(file.size);
  dropZone.hidden = true;
  fileCard.hidden = false;
  submitButton.disabled = false;
}

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function showError(message) {
  errorMessage.textContent = message;
  errorPanel.hidden = false;
}

function clearError() {
  errorMessage.textContent = "";
  errorPanel.hidden = true;
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading || !selectedFile;
  input.disabled = isLoading;
  removeFileButton.disabled = isLoading;
  statusPanel.hidden = !isLoading;
  submitButton.classList.toggle("is-loading", isLoading);

  window.clearTimeout(phaseTimer);
  if (isLoading) {
    statusTitle.textContent = "Extracting text";
    statusDetail.textContent = "Reading your document securely…";
    phaseTimer = window.setTimeout(() => {
      statusTitle.textContent = "Generating summary";
      statusDetail.textContent = "Finding the ideas that matter most…";
    }, 1200);
  }
}

function renderResults(data) {
  summaryText.textContent = data.summary;
  keyPoints.replaceChildren();
  data.key_points.forEach((point) => {
    const item = document.createElement("li");
    const marker = document.createElement("span");
    marker.setAttribute("aria-hidden", "true");
    marker.textContent = "✓";
    const text = document.createElement("p");
    text.textContent = point;
    item.append(marker, text);
    keyPoints.append(item);
  });

  const typeLabel = data.metadata.file_type === "pdf"
    ? `${data.metadata.pages} page${data.metadata.pages === 1 ? "" : "s"}`
    : "Scanned image";
  resultMeta.textContent = `${data.metadata.filename} · ${typeLabel} · ${data.metadata.summary_length} summary`;
  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function submitDocument(event) {
  event.preventDefault();
  if (!selectedFile) {
    showError("Choose a document to summarize.");
    return;
  }

  clearError();
  results.hidden = true;
  setLoading(true);

  const payload = new FormData();
  payload.append("document", selectedFile);
  payload.append("length", new FormData(form).get("length"));

  try {
    const response = await fetch("/api/summarize", { method: "POST", body: payload });
    let data;
    try {
      data = await response.json();
    } catch (_error) {
      throw new Error("The server returned an unreadable response.");
    }
    if (!response.ok) {
      throw new Error(data.error?.message || "The document could not be summarized.");
    }
    renderResults(data);
  } catch (error) {
    showError(error.message || "The document could not be summarized.");
  } finally {
    setLoading(false);
  }
}

function resetWorkspace() {
  setFile(null);
  clearError();
  results.hidden = true;
  summaryText.textContent = "";
  keyPoints.replaceChildren();
  form.querySelector('input[name="length"][value="medium"]').checked = true;
  dropZone.focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

dropZone.addEventListener("click", chooseFile);
dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    chooseFile();
  }
});
["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
});
["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  });
});
dropZone.addEventListener("drop", (event) => setFile(event.dataTransfer.files[0]));
input.addEventListener("change", () => setFile(input.files[0]));
removeFileButton.addEventListener("click", () => setFile(null));
form.addEventListener("submit", submitDocument);
startOverButton.addEventListener("click", resetWorkspace);
copyButton.addEventListener("click", async () => {
  const points = [...keyPoints.querySelectorAll("p")].map((point) => `• ${point.textContent}`);
  const text = `${summaryText.textContent}\n\nKey points\n${points.join("\n")}`;
  try {
    await navigator.clipboard.writeText(text);
    copyButton.querySelector("span").textContent = "Copied";
    window.setTimeout(() => {
      copyButton.querySelector("span").textContent = "Copy";
    }, 1600);
  } catch (_error) {
    showError("Copying is unavailable. Select the summary text manually.");
  }
});

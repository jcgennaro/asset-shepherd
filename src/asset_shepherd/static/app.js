const fileInput = document.querySelector("[data-file-input]");
const fileLabel = document.querySelector("[data-file-label]");

if (fileInput && fileLabel) {
  fileInput.addEventListener("change", () => {
    const selected = fileInput.files?.[0];
    fileLabel.textContent = selected ? selected.name : "Choose your GLB file";
  });
}

for (const form of document.querySelectorAll("[data-busy-form]")) {
  form.addEventListener("submit", (event) => {
    const submitter = event.submitter;
    for (const button of form.querySelectorAll("[data-submit-button]")) {
      if (button !== submitter) {
        button.disabled = true;
      }
    }
    if (submitter) {
      submitter.dataset.originalLabel = submitter.textContent;
      submitter.textContent = "Working…";
      submitter.setAttribute("aria-busy", "true");
      submitter.style.pointerEvents = "none";
    }
  });
}

for (const viewer of document.querySelectorAll("model-viewer")) {
  viewer.addEventListener("error", () => {
    viewer.classList.add("viewer-error");
    viewer.setAttribute("aria-label", `${viewer.getAttribute("alt")} — preview unavailable`);
  });
}

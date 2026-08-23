window.scrollTo(0, 0);

for (const fileInput of document.querySelectorAll("[data-file-input]")) {
  const dropZone = fileInput.closest("[data-drop-zone]");
  const fileLabel = dropZone?.querySelector("[data-file-label]");
  const fileError = dropZone?.querySelector("[data-file-error]");
  if (!dropZone || !fileLabel) {
    continue;
  }

  function updateFileState() {
    const selected = fileInput.files?.[0];
    const valid = Boolean(selected && selected.name.toLowerCase().endsWith(".glb"));
    fileInput.setCustomValidity(valid || !selected ? "" : "Choose one GLB file.");
    fileLabel.textContent = selected ? selected.name : "Choose or drop your GLB";
    dropZone.classList.toggle("invalid", Boolean(selected && !valid));
    if (fileError) {
      fileError.textContent = selected && !valid ? "Choose one GLB file." : "";
    }
  }

  fileInput.addEventListener("change", updateFileState);
  for (const eventName of ["dragenter", "dragover"]) {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = "copy";
      }
      dropZone.classList.add("dragging");
    });
  }
  dropZone.addEventListener("dragleave", (event) => {
    if (!dropZone.contains(event.relatedTarget)) {
      dropZone.classList.remove("dragging");
    }
  });
  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
    const dropped = event.dataTransfer?.files;
    if (!dropped || dropped.length !== 1 || !dropped[0].name.toLowerCase().endsWith(".glb")) {
      fileInput.value = "";
      fileInput.setCustomValidity("Choose one GLB file.");
      fileLabel.textContent = "Choose or drop your GLB";
      dropZone.classList.add("invalid");
      if (fileError) {
        fileError.textContent = "Choose one GLB file.";
      }
      return;
    }
    fileInput.files = dropped;
    updateFileState();
  });
}

const policyProposal = document.querySelector("[data-policy-proposal]");
const profileMode = document.querySelector("[data-profile-mode]");
const customToggle = document.querySelector("[data-custom-toggle]");
const customFields = document.querySelector("[data-custom-fields]");
const customStatus = document.querySelector("[data-custom-status]");
const customInputs = [...document.querySelectorAll("[data-custom-field]")];
const selectedPolicyLabel = document.querySelector("[data-selected-policy]");

function populateCustomFields() {
  const defaults = JSON.parse(policyProposal?.dataset.profileDefaults || "{}");
  for (const input of customInputs) {
    const key = input.dataset.customField;
    const value = defaults[key];
    input.value = typeof value === "boolean" ? String(value) : value;
  }
}

function updateSelectedPolicyLabel() {
  if (!selectedPolicyLabel) {
    return;
  }
  selectedPolicyLabel.textContent = customToggle?.checked
    ? "Agent-resolved rules — adjusted"
    : "Agent-resolved rules";
}

function setCustomMode(enabled) {
  if (profileMode) {
    profileMode.value = enabled ? "custom" : "resolved";
  }
  if (customFields) {
    customFields.hidden = !enabled;
  }
  for (const input of customInputs) {
    input.disabled = !enabled;
    input.required = enabled;
  }
  if (customStatus) {
    customStatus.textContent = enabled
      ? "Your supported adjustments will be validated and frozen."
      : "Agent proposal remains active.";
  }
  updateSelectedPolicyLabel();
}

customToggle?.addEventListener("change", () => {
  populateCustomFields();
  setCustomMode(customToggle.checked);
});

populateCustomFields();
setCustomMode(false);

const intakeWorkflow = document.querySelector("[data-intake-workflow]");

if (intakeWorkflow) {
  const panels = [...intakeWorkflow.querySelectorAll("[data-intake-panel]")];
  const stepButtons = [...intakeWorkflow.querySelectorAll("[data-intake-step-button]")];
  const validationMessage = intakeWorkflow.querySelector("[data-step-validation]");

  function validateRules() {
    for (const input of customInputs) {
      if (!input.disabled && !input.checkValidity()) {
        input.reportValidity();
        return false;
      }
    }
    if (validationMessage) {
      validationMessage.textContent = "";
    }
    updateSelectedPolicyLabel();
    return true;
  }

  function showStep(step) {
    if (step === "upload" && !validateRules()) {
      return;
    }
    for (const panel of panels) {
      panel.hidden = panel.dataset.intakePanel !== step;
    }
    for (const button of stepButtons) {
      if (button.dataset.intakeStepButton === step) {
        button.setAttribute("aria-current", "step");
      } else {
        button.removeAttribute("aria-current");
      }
    }
    intakeWorkflow.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  for (const button of intakeWorkflow.querySelectorAll("[data-intake-next]")) {
    button.addEventListener("click", () => showStep(button.dataset.intakeNext));
  }
  for (const button of stepButtons) {
    button.addEventListener("click", () => showStep(button.dataset.intakeStepButton));
  }
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

const inspectionExperience = document.querySelector("[data-inspection-experience]");

if (inspectionExperience && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const rows = [...inspectionExperience.querySelectorAll("[data-inspection-check]")];
  const results = [...document.querySelectorAll("[data-inspection-result]")];
  const count = inspectionExperience.querySelector("[data-inspection-count]");
  inspectionExperience.classList.add("replaying");
  if (count) {
    count.textContent = `0 of ${rows.length}`;
  }
  for (const row of rows) {
    row.classList.remove(row.dataset.status);
    row.classList.add("replaying");
    row.querySelector(".inspection-check-icon").textContent = "…";
    row.querySelector("strong").textContent = `Checking ${row.dataset.label}…`;
  }
  results.forEach((result) => result.setAttribute("aria-hidden", "true"));

  rows.forEach((row, index) => {
    window.setTimeout(() => {
      const status = row.dataset.status;
      row.classList.remove("replaying");
      row.classList.add(status);
      row.querySelector("strong").textContent = row.dataset.label;
      row.querySelector(".inspection-check-icon").textContent =
        status === "pass" ? "✓" : status === "blocked" ? "×" : status === "checking" ? "…" : "!";
      if (count) {
        count.textContent = `${index + 1} of ${rows.length}`;
      }
      if (index === rows.length - 1) {
        inspectionExperience.classList.remove("replaying");
        inspectionExperience.classList.add("replay-complete");
        results.forEach((result) => result.removeAttribute("aria-hidden"));
      }
    }, 220 * (index + 1));
  });
}

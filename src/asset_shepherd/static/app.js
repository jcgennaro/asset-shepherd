const fileInput = document.querySelector("[data-file-input]");
const fileLabel = document.querySelector("[data-file-label]");

if (fileInput && fileLabel) {
  fileInput.addEventListener("change", () => {
    const selected = fileInput.files?.[0];
    fileLabel.textContent = selected ? selected.name : "Choose your GLB file";
  });
}

const profileRadios = [...document.querySelectorAll('input[name="profile_id"]')];
const profileMode = document.querySelector("[data-profile-mode]");
const customToggle = document.querySelector("[data-custom-toggle]");
const customFields = document.querySelector("[data-custom-fields]");
const customStatus = document.querySelector("[data-custom-status]");
const customInputs = [...document.querySelectorAll("[data-custom-field]")];

function selectedProfile() {
  return profileRadios.find((radio) => radio.checked);
}

function populateCustomFields(profileRadio) {
  const defaults = JSON.parse(profileRadio.dataset.profileDefaults || "{}");
  for (const input of customInputs) {
    const key = input.dataset.customField;
    const value = defaults[key];
    input.value = typeof value === "boolean" ? String(value) : value;
  }
  const profileName = profileRadio
    .closest(".profile-option-shell")
    ?.querySelector(".profile-option strong")?.textContent;
  if (customStatus) {
    customStatus.textContent = `Copy of ${profileName || "selected preset"}; preset remains unchanged.`;
  }
}

function setCustomMode(enabled) {
  if (profileMode) {
    profileMode.value = enabled ? "custom" : "preset";
  }
  if (customFields) {
    customFields.hidden = !enabled;
  }
  for (const input of customInputs) {
    input.disabled = !enabled;
    input.required = enabled;
  }
}

for (const radio of profileRadios) {
  radio.addEventListener("change", () => {
    populateCustomFields(radio);
    if (customToggle) {
      customToggle.checked = false;
    }
    setCustomMode(false);
  });
}

customToggle?.addEventListener("change", () => {
  const profileRadio = selectedProfile();
  if (!profileRadio) {
    customToggle.checked = false;
    setCustomMode(false);
    profileRadios[0]?.focus();
    return;
  }
  populateCustomFields(profileRadio);
  setCustomMode(customToggle.checked);
});

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
